#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <tyrant_payload_interfaces/msg/payload_water_quality.h>
#include "sensor_types.h"

class WaterQualityManager {
public:
    WaterQualityManager();
    void begin(uint8_t sda_pin = 8, uint8_t scl_pin = 9);
    void update();
    WaterQualitySnapshot readAll();
    
    // Fungsi langsung mengisi pesan ROS
    void populateRosMessage(tyrant_payload_interfaces__msg__PayloadWaterQuality &msg);

private:
    WaterQualitySnapshot current_data;
    enum EzoState { IDLE, WAITING_CONVERSION };

    // State machine EZO-pH (0x63)
    EzoState ph_state;
    unsigned long ph_timer;
    void requestPhReading();
    void fetchPhReading();

    // State machine EZO-EC (0x64)
    EzoState ec_state;
    unsigned long ec_timer;
    void requestEcReading();
    void fetchEcReading();

    // State machine EZO-DO (0x61)
    EzoState do_state;
    unsigned long do_timer;
    void requestDoReading();
    void fetchDoReading();

    // Suhu Analog Surveyor Kit (PIn 7)
    unsigned long temp_timer;
    void updateTemperature();
};