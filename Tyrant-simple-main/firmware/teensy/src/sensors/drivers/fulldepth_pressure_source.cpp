#include "sensors/drivers/fulldepth_pressure_source.h"

#include <math.h>


namespace TyrantSensors
{

FullDepthPressureSource::FullDepthPressureSource(
    TwoWire &wire,
    uint32_t i2c_clock_hz,
    uint32_t sample_period_us
)
    :
    wire_(wire),
    i2c_clock_hz_(i2c_clock_hz),
    sample_period_us_(sample_period_us)
{
}


bool FullDepthPressureSource::begin()
{
    initialized_ = false;
    sample_available_ = false;

    sequence_ = 0;

    stats_ = {
        0,
        0,
        0
    };


    if (
        i2c_clock_hz_ == 0 ||
        sample_period_us_ == 0
    )
    {
        return false;
    }


    wire_.begin();
    wire_.setClock(
        i2c_clock_hz_
    );


    if (!sensor_.init(wire_))
    {
        return false;
    }


    // FullDepth 300 m hardware uses the MS5837-30BA family.
    // Set it explicitly instead of relying on auto-detection.
    sensor_.setModel(
        MS5837::MS5837_30BA
    );


    const uint32_t now_us =
        micros();

    last_read_us_ =
        now_us - sample_period_us_;

    initialized_ = true;

    return true;
}


bool FullDepthPressureSource::sampleDue(
    uint32_t now_us
) const
{
    return (
        static_cast<uint32_t>(
            now_us - last_read_us_
        ) >= sample_period_us_
    );
}


void FullDepthPressureSource::update()
{
    if (!initialized_)
    {
        return;
    }


    const uint32_t now_us =
        micros();


    if (!sampleDue(now_us))
    {
        return;
    }


    last_read_us_ =
        now_us;

    stats_.read_attempts++;


    // BlueRobotics MS5837 read() performs the complete blocking
    // pressure + temperature conversion. Production cadence is
    // intentionally throttled by sample_period_us_.
    sensor_.read();


    const float pressure_pa =
        sensor_.pressure(
            MS5837::Pa
        );

    const float temperature_c =
        sensor_.temperature();


    const bool valid =
        isfinite(pressure_pa) &&
        pressure_pa > 0.0f &&
        isfinite(temperature_c);


    sequence_++;

    sample_.sequence =
        sequence_;

    sample_.timestamp_us =
        micros();

    sample_.pressure_pa =
        pressure_pa;

    sample_.temperature_c =
        temperature_c;

    sample_.valid =
        valid;


    // Always expose the completed conversion to SensorManager.
    // Invalid samples are useful for telemetry/health diagnosis,
    // while SensorManager keeps them out of the processing stream.
    sample_available_ =
        true;

    stats_.samples_produced++;


    if (valid)
    {
        stats_.read_successes++;
    }
}


bool FullDepthPressureSource::takeSample(
    PressureSample &sample
)
{
    if (!sample_available_)
    {
        return false;
    }


    sample =
        sample_;

    sample_available_ =
        false;

    return true;
}


PressureSourceStats
FullDepthPressureSource::getStats() const
{
    return stats_;
}

} // namespace TyrantSensors
