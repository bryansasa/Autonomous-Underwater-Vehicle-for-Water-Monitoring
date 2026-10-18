#include "estimation/simple_state_estimator.h"

#include <math.h>

namespace
{
constexpr float PI_F = 3.14159265358979323846f;
constexpr float TWO_PI_F = 2.0f * PI_F;
constexpr float MIN_HORIZONTAL_FIELD_SQUARED = 1.0e-12f;

TyrantSimpleEstimator::Config runtime_config {};
bool config_valid = false;
bool estimator_initialized = false;
bool fault_latched = false;

TyrantSimpleEstimator::State current_state {};

uint32_t last_imu_timestamp_us = 0;
bool timing_baseline_valid = false;

uint32_t last_heading_timestamp_us = 0;
bool heading_seen = false;

uint32_t last_depth_timestamp_us = 0;
bool depth_seen = false;

uint32_t last_mag_sequence = 0;
bool mag_sequence_seen = false;

uint32_t stationary_sample_count = 0;
TyrantSimpleEstimator::Vector3 accel_sum_b {};
TyrantSimpleEstimator::Vector3 gyro_sum_b {};
TyrantSimpleEstimator::Vector3 fixed_gyro_bias_b {};

// Covariance for state [yaw, yaw_rate_bias].
float yaw_cov_00 = 0.0f;
float yaw_cov_01 = 0.0f;
float yaw_cov_10 = 0.0f;
float yaw_cov_11 = 0.0f;


// ============================================================
// BASIC HELPERS
// ============================================================

float wrapAngleRad(float angle_rad)
{
    if (!isfinite(angle_rad))
    {
        return NAN;
    }

    float wrapped = fmodf(angle_rad + PI_F, TWO_PI_F);
    if (wrapped < 0.0f)
    {
        wrapped += TWO_PI_F;
    }
    return wrapped - PI_F;
}

bool finitePositive(float value)
{
    return isfinite(value) && value > 0.0f;
}

bool finiteNonNegative(float value)
{
    return isfinite(value) && value >= 0.0f;
}

bool vectorFinite(const TyrantSimpleEstimator::Vector3 &value)
{
    return isfinite(value.x) && isfinite(value.y) && isfinite(value.z);
}

float vectorNorm(const TyrantSimpleEstimator::Vector3 &value)
{
    return sqrtf(value.x * value.x + value.y * value.y + value.z * value.z);
}

bool configValid(const TyrantSimpleEstimator::Config &config)
{
    if (
        config.required_stationary_samples == 0 ||
        !finitePositive(config.gravity_mps2) ||
        !finitePositive(config.accel_norm_tolerance_mps2) ||
        !finitePositive(config.max_stationary_gyro_norm_rad_s) ||
        !finitePositive(config.max_dt_s) ||
        !finitePositive(config.roll_pitch_time_constant_s) ||
        !finiteNonNegative(config.yaw_initial_variance_rad2) ||
        !finiteNonNegative(config.yaw_rate_bias_initial_variance_rad2ps2) ||
        !finiteNonNegative(config.yaw_process_noise_rad2_per_s) ||
        !finiteNonNegative(config.yaw_rate_bias_process_noise_rad2ps3) ||
        !finitePositive(config.yaw_measurement_variance_rad2) ||
        !finitePositive(config.min_abs_cos_pitch) ||
        config.min_abs_cos_pitch >= 1.0f ||
        config.heading_timeout_us == 0 ||
        config.depth_timeout_us == 0)
    {
        return false;
    }

    const auto &cal = config.magnetometer_calibration;
    if (!vectorFinite(cal.hard_iron_offset_lsb))
    {
        return false;
    }

    for (size_t row = 0; row < 3; ++row)
    {
        for (size_t column = 0; column < 3; ++column)
        {
            if (!isfinite(cal.soft_iron[row][column]))
            {
                return false;
            }
        }
    }

    return true;
}

void clearStationaryAccumulator()
{
    stationary_sample_count = 0;
    accel_sum_b = {0.0f, 0.0f, 0.0f};
    gyro_sum_b = {0.0f, 0.0f, 0.0f};
}

bool fresh(
    bool seen,
    uint32_t last_timestamp_us,
    uint32_t now_us,
    uint32_t timeout_us)
{
    return seen &&
        static_cast<uint32_t>(now_us - last_timestamp_us) <= timeout_us;
}

void latchFault()
{
    fault_latched = true;
    current_state.status = TyrantSimpleEstimator::Status::FAULT;
    current_state.attitude_valid = false;
}


// ============================================================
// ATTITUDE OBSERVATIONS
// ============================================================

bool accelRollPitch(
    const TyrantSimpleEstimator::Vector3 &accel_b,
    float &roll_rad,
    float &pitch_rad)
{
    if (!vectorFinite(accel_b))
    {
        return false;
    }

    // BODY FRD, stationary specific force approximately [0,0,-g].
    const float roll = atan2f(-accel_b.y, -accel_b.z);
    const float yz_norm = sqrtf(accel_b.y * accel_b.y + accel_b.z * accel_b.z);
    const float pitch = atan2f(accel_b.x, yz_norm);

    if (!isfinite(roll) || !isfinite(pitch))
    {
        return false;
    }

    roll_rad = roll;
    pitch_rad = pitch;
    return true;
}

bool applyMagCalibration(
    const TyrantSimpleEstimator::Vector3 &raw,
    TyrantSimpleEstimator::Vector3 &corrected)
{
    const auto &cal = runtime_config.magnetometer_calibration;

    const TyrantSimpleEstimator::Vector3 centered {
        raw.x - cal.hard_iron_offset_lsb.x,
        raw.y - cal.hard_iron_offset_lsb.y,
        raw.z - cal.hard_iron_offset_lsb.z
    };

    corrected.x =
        cal.soft_iron[0][0] * centered.x +
        cal.soft_iron[0][1] * centered.y +
        cal.soft_iron[0][2] * centered.z;

    corrected.y =
        cal.soft_iron[1][0] * centered.x +
        cal.soft_iron[1][1] * centered.y +
        cal.soft_iron[1][2] * centered.z;

    corrected.z =
        cal.soft_iron[2][0] * centered.x +
        cal.soft_iron[2][1] * centered.y +
        cal.soft_iron[2][2] * centered.z;

    return vectorFinite(corrected);
}

bool magneticYaw(
    const TyrantSensors::ImuSample &sample,
    float roll_rad,
    float pitch_rad,
    float &yaw_rad)
{
    if (!sample.mag_valid)
    {
        return false;
    }

    TyrantSimpleEstimator::Vector3 calibrated {};
    const TyrantSimpleEstimator::Vector3 raw {
        static_cast<float>(sample.mag_x_lsb),
        static_cast<float>(sample.mag_y_lsb),
        static_cast<float>(sample.mag_z_lsb)
    };

    if (!applyMagCalibration(raw, calibrated))
    {
        return false;
    }

    const float sin_roll = sinf(roll_rad);
    const float cos_roll = cosf(roll_rad);
    const float sin_pitch = sinf(pitch_rad);
    const float cos_pitch = cosf(pitch_rad);

    if (
        !isfinite(sin_roll) || !isfinite(cos_roll) ||
        !isfinite(sin_pitch) || !isfinite(cos_pitch) ||
        fabsf(cos_pitch) < runtime_config.min_abs_cos_pitch)
    {
        return false;
    }

    // BODY FRD / NAV NED-like tilt compensation.
    const float horizontal_x =
        cos_pitch * calibrated.x +
        sin_pitch * sin_roll * calibrated.y +
        sin_pitch * cos_roll * calibrated.z;

    const float horizontal_y =
        cos_roll * calibrated.y -
        sin_roll * calibrated.z;

    const float horizontal_squared =
        horizontal_x * horizontal_x + horizontal_y * horizontal_y;

    if (!isfinite(horizontal_squared) ||
        horizontal_squared <= MIN_HORIZONTAL_FIELD_SQUARED)
    {
        return false;
    }

    // Positive yaw clockwise viewed from above in NED-like convention.
    const float yaw = wrapAngleRad(atan2f(-horizontal_y, horizontal_x));
    if (!isfinite(yaw))
    {
        return false;
    }

    yaw_rad = yaw;
    return true;
}


// ============================================================
// INITIALIZATION
// ============================================================

bool initializeFromStationarySample(const TyrantSensors::ImuSample &sample)
{
    const TyrantSimpleEstimator::Vector3 accel_b {
        sample.accel_x, sample.accel_y, sample.accel_z
    };
    const TyrantSimpleEstimator::Vector3 gyro_b {
        sample.gyro_x, sample.gyro_y, sample.gyro_z
    };

    const float accel_norm = vectorNorm(accel_b);
    const float gyro_norm = vectorNorm(gyro_b);

    if (!isfinite(accel_norm) || !isfinite(gyro_norm))
    {
        return false;
    }

    const bool stationary =
        fabsf(accel_norm - runtime_config.gravity_mps2) <=
            runtime_config.accel_norm_tolerance_mps2 &&
        gyro_norm <= runtime_config.max_stationary_gyro_norm_rad_s;

    if (!stationary)
    {
        clearStationaryAccumulator();
        return false;
    }

    if (stationary_sample_count < runtime_config.required_stationary_samples)
    {
        accel_sum_b.x += accel_b.x;
        accel_sum_b.y += accel_b.y;
        accel_sum_b.z += accel_b.z;

        gyro_sum_b.x += gyro_b.x;
        gyro_sum_b.y += gyro_b.y;
        gyro_sum_b.z += gyro_b.z;

        ++stationary_sample_count;
    }

    if (stationary_sample_count < runtime_config.required_stationary_samples)
    {
        return false;
    }

    const float inverse_count = 1.0f / static_cast<float>(stationary_sample_count);

    const TyrantSimpleEstimator::Vector3 mean_accel_b {
        accel_sum_b.x * inverse_count,
        accel_sum_b.y * inverse_count,
        accel_sum_b.z * inverse_count
    };

    fixed_gyro_bias_b = {
        gyro_sum_b.x * inverse_count,
        gyro_sum_b.y * inverse_count,
        gyro_sum_b.z * inverse_count
    };

    float roll = 0.0f;
    float pitch = 0.0f;
    float yaw = 0.0f;

    if (!accelRollPitch(mean_accel_b, roll, pitch) ||
        !magneticYaw(sample, roll, pitch, yaw))
    {
        return false;
    }

    current_state.roll_rad = roll;
    current_state.pitch_rad = pitch;
    current_state.yaw_rad = yaw;
    current_state.angular_velocity_b_rad_s = {0.0f, 0.0f, 0.0f};
    current_state.yaw_rate_bias_rad_s = 0.0f;
    current_state.attitude_valid = true;
    current_state.heading_valid = true;
    current_state.status = TyrantSimpleEstimator::Status::RUNNING;

    yaw_cov_00 = runtime_config.yaw_initial_variance_rad2;
    yaw_cov_01 = 0.0f;
    yaw_cov_10 = 0.0f;
    yaw_cov_11 = runtime_config.yaw_rate_bias_initial_variance_rad2ps2;

    last_imu_timestamp_us = static_cast<uint32_t>(sample.timestamp_us);
    timing_baseline_valid = true;

    last_heading_timestamp_us = static_cast<uint32_t>(sample.timestamp_us);
    heading_seen = true;

    last_mag_sequence = sample.mag_sequence;
    mag_sequence_seen = true;

    estimator_initialized = true;
    return true;
}


// ============================================================
// ROLL / PITCH COMPLEMENTARY FILTER
// ============================================================

bool updateRollPitch(
    const TyrantSimpleEstimator::Vector3 &corrected_gyro_b,
    const TyrantSimpleEstimator::Vector3 &accel_b,
    float dt_s,
    bool &accel_correction_used)
{
    accel_correction_used = false;

    const float roll = current_state.roll_rad;
    const float pitch = current_state.pitch_rad;

    const float sin_roll = sinf(roll);
    const float cos_roll = cosf(roll);
    const float cos_pitch = cosf(pitch);

    if (!isfinite(sin_roll) || !isfinite(cos_roll) ||
        !isfinite(cos_pitch) ||
        fabsf(cos_pitch) < runtime_config.min_abs_cos_pitch)
    {
        return false;
    }

    const float tan_pitch = tanf(pitch);
    const float p = corrected_gyro_b.x;
    const float q = corrected_gyro_b.y;
    const float r = corrected_gyro_b.z;

    const float roll_rate =
        p + q * sin_roll * tan_pitch + r * cos_roll * tan_pitch;
    const float pitch_rate = q * cos_roll - r * sin_roll;

    float predicted_roll = wrapAngleRad(roll + roll_rate * dt_s);
    float predicted_pitch = pitch + pitch_rate * dt_s;

    if (!isfinite(predicted_roll) || !isfinite(predicted_pitch))
    {
        return false;
    }

    const float accel_norm = vectorNorm(accel_b);
    const bool accel_usable =
        isfinite(accel_norm) &&
        fabsf(accel_norm - runtime_config.gravity_mps2) <=
            runtime_config.accel_norm_tolerance_mps2;

    if (accel_usable)
    {
        float accel_roll = 0.0f;
        float accel_pitch = 0.0f;

        if (!accelRollPitch(accel_b, accel_roll, accel_pitch))
        {
            return false;
        }

        const float alpha =
            runtime_config.roll_pitch_time_constant_s /
            (runtime_config.roll_pitch_time_constant_s + dt_s);

        predicted_roll = wrapAngleRad(
            predicted_roll +
            (1.0f - alpha) * wrapAngleRad(accel_roll - predicted_roll));

        predicted_pitch =
            alpha * predicted_pitch +
            (1.0f - alpha) * accel_pitch;

        accel_correction_used = true;
    }

    current_state.roll_rad = predicted_roll;
    current_state.pitch_rad = predicted_pitch;
    return true;
}


// ============================================================
// TWO-STATE YAW KALMAN FILTER
// ============================================================

bool predictYaw(
    const TyrantSimpleEstimator::Vector3 &corrected_gyro_b,
    float dt_s)
{
    const float roll = current_state.roll_rad;
    const float pitch = current_state.pitch_rad;

    const float sin_roll = sinf(roll);
    const float cos_roll = cosf(roll);
    const float cos_pitch = cosf(pitch);

    if (!isfinite(sin_roll) || !isfinite(cos_roll) ||
        !isfinite(cos_pitch) ||
        fabsf(cos_pitch) < runtime_config.min_abs_cos_pitch)
    {
        return false;
    }

    const float yaw_rate_measured =
        (corrected_gyro_b.y * sin_roll +
         corrected_gyro_b.z * cos_roll) /
        cos_pitch;

    if (!isfinite(yaw_rate_measured))
    {
        return false;
    }

    current_state.yaw_rad = wrapAngleRad(
        current_state.yaw_rad +
        (yaw_rate_measured - current_state.yaw_rate_bias_rad_s) * dt_s);

    // F = [1 -dt; 0 1]
    const float prior_00 =
        yaw_cov_00 - dt_s * yaw_cov_10 - dt_s * yaw_cov_01 +
        dt_s * dt_s * yaw_cov_11 +
        runtime_config.yaw_process_noise_rad2_per_s * dt_s;

    const float prior_01 = yaw_cov_01 - dt_s * yaw_cov_11;
    const float prior_10 = yaw_cov_10 - dt_s * yaw_cov_11;
    const float prior_11 =
        yaw_cov_11 +
        runtime_config.yaw_rate_bias_process_noise_rad2ps3 * dt_s;

    if (!isfinite(prior_00) || !isfinite(prior_01) ||
        !isfinite(prior_10) || !isfinite(prior_11) ||
        prior_00 < 0.0f || prior_11 < 0.0f)
    {
        return false;
    }

    yaw_cov_00 = prior_00;
    yaw_cov_01 = 0.5f * (prior_01 + prior_10);
    yaw_cov_10 = yaw_cov_01;
    yaw_cov_11 = prior_11;

    return isfinite(current_state.yaw_rad);
}

bool correctYaw(float measured_yaw_rad)
{
    const float measurement_variance = runtime_config.yaw_measurement_variance_rad2;
    const float innovation_variance = yaw_cov_00 + measurement_variance;

    if (!finitePositive(innovation_variance))
    {
        return false;
    }

    const float innovation = wrapAngleRad(measured_yaw_rad - current_state.yaw_rad);
    const float k0 = yaw_cov_00 / innovation_variance;
    const float k1 = yaw_cov_10 / innovation_variance;

    if (!isfinite(innovation) || !isfinite(k0) || !isfinite(k1))
    {
        return false;
    }

    current_state.yaw_rad = wrapAngleRad(
        current_state.yaw_rad + k0 * innovation);
    current_state.yaw_rate_bias_rad_s += k1 * innovation;

    // Joseph covariance update, H = [1 0].
    const float p00 = yaw_cov_00;
    const float p01 = yaw_cov_01;
    const float p10 = yaw_cov_10;
    const float p11 = yaw_cov_11;
    const float a = 1.0f - k0;

    const float updated_00 =
        a * a * p00 + k0 * k0 * measurement_variance;
    const float updated_01 =
        a * (p01 - k1 * p00) + k0 * k1 * measurement_variance;
    const float updated_11 =
        k1 * k1 * p00 - k1 * p01 - k1 * p10 + p11 +
        k1 * k1 * measurement_variance;

    if (!isfinite(updated_00) || !isfinite(updated_01) ||
        !isfinite(updated_11) ||
        updated_00 < 0.0f || updated_11 < 0.0f ||
        !isfinite(current_state.yaw_rad) ||
        !isfinite(current_state.yaw_rate_bias_rad_s))
    {
        return false;
    }

    yaw_cov_00 = updated_00;
    yaw_cov_01 = updated_01;
    yaw_cov_10 = updated_01;
    yaw_cov_11 = updated_11;
    return true;
}

} // namespace

namespace TyrantSimpleEstimator
{

void reset()
{
    config_valid = false;
    estimator_initialized = false;
    fault_latched = false;

    current_state = {};
    current_state.status = Status::INITIALIZING;

    last_imu_timestamp_us = 0;
    timing_baseline_valid = false;
    last_heading_timestamp_us = 0;
    heading_seen = false;
    last_depth_timestamp_us = 0;
    depth_seen = false;
    last_mag_sequence = 0;
    mag_sequence_seen = false;

    fixed_gyro_bias_b = {};
    yaw_cov_00 = 0.0f;
    yaw_cov_01 = 0.0f;
    yaw_cov_10 = 0.0f;
    yaw_cov_11 = 0.0f;

    clearStationaryAccumulator();
}

void init(const Config &config)
{
    reset();
    runtime_config = config;
    config_valid = configValid(runtime_config);

    if (!config_valid)
    {
        latchFault();
    }
}

bool initialized()
{
    return estimator_initialized && !fault_latched;
}

ImuUpdateResult processImuSample(const TyrantSensors::ImuSample &sample)
{
    ImuUpdateResult result {
        ImuUpdateStatus::INVALID_INPUT,
        false,
        false
    };

    if (!config_valid)
    {
        result.status = ImuUpdateStatus::INVALID_CONFIG;
        return result;
    }

    if (fault_latched)
    {
        result.status = ImuUpdateStatus::FAULT_LATCHED;
        return result;
    }

    const Vector3 accel_b {sample.accel_x, sample.accel_y, sample.accel_z};
    const Vector3 gyro_b {sample.gyro_x, sample.gyro_y, sample.gyro_z};

    if (!sample.valid || !vectorFinite(accel_b) || !vectorFinite(gyro_b))
    {
        result.status = ImuUpdateStatus::INVALID_INPUT;
        return result;
    }

    if (!estimator_initialized)
    {
        if (initializeFromStationarySample(sample))
        {
            result.status = ImuUpdateStatus::INITIALIZED;
            result.magnetometer_correction_used = true;
        }
        else
        {
            result.status = ImuUpdateStatus::INITIALIZING;
        }
        return result;
    }

    const uint32_t timestamp_us = static_cast<uint32_t>(sample.timestamp_us);
    const uint32_t dt_us = static_cast<uint32_t>(timestamp_us - last_imu_timestamp_us);

    if (dt_us == 0)
    {
        result.status = ImuUpdateStatus::DUPLICATE_TIMESTAMP;
        return result;
    }

    last_imu_timestamp_us = timestamp_us;
    timing_baseline_valid = true;

    const float dt_s = static_cast<float>(dt_us) * 1.0e-6f;
    if (!isfinite(dt_s) || dt_s <= 0.0f)
    {
        result.status = ImuUpdateStatus::INVALID_INPUT;
        return result;
    }

    if (dt_s > runtime_config.max_dt_s)
    {
        current_state.status = Status::DEGRADED;
        result.status = ImuUpdateStatus::GAP_TOO_LARGE;
        return result;
    }

    const Vector3 corrected_gyro_b {
        gyro_b.x - fixed_gyro_bias_b.x,
        gyro_b.y - fixed_gyro_bias_b.y,
        gyro_b.z - fixed_gyro_bias_b.z
    };

    current_state.angular_velocity_b_rad_s = corrected_gyro_b;

    bool accel_correction_used = false;
    if (!updateRollPitch(corrected_gyro_b, accel_b, dt_s, accel_correction_used) ||
        !predictYaw(corrected_gyro_b, dt_s))
    {
        latchFault();
        result.status = ImuUpdateStatus::NUMERICAL_FAILURE;
        return result;
    }

    result.accel_correction_used = accel_correction_used;

    const bool new_mag_sample =
        sample.mag_valid &&
        (!mag_sequence_seen || sample.mag_sequence != last_mag_sequence);

    if (new_mag_sample)
    {
        last_mag_sequence = sample.mag_sequence;
        mag_sequence_seen = true;

        float measured_yaw = 0.0f;
        if (magneticYaw(sample, current_state.roll_rad, current_state.pitch_rad, measured_yaw))
        {
            if (!correctYaw(measured_yaw))
            {
                latchFault();
                result.status = ImuUpdateStatus::NUMERICAL_FAILURE;
                return result;
            }

            last_heading_timestamp_us = timestamp_us;
            heading_seen = true;
            result.magnetometer_correction_used = true;
        }
    }

    current_state.attitude_valid = true;
    current_state.status = Status::RUNNING;
    result.status = ImuUpdateStatus::UPDATED;
    return result;
}

void processDepthMeasurement(const TyrantSensors::DepthMeasurement &measurement)
{
    if (fault_latched || !measurement.valid || !isfinite(measurement.depth_m))
    {
        return;
    }

    current_state.depth_m = measurement.depth_m;
    last_depth_timestamp_us = static_cast<uint32_t>(measurement.timestamp_us);
    depth_seen = true;
}

bool getState(State &state, uint32_t now_us)
{
    if (!estimator_initialized || fault_latched)
    {
        state = current_state;
        return false;
    }

    current_state.heading_valid = fresh(
        heading_seen,
        last_heading_timestamp_us,
        now_us,
        runtime_config.heading_timeout_us);

    current_state.depth_valid = fresh(
        depth_seen,
        last_depth_timestamp_us,
        now_us,
        runtime_config.depth_timeout_us);

    current_state.status = current_state.heading_valid
        ? Status::RUNNING
        : Status::DEGRADED;

    state = current_state;
    return current_state.attitude_valid;
}

} // namespace TyrantSimpleEstimator
