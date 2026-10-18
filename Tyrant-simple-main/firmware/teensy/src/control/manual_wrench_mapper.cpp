#include "control/manual_wrench_mapper.h"

namespace TyrantControl
{
    WrenchRequest makeZeroWrenchRequest(
        uint32_t source_sequence,
        bool command_fresh
    )
    {
        WrenchRequest request {};
        request.source_sequence = source_sequence;
        request.command_fresh = command_fresh;
        request.enabled = false;
        return request;
    }


    WrenchRequest makeManualWrenchRequest(
        const ManualCommand &command,
        bool command_fresh,
        bool propulsion_allowed
    )
    {
        if (
            !command_fresh ||
            !propulsion_allowed
        )
        {
            return makeZeroWrenchRequest(
                command.sequence,
                command_fresh
            );
        }

        WrenchRequest request {};

        request.source_sequence = command.sequence;

        request.x = command.surge;
        request.y = command.sway;
        request.z = command.heave;

        request.k = command.roll;
        request.m = command.pitch;
        request.n = command.yaw;

        request.command_fresh = true;
        request.enabled = true;

        return request;
    }
}
