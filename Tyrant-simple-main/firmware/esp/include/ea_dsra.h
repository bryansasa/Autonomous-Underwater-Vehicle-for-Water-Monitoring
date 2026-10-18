#pragma once
#include "sensor_types.h"
struct EaDsraOutput {
    float v_filtered = NAN, soc = NAN, w_ea = 1, max_slope = 0;
    uint32_t tbm_dsra_ms = 1000, t_ea_final_ms = 1000;
    bool is_penalty_active = false;
};
class EaDsraController {
public:
    void begin(float v_max=25.2f, float v_min=19.8f, float soc_th=30.0f,
        float e_param=5.0f, float s_param=2.0f, uint32_t t_min_ms=1000, uint32_t t_max_ms=5000);
    EaDsraOutput evaluate(const WaterQualitySnapshot &wq, float raw_battery_voltage);
    EaDsraOutput getLastOutput() const { return output_; }
private:
    float v_max_=25.2f, v_min_=19.8f, soc_th_=30, e_=5, s_=2;
    uint32_t min_=1000, max_=5000;
    float estimate_=NAN, covariance_=1;
    bool voltage_seen_=false;
    SensorData previous_[4];
    EaDsraOutput output_;
};
