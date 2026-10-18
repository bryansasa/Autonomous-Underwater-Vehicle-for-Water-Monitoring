#include "actuation/thruster_backend.h"

#include <math.h>

#include "actuation/mock_thruster_backend.h"

namespace
{
TyrantActuation::ThrusterBackendConfig backend_config {};
TyrantActuation::ThrusterBackendStatus backend_status {};

bool finiteThrusterCommand(
    const TyrantControl::ThrusterCommand &command
)
{
    if (!isfinite(command.residual_norm))
    {
        return false;
    }

    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        if (!isfinite(command.value[index]))
        {
            return false;
        }
    }

    return true;
}

void setNeutralPulseFrame()
{
    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        backend_status.pulse_us[index] =
            backend_config.pwm.channel[index].neutral_us;
    }
}

void latchFault(
    TyrantActuation::ThrusterBackendFault fault
)
{
    backend_status.fault = fault;
    backend_status.fault_latched = true;
    backend_status.ready = false;
}

void applyNeutralCommand(
    uint32_t source_sequence,
    TyrantControl::ThrusterAllocationStatus allocation_status,
    bool valid,
    uint32_t now_us
)
{
    const auto neutral =
        TyrantControl::makeNeutralThrusterCommand(
            source_sequence,
            allocation_status,
            valid
        );

    backend_status.applied_command = neutral;
    backend_status.last_command_us = now_us;
    backend_status.command_age_us = 0;
    ++backend_status.neutralize_count;

    if (backend_status.type == TyrantActuation::ThrusterBackendType::MOCK)
    {
        TyrantActuation::neutralizeMockThrusters(
            source_sequence,
            allocation_status,
            valid
        );

        backend_status.applied_command =
            TyrantActuation::getMockThrusterState().command;
    }
    else if (backend_status.type == TyrantActuation::ThrusterBackendType::PWM)
    {
        TyrantActuation::neutralizePwmThrusterBackend(
            backend_config.pwm
        );
        setNeutralPulseFrame();
    }
}

} // namespace

namespace TyrantActuation
{

void initThrusterBackend(
    const ThrusterBackendConfig &config,
    uint32_t now_us
)
{
    backend_config = config;
    backend_status = ThrusterBackendStatus {};
    backend_status.last_command_us = now_us;

    backend_status.applied_command =
        TyrantControl::makeNeutralThrusterCommand(
            0,
            TyrantControl::ThrusterAllocationStatus::REQUEST_DISABLED,
            false
        );

    setNeutralPulseFrame();

#if defined(TYRANT_USE_MOCK_THRUSTER_BACKEND)
    backend_status.type = ThrusterBackendType::MOCK;
    backend_status.configured = true;
    backend_status.ready = true;
    backend_status.physical_output_enabled = false;
    backend_status.fault = ThrusterBackendFault::NONE;
    initMockThrusterBackend();
#elif defined(TYRANT_ENABLE_PHYSICAL_THRUSTER_OUTPUT)
    backend_status.type = ThrusterBackendType::PWM;
    backend_status.physical_output_enabled = true;
    backend_status.configured = validatePwmBackendConfig(config.pwm);

    if (
        backend_status.configured &&
        initPwmThrusterBackend(config.pwm)
    )
    {
        backend_status.ready = true;
        backend_status.fault = ThrusterBackendFault::NONE;
    }
    else
    {
        backend_status.ready = false;
        latchFault(ThrusterBackendFault::PWM_INIT_FAILED);
    }
#else
    backend_status.type = ThrusterBackendType::DISABLED;
    backend_status.configured = false;
    backend_status.ready = false;
    backend_status.physical_output_enabled = false;
    backend_status.fault = ThrusterBackendFault::NOT_CONFIGURED;
#endif
}

void updateThrusterBackend(uint32_t now_us)
{
    backend_status.command_age_us =
        static_cast<uint32_t>(
            now_us - backend_status.last_command_us
        );

    if (
        !backend_status.ready ||
        backend_config.command_timeout_us == 0 ||
        !backend_status.applied_command.enabled
    )
    {
        return;
    }

    if (
        backend_status.command_age_us >
        backend_config.command_timeout_us
    )
    {
        applyNeutralCommand(
            backend_status.applied_command.source_sequence,
            TyrantControl::ThrusterAllocationStatus::REQUEST_DISABLED,
            false,
            now_us
        );

        latchFault(
            ThrusterBackendFault::COMMAND_TIMEOUT
        );
    }
}

void applyThrusterBackendCommand(
    const TyrantControl::ThrusterCommand &command,
    uint32_t now_us
)
{
    ++backend_status.apply_count;

    if (!backend_status.ready)
    {
        ++backend_status.reject_count;
        applyNeutralCommand(
            command.source_sequence,
            command.status,
            false,
            now_us
        );
        return;
    }

    if (
        !command.valid ||
        !finiteThrusterCommand(command)
    )
    {
        ++backend_status.reject_count;
        applyNeutralCommand(
            command.source_sequence,
            command.status,
            false,
            now_us
        );
        latchFault(
            ThrusterBackendFault::INVALID_COMMAND
        );
        return;
    }

    backend_status.last_command_us = now_us;
    backend_status.command_age_us = 0;

    if (backend_status.type == ThrusterBackendType::MOCK)
    {
        applyMockThrusterCommand(command);
        backend_status.applied_command =
            getMockThrusterState().command;
        return;
    }

    if (backend_status.type == ThrusterBackendType::PWM)
    {
        const auto frame =
            mapThrusterCommandToPwm(
                command,
                backend_config.pwm.channel
            );

        if (
            !frame.valid ||
            !writePwmThrusterBackend(frame)
        )
        {
            ++backend_status.reject_count;
            applyNeutralCommand(
                command.source_sequence,
                command.status,
                false,
                now_us
            );
            latchFault(
                ThrusterBackendFault::PWM_WRITE_FAILED
            );
            return;
        }

        backend_status.applied_command = command;

        for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
        {
            backend_status.pulse_us[index] =
                frame.pulse_us[index];
        }
    }
}

void forceNeutralThrusterBackend(
    uint32_t source_sequence,
    TyrantControl::ThrusterAllocationStatus status,
    bool valid,
    uint32_t now_us
)
{
    applyNeutralCommand(
        source_sequence,
        status,
        valid,
        now_us
    );
}

ThrusterBackendStatus getThrusterBackendStatus(
    uint32_t now_us
)
{
    ThrusterBackendStatus snapshot = backend_status;
    snapshot.command_age_us =
        static_cast<uint32_t>(
            now_us - backend_status.last_command_us
        );

    if (snapshot.type == ThrusterBackendType::MOCK)
    {
        snapshot.applied_command =
            getMockThrusterState().command;
    }

    return snapshot;
}

bool thrusterBackendReady()
{
    return backend_status.ready &&
           !backend_status.fault_latched;
}

} // namespace TyrantActuation
