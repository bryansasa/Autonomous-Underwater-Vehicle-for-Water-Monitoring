#include "actuation/mock_thruster_backend.h"

#include <math.h>

namespace
{
TyrantActuation::MockThrusterState state {};

bool finiteCommand(
    const TyrantControl::ThrusterCommand &command
)
{
    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        if (!isfinite(command.value[index]))
        {
            return false;
        }
    }

    return isfinite(command.residual_norm);
}

} // namespace

namespace TyrantActuation
{

void initMockThrusterBackend()
{
    state = MockThrusterState {};
    state.command = TyrantControl::makeNeutralThrusterCommand(
        0,
        TyrantControl::ThrusterAllocationStatus::REQUEST_DISABLED,
        false
    );
}

void applyMockThrusterCommand(
    const TyrantControl::ThrusterCommand &command
)
{
    ++state.apply_count;

    if (!command.valid || !finiteCommand(command))
    {
        state.command = TyrantControl::makeNeutralThrusterCommand(
            command.source_sequence,
            command.status,
            false
        );
        return;
    }

    state.command = command;

    if (!command.enabled)
    {
        for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
        {
            state.command.value[index] = 0.0f;
        }
    }
}

void neutralizeMockThrusters(
    uint32_t source_sequence,
    TyrantControl::ThrusterAllocationStatus status,
    bool valid
)
{
    applyMockThrusterCommand(
        TyrantControl::makeNeutralThrusterCommand(
            source_sequence,
            status,
            valid
        )
    );
}

MockThrusterState getMockThrusterState()
{
    return state;
}

} // namespace TyrantActuation
