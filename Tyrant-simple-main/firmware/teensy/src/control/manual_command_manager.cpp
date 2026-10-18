#include "control/manual_command_manager.h"

#include <math.h>

#include "config/control_config.h"

namespace
{
    TyrantControl::ManualCommand latest_command {};

    bool command_received = false;
    unsigned long last_command_ms = 0;


    bool finiteAxis(float value)
    {
        return isfinite(value);
    }


    float clampNormalized(float value)
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


    bool validCommand(
        const TyrantControl::ManualCommand &command
    )
    {
        return
            finiteAxis(command.surge) &&
            finiteAxis(command.sway) &&
            finiteAxis(command.heave) &&
            finiteAxis(command.roll) &&
            finiteAxis(command.pitch) &&
            finiteAxis(command.yaw);
    }
}


namespace TyrantControl
{
    void initManualCommandManager()
    {
        clearManualCommand();
    }


    bool acceptManualCommand(
        const ManualCommand &command
    )
    {
        if (!validCommand(command))
        {
            clearManualCommand();
            return false;
        }

        latest_command = command;

        latest_command.surge =
            clampNormalized(command.surge);
        latest_command.sway =
            clampNormalized(command.sway);
        latest_command.heave =
            clampNormalized(command.heave);
        latest_command.roll =
            clampNormalized(command.roll);
        latest_command.pitch =
            clampNormalized(command.pitch);
        latest_command.yaw =
            clampNormalized(command.yaw);

        command_received = true;
        last_command_ms = millis();

        return true;
    }


    bool manualCommandFresh()
    {
        if (!command_received)
        {
            return false;
        }

        return (
            millis() - last_command_ms <=
            TyrantControlConfig::MANUAL_COMMAND_TIMEOUT_MS
        );
    }


    bool getFreshManualCommand(
        ManualCommand &command
    )
    {
        if (!manualCommandFresh())
        {
            return false;
        }

        command = latest_command;
        return true;
    }


    uint32_t manualCommandAgeMs()
    {
        if (!command_received)
        {
            return 0xFFFFFFFFu;
        }

        return static_cast<uint32_t>(
            millis() - last_command_ms
        );
    }


    void clearManualCommand()
    {
        latest_command = ManualCommand {};
        command_received = false;
        last_command_ms = 0;
    }
}
