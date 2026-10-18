#pragma once

#include "application/emergency_recovery_manager.h"

namespace TyrantMissionConfig
{
inline TyrantEmergency::Config makeDevelopmentEmergencyConfig()
{
    TyrantEmergency::Config config {};
    config.surface_target_depth_m = 0.15f;
    config.surface_tolerance_m = 0.05f;
    config.ascent_command = 0.60f;
    config.max_runtime_ms = 120000;
    return config;
}
}
