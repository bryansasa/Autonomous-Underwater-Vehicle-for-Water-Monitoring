#ifndef WATER_QUALITY_LIB_H
#define WATER_QUALITY_LIB_H

#include "sensor_types.h"

class WaterQualityManager {
public:
    WaterQualityManager();
    void begin();
    WaterQualitySnapshot readAll();

private:
    SensorData readTemperature();
    SensorData readConductivity();
    SensorData readPh();
    SensorData readDissolvedOxygen();

    // Nilai dummy simulasi
    float dummy_temp;
    float dummy_ec;
    float dummy_ph;
    float dummy_do;
};

#endif