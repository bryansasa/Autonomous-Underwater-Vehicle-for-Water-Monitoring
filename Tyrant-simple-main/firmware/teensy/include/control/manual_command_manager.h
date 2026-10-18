#pragma once

#include <Arduino.h>

#include "control/control_types.h"

namespace TyrantControl
{
    void initManualCommandManager();

    bool acceptManualCommand(
        const ManualCommand &command
    );

    bool getFreshManualCommand(
        ManualCommand &command
    );

    bool manualCommandFresh();

    uint32_t manualCommandAgeMs();

    void clearManualCommand();
}
