#include "water_quality_lib.h"
#include <Wire.h>

WaterQualityManager::WaterQualityManager() 
    : dummy_temp(27.5f), dummy_ec(245.0f), dummy_ph(7.35f), dummy_do(6.80f) {}

void WaterQualityManager::begin() {
    // Inisialisasi Bus I2C-1 saat hardware siap
    // Wire.begin();
}

SensorData WaterQualityManager::readTemperature() {
    SensorData data;
    /* LOGIKA I2C TSYS01 / BR CELSIUS AKTUAL:
    Wire.beginTransmission(0x76);
    Wire.write(0x48);
    if (Wire.endTransmission() != 0) {
        data.valid = false; data.state = STATE_ERROR; return data;
    }
    Wire.requestFrom(0x76, 3);
    if (Wire.available() == 3) {
        uint32_t raw = (Wire.read() << 16) | (Wire.read() << 8) | Wire.read();
        data.value = calculate_celsius(raw);
        data.valid = true; data.state = STATE_READY; return data;
    }
    */

    // SIMULASI DUMMY
    dummy_temp += 0.05f;
    if (dummy_temp > 30.0f) dummy_temp = 27.5f;
    data.value = dummy_temp;
    data.valid = true;
    data.state = STATE_READY;
    return data;
}

SensorData WaterQualityManager::readConductivity() {
    SensorData data;
    /* LOGIKA I2C ATLAS SCIENTIFIC EZO-EC (0x64):
    Wire.beginTransmission(0x64);
    Wire.write("R");
    Wire.endTransmission();
    // parse response...
    */

    // SIMULASI DUMMY
    dummy_ec += 0.5f;
    if (dummy_ec > 300.0f) dummy_ec = 245.0f;
    data.value = dummy_ec;
    data.valid = true;
    data.state = STATE_READY;
    return data;
}

SensorData WaterQualityManager::readPh() {
    SensorData data;
    /* LOGIKA I2C ATLAS SCIENTIFIC EZO-pH (0x63):
    Wire.beginTransmission(0x63);
    Wire.write("R");
    Wire.endTransmission();
    // parse response...
    */

    // SIMULASI DUMMY
    dummy_ph += 0.01f;
    if (dummy_ph > 7.80f) dummy_ph = 7.35f;
    data.value = dummy_ph;
    data.valid = true;
    data.state = STATE_READY;
    return data;
}

SensorData WaterQualityManager::readDissolvedOxygen() {
    SensorData data;
    /* LOGIKA I2C ATLAS SCIENTIFIC EZO-DO (0x61):
    Wire.beginTransmission(0x61);
    Wire.write("R");
    Wire.endTransmission();
    // parse response...
    */

    // SIMULASI DUMMY
    dummy_do += 0.02f;
    if (dummy_do > 8.50f) dummy_do = 6.80f;
    data.value = dummy_do;
    data.valid = true;
    data.state = STATE_READY;
    return data;
}

WaterQualitySnapshot WaterQualityManager::readAll() {
    WaterQualitySnapshot snap;
    // Pembacaan berurutan 1 per 1 (Suhu -> EC -> pH -> DO)
    snap.temperature = readTemperature();
    snap.conductivity = readConductivity();
    snap.ph = readPh();
    snap.dissolved_oxygen = readDissolvedOxygen();
    return snap;
}