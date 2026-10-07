#include "ea_dsra.h"

EaDsraController::EaDsraController()
    : v_max_nominal(25.2f), v_min_nominal(19.8f), soc_threshold(30.0f),
      param_e(5.0f), param_s(2.0f), epsilon(0.001f),
      t_min(1000), t_max(5000),
      x_hat(24.0f), p_cov(1.0f), q_cov(1e-5f), r_cov(0.01f),
      is_first_sample(true), prev_sample_time_ms(0),
      prev_ph(7.0f), prev_ec(0.0f), prev_do(0.0f), prev_temp(25.0f) {
    last_output = {24.0f, 100.0f, 1.0f, 0.0f, 1000, 1000, false};
}

void EaDsraController::begin(float v_max, float v_min, float soc_th, 
                            float e_param, float s_param, 
                            uint32_t t_min_ms, uint32_t t_max_ms) {
    v_max_nominal = v_max;
    v_min_nominal = v_min;
    soc_threshold = soc_th;
    param_e = e_param;
    param_s = s_param;
    t_min = t_min_ms;
    t_max = t_max_ms;
    is_first_sample = true;
}

EaDsraOutput EaDsraController::evaluate(const WaterQualitySnapshot &wq, float raw_v_bat) {
    unsigned long now_ms = millis();

    //  1: Filter Kalman 1D untuk estimasi baterai
    if (is_first_sample) {
        x_hat = raw_v_bat;
        p_cov = 1.0f;
    } else {
        // 1. Tahap Prediksi
        float x_hat_minus = x_hat;
        float p_minus = p_cov + q_cov;

        // 2. Tahap Koreksi
        float kalman_gain = p_minus / (p_minus + r_cov);
        x_hat = x_hat_minus + kalman_gain * (raw_v_bat - x_hat_minus);
        p_cov = (1.0f - kalman_gain) * p_minus;
    }

    //  2: Konversi Tegangan hasil filter  ke SOC
    float soc_calc = ((x_hat - v_min_nominal) / (v_max_nominal - v_min_nominal)) * 100.0f;
    if (soc_calc > 100.0f) soc_calc = 100.0f;
    if (soc_calc < 0.0f) soc_calc = 0.0f;

    //  3: DSRA Standar
    float dt = (now_ms - prev_sample_time_ms) / 1000.0f;
    float max_slope = 0.0f;

    if (!is_first_sample && dt > 0.05f) {
        // Hitung laju perubahan (slope) untuk tiap sensor yang valid
        if (wq.ph.valid) {
            float s_ph = fabsf(wq.ph.value - prev_ph) / dt;
            if (s_ph > max_slope) max_slope = s_ph;
        }
        if (wq.dissolved_oxygen.valid) {
            float s_do = fabsf(wq.dissolved_oxygen.value - prev_do) / dt;
            if (s_do > max_slope) max_slope = s_do;
        }
        if (wq.temperature.valid) {
            float s_temp = fabsf(wq.temperature.value - prev_temp) / dt;
            if (s_temp > max_slope) max_slope = s_temp;
        }
        if (wq.conductivity.valid) {
            // Skalakan konduktivitas (uS/cm dibagi 100) agar setara dengan bobot parameter lain
            float s_ec = (fabsf(wq.conductivity.value - prev_ec) / 100.0f) / dt;
            if (s_ec > max_slope) max_slope = s_ec;
        }
    }

    // Update histori data
    if (wq.ph.valid) prev_ph = wq.ph.value;
    if (wq.dissolved_oxygen.valid) prev_do = wq.dissolved_oxygen.value;
    if (wq.temperature.valid) prev_temp = wq.temperature.value;
    if (wq.conductivity.valid) prev_ec = wq.conductivity.value;
    prev_sample_time_ms = now_ms;
    is_first_sample = false;

    // Hitung TBMcalc
    float tbm_calc_sec = param_e - fabsf(param_s * max_slope);
    if (tbm_calc_sec < epsilon) tbm_calc_sec = epsilon;

    // Clamping DSRA standar ke rentang [t_min, t_max]
    uint32_t tbm_calc_ms = (uint32_t)(tbm_calc_sec * 1000.0f);
    uint32_t tbm_dsra_ms = tbm_calc_ms;
    if (tbm_dsra_ms > t_max) tbm_dsra_ms = t_max;
    if (tbm_dsra_ms < t_min) tbm_dsra_ms = t_min;

    // BLOK 4: Energy-Aware Modulation (EA-DSRA)
    float w_ea = 1.0f;
    bool penalty_active = false;

    if (soc_calc <= soc_threshold) {
        // Hindari pembagian dengan nol jika baterai drop ekstrem
        float safe_soc = (soc_calc < 1.0f) ? 1.0f : soc_calc;
        w_ea = soc_threshold / safe_soc;
        penalty_active = true;
    } else {
        w_ea = 1.0f;
    }

    // T_ea^calc = TBM_DSRA * W_ea
    float t_ea_calc_ms = (float)tbm_dsra_ms * w_ea;

    // Clamping final T_ea ke rentang [t_min, t_max]
    uint32_t t_ea_final_ms = (uint32_t)t_ea_calc_ms;
    if (t_ea_final_ms > t_max) t_ea_final_ms = t_max;
    if (t_ea_final_ms < t_min) t_ea_final_ms = t_min;

    // save ke output
    last_output.v_filtered = x_hat;
    last_output.soc = soc_calc;
    last_output.w_ea = w_ea;
    last_output.max_slope = max_slope;
    last_output.tbm_dsra_ms = tbm_dsra_ms;
    last_output.t_ea_final_ms = t_ea_final_ms;
    last_output.is_penalty_active = penalty_active;

    return last_output;
}