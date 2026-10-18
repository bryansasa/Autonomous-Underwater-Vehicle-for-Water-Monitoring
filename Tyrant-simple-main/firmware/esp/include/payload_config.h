#pragma once
#include <stdint.h>

// EDIT DI SINI: nomor GPIO sementara, sesuaikan dengan board/kabel aktual.
namespace PayloadConfig {
#ifdef PAYLOAD_SIMULATION
constexpr const char *ROS_NAMESPACE = "/tyrant/payload_sim";
constexpr const char *ROS_NODE_NAME = "tyrant_payload_esp32_sim";
#else
constexpr const char *ROS_NAMESPACE = "/tyrant/payload";
constexpr const char *ROS_NODE_NAME = "tyrant_payload_esp32";
#endif
// I2C pertama: EZO EC, pH, DO dan INA226 rel sensor.
constexpr int I2C_PAYLOAD_SDA = 8;
constexpr int I2C_PAYLOAD_SCL = 9;
// I2C kedua: INA226 thruster / board power 6S.
constexpr int I2C_POWER_SDA = 10;
constexpr int I2C_POWER_SCL = 11;
constexpr int TEMPERATURE_ADC = 7;
constexpr int MOSFET_EC = 4;
constexpr int MOSFET_PH = 5;
constexpr int MOSFET_TEMPERATURE = 6;
constexpr int MOSFET_DO = 15;
constexpr bool MOSFET_ACTIVE_HIGH = true;
constexpr uint32_t I2C_HZ = 100000;
constexpr uint16_t I2C_TIMEOUT_MS = 20;
constexpr uint8_t EC_ADDRESS = 0x64;
constexpr uint8_t PH_ADDRESS = 0x63;
constexpr uint8_t DO_ADDRESS = 0x61;
constexpr uint8_t SENSOR_INA_ADDRESS = 0x40;
constexpr uint8_t THRUSTER_INA_ADDRESS = 0x40;
constexpr float SENSOR_SHUNT_OHM = 0.1f; // R100
constexpr float THRUSTER_SHUNT_OHM = 0.075f / 200.0f; // 200 A / 75 mV
// Model suhu belum dikonfirmasi; kandidat rumus Surveyor tidak dianggap valid.
constexpr bool TEMPERATURE_CALIBRATION_CONFIRMED = false;
constexpr float TEMPERATURE_OFFSET_V = 1.058f;
constexpr float TEMPERATURE_V_PER_C = 0.009f;
constexpr float TEMPERATURE_MIN_V = 0.5f;
constexpr float TEMPERATURE_MAX_V = 3.1f;
constexpr uint32_t SENSOR_WARMUP_MS = 1500;
constexpr uint32_t SENSOR_STALE_MS = 6500;
constexpr uint32_t EZO_CONVERSION_MS = 900;
constexpr uint32_t EZO_TIMEOUT_MS = 1500;
constexpr uint32_t HEARTBEAT_TIMEOUT_MS = 1000;
constexpr uint32_t AGENT_PING_INTERVAL_MS = 500;
constexpr int AGENT_PING_TIMEOUT_MS = 100;
constexpr uint8_t AGENT_MISSED_PROBES = 3;
constexpr int RELIABLE_PUBLISH_TIMEOUT_MS = 100;
constexpr uint32_t PUBLISH_FAILURE_GRACE_MS = 3000;
constexpr uint32_t MIN_SAMPLE_INTERVAL_MS = 1000;
constexpr uint32_t MAX_SAMPLE_INTERVAL_MS = 5000;
constexpr float BATTERY_FULL_V = 25.2f;
constexpr float BATTERY_EMPTY_V = 19.8f;
constexpr float CRITICAL_DO_MG_L = 2.0f;
// Kontrak host belum diubah. Topic relatif terhadap /tyrant/payload.
constexpr const char* HOST_HEARTBEAT_TOPIC = "host_heartbeat";
constexpr uint32_t ROS_DOMAIN_ID = 0;

constexpr int PINS[] = {I2C_PAYLOAD_SDA, I2C_PAYLOAD_SCL, I2C_POWER_SDA,
    I2C_POWER_SCL, TEMPERATURE_ADC, MOSFET_EC, MOSFET_PH,
    MOSFET_TEMPERATURE, MOSFET_DO};
constexpr bool pinsUnique(unsigned i = 0, unsigned j = 1) {
    return i >= sizeof(PINS)/sizeof(PINS[0]) ? true :
        j >= sizeof(PINS)/sizeof(PINS[0]) ? pinsUnique(i+1, i+2) :
        PINS[i] != PINS[j] && pinsUnique(i, j+1);
}
static_assert(pinsUnique(), "GPIO payload bertabrakan: periksa payload_config.h");
static_assert(TEMPERATURE_ADC >= 1 && TEMPERATURE_ADC <= 10,
              "Pilih pin ADC1 ESP32-S3 GPIO 1..10 untuk suhu");
}
