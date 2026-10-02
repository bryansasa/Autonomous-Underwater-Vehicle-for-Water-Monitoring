#include "water_quality_lib.h"

#define EZO_PH_I2C_ADDR 0x63
#define EZO_EC_I2C_ADDR 0x64
#define EZO_DO_I2C_ADDR 0x61
#define TEMP_PIN 7

WaterQualityManager::WaterQualityManager() 
    : ph_state(IDLE), ph_timer(0), 
    ec_state(IDLE), ec_timer(0), 
    do_state(IDLE), do_timer(0) {
    // Inisialisasi awal sensor pH (default sebelum ada pembacaan valid)
    current_data.ph.value = 7.0f;
    current_data.ph.valid = false;
    current_data.ph.state = decltype(current_data.ph.state)(1); // 1 = INITIALIZING / STANDBY
    
    // Inisialisasi awal sensor konduktivitas
    current_data.conductivity.value = 0.0f;
    current_data.conductivity.valid = false;
    current_data.conductivity.state = decltype(current_data.conductivity.state)(1); // 1 = INITIALIZING / STANDBY
    // Inisialisasi awal sensor Dissolved Oxygen (DO)
    current_data.dissolved_oxygen.value = 0.0f;
    current_data.dissolved_oxygen.valid = false;
    current_data.dissolved_oxygen.state = decltype(current_data.dissolved_oxygen.state)(1);

    // Inisialisasi suhu (default 25.0 C)
    current_data.temperature.value = 0.0f;
    current_data.temperature.valid = false;
    current_data.temperature.state = decltype(current_data.temperature.state)(1);
}

void WaterQualityManager::begin(uint8_t sda_pin, uint8_t scl_pin) {
    Wire.begin(sda_pin, scl_pin);
    Wire.setClock(100000);

    ph_timer = millis();
    ec_timer = millis() + 500; //  offset 500 ms agar request pH dan EC interleaving
    do_timer = millis() + 600; //  offset 1000 ms agar request DO tertunda

    // Setup Suhu
    pinMode(TEMP_PIN, INPUT);
    analogReadResolution(!2);
    temp_timer = millis();
}

void WaterQualityManager::requestPhReading() {
    Wire.beginTransmission(EZO_PH_I2C_ADDR);
    Wire.write('R');
    Wire.endTransmission();
    ph_timer = millis();
    ph_state = WAITING_CONVERSION;
}

//State Machine EC
void WaterQualityManager::fetchPhReading() {
    Wire.requestFrom((uint8_t)EZO_PH_I2C_ADDR, (size_t)7);
    if (Wire.available()) {
        uint8_t response_code = Wire.read();
        if (response_code == 1) { // Status SUCCESS dari modul EZO
            char ph_buf[8] = {0};
            uint8_t idx = 0;
            while (Wire.available() && idx < 7) {
                ph_buf[idx++] = Wire.read();
            }

            float val = atof(ph_buf);
            if (val > 0.0f) {
                // Bulatkan ke 2 desimal di sini (misal 2.974999... jadi 2.97)
                val = roundf(val * 100.0f) / 100.0f;

                current_data.ph.value = val;
                current_data.ph.valid = true;
                current_data.ph.state = decltype(current_data.ph.state)(2);
            }
        }
    }
    ph_state = IDLE;
    ph_timer = millis();
}

// STATE MACHINE: EZO-EC
void WaterQualityManager::requestEcReading() {
    Wire.beginTransmission(EZO_EC_I2C_ADDR);
    Wire.write('R');
    Wire.endTransmission();
    ec_timer = millis();
    ec_state = WAITING_CONVERSION;
}

void WaterQualityManager::fetchEcReading() {
    Wire.requestFrom((uint8_t)EZO_EC_I2C_ADDR, (size_t)16);
    if (Wire.available()) {
        uint8_t response_code = Wire.read();
        if (response_code == 1) { // Status SUCCESS (byte 1)
            char ec_buf[16] = {0};
            uint8_t idx = 0;
            while (Wire.available() && idx < 15) {
                char c = Wire.read();
                // Jika EZO-EC mengirim data berantai (misal: "1413,763,0.7"), ambil angka pertama sebelum koma
                if (c == ',') break;
                ec_buf[idx++] = c;
            }

            float val = atof(ec_buf);
            if (val >= 0.0f) {
                val = roundf(val * 10.0f) / 10.0f; // Bulatkan ke 1 desimal

                current_data.conductivity.value = val;
                current_data.conductivity.valid = true;
                current_data.conductivity.state = decltype(current_data.conductivity.state)(2);
            }
        } else {
            current_data.conductivity.valid = false;
        }
    }
    ec_state = IDLE;
    ec_timer = millis();
}

// 3. STATE MACHINE: EZO-DO (0x61)
void WaterQualityManager::requestDoReading() {
    Wire.beginTransmission(EZO_DO_I2C_ADDR);
    Wire.write('R');
    Wire.endTransmission();
    do_timer = millis();
    do_state = WAITING_CONVERSION;
}

void WaterQualityManager::fetchDoReading() {
    // EZO-DO mengembalikan 1 byte response code + ASCII nilai mg/L (contoh: 8.25)
    Wire.requestFrom((uint8_t)EZO_DO_I2C_ADDR, (size_t)10);
    if (Wire.available()) {
        uint8_t response_code = Wire.read();
        if (response_code == 1) { // 1 = SUCCESS
            char do_buf[10] = {0};
            uint8_t idx = 0;
            while (Wire.available() && idx < 9) {
                char c = Wire.read();
                if (c == ',') break; // Jika ada multi-output (% saturasi), ambil konsentrasi mg/L pertama
                do_buf[idx++] = c;
            }

            float val = atof(do_buf);
            if (val >= 0.0f) {
                current_data.dissolved_oxygen.value = roundf(val * 100.0f) / 100.0f; // 2 desimal
                current_data.dissolved_oxygen.valid = true;
                current_data.dissolved_oxygen.state = decltype(current_data.dissolved_oxygen.state)(2);
            }
        } else {
            current_data.dissolved_oxygen.valid = false;
        }
    }
    do_state = IDLE;
    do_timer = millis();
}

// --- FUNGSI PEMBACAAN SUHU ANALOG SURVEYOR ---
void WaterQualityManager::updateTemperature() {
    // Ambil rata-rata 10 sampel milivolt via ADC1 ESP32
    uint32_t mv_sum = 0;
    for (int i = 0; i < 10; i++) {
        mv_sum += analogReadMilliVolts(TEMP_PIN);
        delayMicroseconds(50);
    }
    float volts = (mv_sum / 10.0f) / 1000.0f;

    // Output Surveyor berkisar 0.5V - 3.1V (-50 C s.d 220 C)
    if (volts >= 0.5f && volts <= 3.1f) {
        // Rumus datasheet: T = (V - 1.058) / 0.009
        float t_val = (volts - 1.058f) / 0.009f;
        t_val = roundf(t_val * 100.0f) / 100.0f; // Bulatkan 2 desimal

        current_data.temperature.value = t_val;
        current_data.temperature.valid = true;
        current_data.temperature.state = decltype(current_data.temperature.state)(2);
    } else {
        current_data.temperature.valid = false;
    }
}

void WaterQualityManager::update() {
    unsigned long now = millis();

    switch (ph_state) {
        case IDLE:
            if (now - ph_timer >= 1000) requestPhReading();
            break;
        case WAITING_CONVERSION:
            if (now - ph_timer >= 900) fetchPhReading();
            break;
    }

    switch (ec_state) {
        case IDLE:
            if (now - ec_timer >= 1000) requestEcReading();
            break;
        case WAITING_CONVERSION:
            if (now - ec_timer >= 600) fetchEcReading();
            break;
    }
    switch (do_state) {
        case IDLE:
            if (now - do_timer >= 1000) requestDoReading();
            break;
        case WAITING_CONVERSION:
            if (now - do_timer >= 600) fetchDoReading();
            break;
    }
 
    if (now - temp_timer >= 500) {
        temp_timer = now;
        updateTemperature();
    }
}

WaterQualitySnapshot WaterQualityManager::readAll() {
    return current_data;
}

void WaterQualityManager::populateRosMessage(tyrant_payload_interfaces__msg__PayloadWaterQuality &msg) {
    // Nilai pH
    msg.ph = current_data.ph.value;
    msg.ph_valid = current_data.ph.valid;
    msg.ph_state = (uint8_t)current_data.ph.state;

    // Nilai Konduktivitas
    msg.conductivity_us_cm = current_data.conductivity.value;
    msg.conductivity_valid = current_data.conductivity.valid;
    msg.conductivity_state = (uint8_t)current_data.conductivity.state;

    // Nilai Dissolved Oxygen
    msg.dissolved_oxygen_mg_l = current_data.dissolved_oxygen.value;
    msg.dissolved_oxygen_valid = current_data.dissolved_oxygen.valid;
    msg.dissolved_oxygen_state = (uint8_t)current_data.dissolved_oxygen.state;

    // Nilai Suhu
    msg.temperature_c = current_data.temperature.value;
    msg.temperature_valid = current_data.temperature.valid;
    msg.temperature_state = (uint8_t)current_data.temperature.state;

}