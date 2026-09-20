#ifndef SENSOR_TYPES_H
#define SENSOR_TYPES_H

#include <Arduino.h>

// Definisi State Sesuai PRD Section 5.3
enum SensorState : uint8_t {
    STATE_NOT_INITIALIZED = 0,
    STATE_INITIALIZING    = 1,
    STATE_READY           = 2,
    STATE_STALE           = 3,
    STATE_ERROR           = 4
};

struct SensorData {
    float value;
    bool valid;
    SensorState state;
};

struct WaterQualitySnapshot {
    SensorData temperature;
    SensorData conductivity;
    SensorData ph;
    SensorData dissolved_oxygen;
};

#endif