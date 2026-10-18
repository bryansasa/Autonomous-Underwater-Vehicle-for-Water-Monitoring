#pragma once

#include <stdint.h>

#include "control/thruster_allocator.h"

namespace TyrantActuation
{

struct MockThrusterState
{
    TyrantControl::ThrusterCommand command;
    uint32_t apply_count;
};

void initMockThrusterBackend();

void applyMockThrusterCommand(
    const TyrantControl::ThrusterCommand &command
);

void neutralizeMockThrusters(
    uint32_t source_sequence,
    TyrantControl::ThrusterAllocationStatus status,
    bool valid
);

MockThrusterState getMockThrusterState();

} // namespace TyrantActuation
