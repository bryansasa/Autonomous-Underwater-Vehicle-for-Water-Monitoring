#include "actuation/pwm_thruster_backend.h"

#ifdef TYRANT_ENABLE_PHYSICAL_THRUSTER_OUTPUT
#include <Servo.h>
#endif

namespace
{
#ifdef TYRANT_ENABLE_PHYSICAL_THRUSTER_OUTPUT
Servo esc[TyrantControl::THRUSTER_COUNT];
bool attached[TyrantControl::THRUSTER_COUNT] {};
#endif
}

namespace TyrantActuation
{

bool validatePwmBackendConfig(
    const PwmBackendConfig &config
)
{
    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        if (config.pin[index] == 0xFFu)
        {
            return false;
        }

        if (!validPwmChannelConfig(config.channel[index]))
        {
            return false;
        }
    }

    return true;
}

bool initPwmThrusterBackend(
    const PwmBackendConfig &config
)
{
#ifndef TYRANT_ENABLE_PHYSICAL_THRUSTER_OUTPUT
    (void)config;
    return false;
#else
    if (!validatePwmBackendConfig(config))
    {
        return false;
    }

    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        if (
            esc[index].attach(
                config.pin[index],
                config.channel[index].reverse_us,
                config.channel[index].forward_us
            ) == 0
        )
        {
            shutdownPwmThrusterBackend();
            return false;
        }

        attached[index] = true;
        esc[index].writeMicroseconds(
            config.channel[index].neutral_us
        );
    }

    return true;
#endif
}

bool writePwmThrusterBackend(
    const PwmOutputFrame &frame
)
{
#ifndef TYRANT_ENABLE_PHYSICAL_THRUSTER_OUTPUT
    (void)frame;
    return false;
#else
    if (!frame.valid)
    {
        return false;
    }

    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        if (!attached[index])
        {
            return false;
        }

        esc[index].writeMicroseconds(
            frame.pulse_us[index]
        );
    }

    return true;
#endif
}

void neutralizePwmThrusterBackend(
    const PwmBackendConfig &config
)
{
#ifdef TYRANT_ENABLE_PHYSICAL_THRUSTER_OUTPUT
    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        if (attached[index])
        {
            esc[index].writeMicroseconds(
                config.channel[index].neutral_us
            );
        }
    }
#else
    (void)config;
#endif
}

void shutdownPwmThrusterBackend()
{
#ifdef TYRANT_ENABLE_PHYSICAL_THRUSTER_OUTPUT
    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        if (attached[index])
        {
            esc[index].detach();
            attached[index] = false;
        }
    }
#endif
}

} // namespace TyrantActuation
