#pragma once

#include "control/control_types.h"

namespace TyrantControl
{
    WrenchRequest makeManualWrenchRequest(
        const ManualCommand &command,
        bool command_fresh,
        bool propulsion_allowed
    );

    WrenchRequest makeZeroWrenchRequest(
        uint32_t source_sequence = 0,
        bool command_fresh = false
    );
}
