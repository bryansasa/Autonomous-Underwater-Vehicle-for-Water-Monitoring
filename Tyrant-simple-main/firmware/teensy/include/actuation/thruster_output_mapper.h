#pragma once

#include <stdint.h>

#include "control/thruster_allocator.h"

namespace TyrantActuation
{

struct PwmChannelConfig
{
    uint16_t reverse_us;
    uint16_t neutral_us;
    uint16_t forward_us;
    float deadband;
    bool inverted;
};

struct PwmOutputFrame
{
    uint16_t pulse_us[TyrantControl::THRUSTER_COUNT];
    bool valid;
};

bool validPwmChannelConfig(
    const PwmChannelConfig &config
);

uint16_t mapNormalizedCommandToPulse(
    float command,
    const PwmChannelConfig &config
);

PwmOutputFrame mapThrusterCommandToPwm(
    const TyrantControl::ThrusterCommand &command,
    const PwmChannelConfig (&config)[TyrantControl::THRUSTER_COUNT]
);

} // namespace TyrantActuation
