#include "ea_dsra.h"
#include "payload_config.h"
#include "payload_clock.h"
void EaDsraController::begin(float vmax, float vmin, float threshold, float e, float s, uint32_t tmin, uint32_t tmax) {
    v_max_=vmax; v_min_=vmin; soc_th_=threshold; e_=e; s_=s; min_=tmin; max_=tmax;
    voltage_seen_=false; covariance_=1; output_=EaDsraOutput{};
    for (auto &p : previous_) p=SensorData{};
}
EaDsraOutput EaDsraController::evaluate(const WaterQualitySnapshot &wq, float voltage) {
    output_=EaDsraOutput{};
    const bool battery_ok=isfinite(voltage) && voltage>0 && v_max_>v_min_;
    if (battery_ok) {
        if (!voltage_seen_) { estimate_=voltage; covariance_=1; voltage_seen_=true; }
        else {
            const float prior=covariance_+1e-5f;
            const float gain=prior/(prior+0.01f);
            estimate_+=gain*(voltage-estimate_); covariance_=(1-gain)*prior;
        }
        output_.v_filtered=estimate_;
        output_.soc=fmaxf(0, fminf(100, (estimate_-v_min_)/(v_max_-v_min_)*100));
        if (output_.soc<=soc_th_) {
            output_.w_ea=soc_th_/fmaxf(1, output_.soc); output_.is_penalty_active=true;
        }
    } else voltage_seen_=false;
    const SensorData samples[]={wq.ph, wq.conductivity, wq.temperature, wq.dissolved_oxygen};
    bool any_valid=false;
    for (unsigned i=0; i<4; ++i) {
        const auto &s=samples[i]; auto &p=previous_[i];
        const bool usable=s.valid && s.seen && isfinite(s.value) &&
            sampleAgeMs(s, payloadTimeUs())<=PayloadConfig::SENSOR_STALE_MS;
        if (!usable) { p=SensorData{}; continue; }
        any_valid=true;
        if (p.valid && s.last_sample_us>p.last_sample_us) {
            const float dt=(s.last_sample_us-p.last_sample_us)/1000000.0f;
            const float slope=fabsf(s.value-p.value)/dt/(i==1 ? 100.0f : 1.0f);
            output_.max_slope=fmaxf(output_.max_slope, slope);
        }
        p=s;
    }
    const float proposed=fmaxf(0.001f, e_-fabsf(s_*output_.max_slope))*1000;
    output_.tbm_dsra_ms=static_cast<uint32_t>(fmaxf(min_, fminf(max_, proposed)));
    const float adjusted=output_.tbm_dsra_ms*output_.w_ea;
    output_.t_ea_final_ms=static_cast<uint32_t>(fmaxf(min_, fminf(max_, adjusted)));
    // Unknown battery/data never justifies energy-based slowing; critical DO overrides penalty.
    if (!battery_ok || !any_valid || (wq.dissolved_oxygen.valid && wq.dissolved_oxygen.seen &&
        sampleAgeMs(wq.dissolved_oxygen, payloadTimeUs())<=PayloadConfig::SENSOR_STALE_MS &&
        wq.dissolved_oxygen.value<=PayloadConfig::CRITICAL_DO_MG_L)) output_.t_ea_final_ms=min_;
    return output_;
}
