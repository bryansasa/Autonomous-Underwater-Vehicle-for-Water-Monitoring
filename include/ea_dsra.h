#pragma once
#include <Arduino.h>
#include "sensor_types.h"

struct EaDsraOutput {
    float v_filtered;             // Tegangan baterai hasil Filter Kalman 1D
    float soc;                    // State of Charge
    float w_ea;                   // Faktor penalti energi
    float max_slope;              // Slope terbesar
    uint32_t tbm_dsra_ms;         // Interval sebelum penalti energi (ms)
    uint32_t t_ea_final_ms;       // Interval pencuplikan adaptif final (ms)
    bool is_penalty_active;       // Flag indikator SoC <= SoC_th
};

class EaDsraController {
public:
    EaDsraController();

    // Inisialisasi parameter
    void begin(
        float v_max = 25.2f,        // LiPo 6S penuh (4.2V/sel)
        float v_min = 19.8f,        // Batas kritis cut-off LiPo 6S (3.3V/sel)
        float soc_th = 30.0f,       // Ambang kritis SoCth (30%)
        float e_param = 5.0f,       // Parameter Eksplorasi E (detik)
        float s_param = 2.0f,       // Parameter Sensitivitas S
        uint32_t t_min_ms = 1000,   // t_min (1000 ms)
        uint32_t t_max_ms = 5000    // t_max (5000 ms)
    );

    // Eksekusi utama
    EaDsraOutput evaluate(const WaterQualitySnapshot &current_wq, float raw_battery_voltage);

    EaDsraOutput getLastOutput() const { return last_output; }

private:
    // Parameter baterai & threshold
    float v_max_nominal;
    float v_min_nominal;
    float soc_threshold;

    // Parameter DSRA standar
    float param_e;
    float param_s;
    float epsilon;
    uint32_t t_min;
    uint32_t t_max;

    // State Filter Kalman 1D (Blok 1)
    float x_hat;      // Estimasi tegangan
    float p_cov;      // Kovariansi galat
    float q_cov;      // Process Noise Covariance (1e-5)
    float r_cov;      // Measurement Noise Covariance (0.01)

    // Histori 
    bool is_first_sample;
    unsigned long prev_sample_time_ms;
    float prev_ph;
    float prev_ec;
    float prev_do;
    float prev_temp;

    EaDsraOutput last_output;
};