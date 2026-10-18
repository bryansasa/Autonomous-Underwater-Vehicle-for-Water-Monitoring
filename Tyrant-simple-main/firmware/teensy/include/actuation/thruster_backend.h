#pragma once

#include <stdint.h>

#include "actuation/pwm_thruster_backend.h"
#include "control/thruster_allocator.h"

namespace TyrantActuation
{

enum class ThrusterBackendType : uint8_t
{
    DISABLED = 0,
    MOCK = 1,
    PWM = 2
};

enum class ThrusterBackendFault : uint8_t
{
    NONE = 0,
    NOT_CONFIGURED,
    INVALID_COMMAND,
    COMMAND_TIMEOUT,
    PWM_INIT_FAILED,
    PWM_WRITE_FAILED
};

struct ThrusterBackendConfig
{
    uint32_t command_timeout_us;
    PwmBackendConfig pwm;
};

struct ThrusterBackendStatus
{
    ThrusterBackendType type;
    ThrusterBackendFault fault;

    bool configured;
    bool ready;
    bool physical_output_enabled;
    bool fault_latched;

    uint32_t apply_count;
    uint32_t reject_count;
    uint32_t neutralize_count;
    uint32_t last_command_us;
    uint32_t command_age_us;

    uint16_t pulse_us[TyrantControl::THRUSTER_COUNT];
    TyrantControl::ThrusterCommand applied_command;
};

void initThrusterBackend(
    const ThrusterBackendConfig &config,
    uint32_t now_us
);

void updateThrusterBackend(uint32_t now_us);

void applyThrusterBackendCommand(
    const TyrantControl::ThrusterCommand &command,
    uint32_t now_us
);

void forceNeutralThrusterBackend(
    uint32_t source_sequence,
    TyrantControl::ThrusterAllocationStatus status,
    bool valid,
    uint32_t now_us
);

ThrusterBackendStatus getThrusterBackendStatus(
    uint32_t now_us
);

bool thrusterBackendReady();

} // namespace TyrantActuation
