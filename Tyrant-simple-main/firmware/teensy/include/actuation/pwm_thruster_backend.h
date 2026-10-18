#pragma once

#include <stdint.h>

#include "actuation/thruster_output_mapper.h"

namespace TyrantActuation
{

struct PwmBackendConfig
{
    uint8_t pin[TyrantControl::THRUSTER_COUNT];
    PwmChannelConfig channel[TyrantControl::THRUSTER_COUNT];
};

bool validatePwmBackendConfig(
    const PwmBackendConfig &config
);

bool initPwmThrusterBackend(
    const PwmBackendConfig &config
);

bool writePwmThrusterBackend(
    const PwmOutputFrame &frame
);

void neutralizePwmThrusterBackend(
    const PwmBackendConfig &config
);

void shutdownPwmThrusterBackend();

} // namespace TyrantActuation
