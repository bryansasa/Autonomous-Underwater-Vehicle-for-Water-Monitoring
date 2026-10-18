#include "actuation/thruster_output_mapper.h"

#include <math.h>

namespace
{
float clampUnit(float value)
{
    if (value > 1.0f)
    {
        return 1.0f;
    }

    if (value < -1.0f)
    {
        return -1.0f;
    }

    return value;
}

float applyDeadband(
    float command,
    float deadband
)
{
    const float magnitude = fabsf(command);

    if (magnitude <= deadband)
    {
        return 0.0f;
    }

    const float scaled =
        (magnitude - deadband) /
        (1.0f - deadband);

    return command < 0.0f
        ? -scaled
        : scaled;
}

uint16_t interpolatePulse(
    float magnitude,
    uint16_t start_us,
    uint16_t end_us
)
{
    const float pulse =
        static_cast<float>(start_us) +
        magnitude *
        static_cast<float>(
            static_cast<int32_t>(end_us) -
            static_cast<int32_t>(start_us)
        );

    return static_cast<uint16_t>(
        lroundf(pulse)
    );
}

} // namespace

namespace TyrantActuation
{

bool validPwmChannelConfig(
    const PwmChannelConfig &config
)
{
    return
        config.reverse_us < config.neutral_us &&
        config.neutral_us < config.forward_us &&
        isfinite(config.deadband) &&
        config.deadband >= 0.0f &&
        config.deadband < 1.0f;
}

uint16_t mapNormalizedCommandToPulse(
    float command,
    const PwmChannelConfig &config
)
{
    if (
        !isfinite(command) ||
        !validPwmChannelConfig(config)
    )
    {
        return config.neutral_us;
    }

    float normalized = clampUnit(command);

    if (config.inverted)
    {
        normalized = -normalized;
    }

    normalized = applyDeadband(
        normalized,
        config.deadband
    );

    if (normalized > 0.0f)
    {
        return interpolatePulse(
            normalized,
            config.neutral_us,
            config.forward_us
        );
    }

    if (normalized < 0.0f)
    {
        return interpolatePulse(
            -normalized,
            config.neutral_us,
            config.reverse_us
        );
    }

    return config.neutral_us;
}

PwmOutputFrame mapThrusterCommandToPwm(
    const TyrantControl::ThrusterCommand &command,
    const PwmChannelConfig (&config)[TyrantControl::THRUSTER_COUNT]
)
{
    PwmOutputFrame frame {};
    frame.valid = command.valid;

    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        if (!validPwmChannelConfig(config[index]))
        {
            frame.valid = false;
        }

        const float requested =
            command.enabled && command.valid
                ? command.value[index]
                : 0.0f;

        if (!isfinite(requested))
        {
            frame.valid = false;
        }

        frame.pulse_us[index] =
            mapNormalizedCommandToPulse(
                requested,
                config[index]
            );
    }

    return frame;
}

} // namespace TyrantActuation
