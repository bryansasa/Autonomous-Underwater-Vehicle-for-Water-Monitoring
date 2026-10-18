#pragma once

#include <stdint.h>

#include "control/control_types.h"
#include "control/thruster_allocation.h"

namespace TyrantControl
{

struct ThrusterAllocatorConfig
{
    // Damped least-squares regularization. Must be finite and > 0.
    float damping;

    // Uniform absolute command limit for every normalized thruster output.
    // Development value is 1.0. Real thrust limits are added after
    // characterization.
    float max_abs_command;
};

enum class ThrusterAllocationStatus : uint8_t
{
    OK = 0,
    REQUEST_DISABLED,
    INVALID_TAM,
    INVALID_REQUEST,
    INVALID_CONFIG,
    SOLVER_FAILED
};

struct ThrusterCommand
{
    uint32_t source_sequence;

    float value[THRUSTER_COUNT];

    bool valid;
    bool enabled;
    bool saturated;

    ThrusterAllocationStatus status;
    float residual_norm;
};

ThrusterCommand makeNeutralThrusterCommand(
    uint32_t source_sequence,
    ThrusterAllocationStatus status,
    bool valid
);

ThrusterCommand allocateNormalizedWrench(
    const ThrusterAllocationMatrix &tam,
    const WrenchRequest &request,
    const ThrusterAllocatorConfig &config
);

} // namespace TyrantControl
