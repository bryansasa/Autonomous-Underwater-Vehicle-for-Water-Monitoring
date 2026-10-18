#pragma once

#include "actuation/thruster_backend.h"
#include "control/thruster_allocation.h"
#include "control/thruster_allocator.h"

namespace TyrantThrusterConfig
{


inline TyrantActuation::ThrusterBackendConfig
makeDevelopmentBackendConfig()
{
    TyrantActuation::ThrusterBackendConfig config {};

    // Backend watchdog remains active even before hardware exists.
    // If an enabled command is not refreshed within this window,
    // the backend neutralizes and latches a fault.
    config.command_timeout_us = 100000u;

    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        // 0xFF intentionally means "unconfigured pin". Production
        // firmware therefore cannot enable physical PWM accidentally.
        config.pwm.pin[index] = 0xFFu;

        // Development mapping only. These pulse widths are placeholders
        // until ESC/thruster characterization is completed.
        config.pwm.channel[index].reverse_us = 1100u;
        config.pwm.channel[index].neutral_us = 1500u;
        config.pwm.channel[index].forward_us = 1900u;
        config.pwm.channel[index].deadband = 0.05f;
        config.pwm.channel[index].inverted = false;
    }

    return config;
}

inline TyrantControl::ThrusterAllocatorConfig
makeDevelopmentAllocatorConfig()
{
    TyrantControl::ThrusterAllocatorConfig config {};

    // Development-only normalized allocator settings.
    // Physical thrust bounds replace these after characterization.
    config.damping = 0.05f;
    config.max_abs_command = 1.0f;

    return config;
}

inline bool loadProductionGeometry(
    TyrantControl::ThrusterGeometry (&geometry)[TyrantControl::THRUSTER_COUNT]
)
{
    // ============================================================
    // PRODUCTION THRUSTER GEOMETRY
    // ============================================================
    // Intentionally unavailable until the final Tyrant CAD/assembly
    // provides verified r_i and d_i for all eight channels.
    //
    // Do not substitute a generic ROV geometry here. Fill this only
    // from docs/thruster_geometry_template.csv after verification.

    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        geometry[index] = {
            {0.0f, 0.0f, 0.0f},
            {0.0f, 0.0f, 0.0f},
            false
        };
    }

    return false;
}

inline bool loadSyntheticDevelopmentGeometry(
    TyrantControl::ThrusterGeometry (&geometry)[TyrantControl::THRUSTER_COUNT]
)
{
    // ============================================================
    // SYNTHETIC MOCK GEOMETRY -- NEVER PRODUCTION HARDWARE
    // ============================================================
    // This deliberately simple full-rank geometry exists only to
    // exercise Wrench -> TAM -> Allocator -> MockBackend end-to-end
    // before the physical chassis is assembled.

    geometry[0] = {{0.0f,  1.0f, 0.0f}, {1.0f, 0.0f, 0.0f}, true};
    geometry[1] = {{0.0f, -1.0f, 0.0f}, {1.0f, 0.0f, 0.0f}, true};

    geometry[2] = {{ 1.0f, 0.0f, 0.0f}, {0.0f, 1.0f, 0.0f}, true};
    geometry[3] = {{-1.0f, 0.0f, 0.0f}, {0.0f, 1.0f, 0.0f}, true};

    geometry[4] = {{0.0f,  1.0f, 0.0f}, {0.0f, 0.0f, 1.0f}, true};
    geometry[5] = {{0.0f, -1.0f, 0.0f}, {0.0f, 0.0f, 1.0f}, true};

    geometry[6] = {{ 1.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 1.0f}, true};
    geometry[7] = {{-1.0f, 0.0f, 0.0f}, {0.0f, 0.0f, 1.0f}, true};

    return true;
}

inline bool loadConfiguredGeometry(
    TyrantControl::ThrusterGeometry (&geometry)[TyrantControl::THRUSTER_COUNT]
)
{
#ifdef TYRANT_USE_SYNTHETIC_THRUSTER_GEOMETRY
    return loadSyntheticDevelopmentGeometry(geometry);
#else
    return loadProductionGeometry(geometry);
#endif
}

} // namespace TyrantThrusterConfig
