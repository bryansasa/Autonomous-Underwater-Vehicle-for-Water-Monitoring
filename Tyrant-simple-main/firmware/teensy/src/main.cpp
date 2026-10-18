#include <Arduino.h>

#include "application/depth_reference_manager.h"
#include "application/emergency_recovery_manager.h"
#include "application/mission_manager.h"
#include "actuation/thruster_backend.h"
#include "communication/connection_manager.h"
#include "communication/ros_interface.h"
#include "control/manual_command_manager.h"
#include "control/stabilized_manual_controller.h"
#include "control/thruster_allocation.h"
#include "control/thruster_allocator.h"
#include "config/control_config.h"
#include "config/mission_config.h"
#include "config/thruster_config.h"
#include "config/simple_estimator_config.h"
#include "estimation/simple_state_estimator.h"
#include "safety/safety_manager.h"
#include "scheduler/scheduler.h"
#include "sensors/sensor_hardware.h"
#include "sensors/sensor_manager.h"
#include "sysid/sysid_recorder.h"
#ifdef TYRANT_USE_SIM_STATE_INPUT
#include "simulation/sim_state_source.h"
#endif

namespace
{
constexpr uint8_t MODE_IDLE = 1;
constexpr uint8_t MODE_MANUAL = 2;
constexpr uint8_t MODE_AUTO = 3;
constexpr uint8_t MODE_SAFE = 4;
constexpr uint8_t MODE_EMERGENCY = 6;

constexpr uint8_t MISSION_CLEAR = 0;
constexpr uint8_t MISSION_APPEND = 1;
constexpr uint8_t MISSION_START = 2;
constexpr uint8_t MISSION_STOP = 3;
constexpr uint8_t STATUS_SNAPSHOT = 255;

constexpr uint8_t EMERGENCY_ZERO_THRUST = 1;
constexpr uint8_t EMERGENCY_CONTROLLED_SURFACE = 2;

constexpr uint8_t SYSID_STOP = 0;
constexpr uint8_t SYSID_START = 1;

uint32_t last_request_id = 0;
uint8_t last_requested_mode = MODE_IDLE;
bool last_request_accepted = false;
uint8_t last_reason = 0;

uint32_t last_control_update_us = 0;

TyrantControl::ThrusterAllocationMatrix production_tam {};
TyrantControl::ThrusterAllocatorConfig allocator_config {};
bool allocator_ready = false;


// ============================================================
// THRUSTER ALLOCATION INITIALIZATION
// ============================================================

void initThrusterAllocation()
{
    allocator_config =
        TyrantThrusterConfig::makeDevelopmentAllocatorConfig();

    TyrantActuation::initThrusterBackend(
        TyrantThrusterConfig::makeDevelopmentBackendConfig(),
        micros()
    );

    TyrantControl::ThrusterGeometry geometry[TyrantControl::THRUSTER_COUNT] {};

    if (!TyrantThrusterConfig::loadConfiguredGeometry(geometry))
    {
        allocator_ready = false;
        return;
    }

    const auto result =
        TyrantControl::buildThrusterAllocationMatrix(
            geometry,
            production_tam
        );

    allocator_ready =
        result.status == TyrantControl::TamBuildStatus::OK &&
        production_tam.valid;
}


// ============================================================
// CONTROL STATE SOURCE
//
// Production uses the real reduced estimator. HIL builds consume a
// ROS-injected SimpleState from the software plant simulator.
// ============================================================

bool getControlState(
    TyrantSimpleEstimator::State &state,
    uint32_t now_us)
{
#ifdef TYRANT_USE_SIM_STATE_INPUT
    return TyrantSimulation::getSimState(state, now_us);
#else
    return TyrantSimpleEstimator::getState(state, now_us);
#endif
}


// ============================================================
// AUTONOMY READINESS
// ============================================================

void updateAutonomyReadiness()
{
    TyrantSimpleEstimator::State state {};
    const bool estimator_ready =
        getControlState(state, micros());

    const bool reduced_state_ready =
        estimator_ready &&
        state.attitude_valid &&
        state.heading_valid &&
        state.depth_valid;

    TyrantSafety::setAutonomyReady(
        allocator_ready &&
        TyrantActuation::thrusterBackendReady() &&
        reduced_state_ready &&
        TyrantMission::readyForAuto()
    );
}


// ============================================================
// MODE STATUS
// ============================================================

void publishModeStatus()
{
    TyrantROS::publishModeStatus(
        last_request_id,
        TyrantSafety::getMode(),
        last_requested_mode,
        last_request_accepted,
        last_reason,
        TyrantSafety::communicationHealthy(),
        TyrantSafety::propulsionAllowed());
}


// ============================================================
// REDUCED STATE UPDATE
// ============================================================

void updateEstimator()
{
    TyrantSensors::ImuSample imu_sample {};
    if (TyrantSensors::takeImuSample(imu_sample))
    {
        (void)TyrantSimpleEstimator::processImuSample(imu_sample);
    }

    TyrantSensors::DepthMeasurement depth {};
    if (TyrantSensors::takeDepthMeasurement(depth))
    {
        TyrantSimpleEstimator::processDepthMeasurement(depth);
    }
}


// ============================================================
// APPLICATION COMMUNICATION
// ============================================================

void handleApplicationCommunication()
{
    if (!TyrantConnection::connected())
    {
        return;
    }

#ifdef TYRANT_USE_SIM_STATE_INPUT
    TyrantSimpleEstimator::State simulated_state {};
    if (TyrantROS::takeSimStateInput(simulated_state))
    {
        (void)TyrantSimulation::acceptSimState(
            simulated_state,
            micros()
        );
    }
#endif

#ifdef TYRANT_ENABLE_DIAGNOSTICS
    if (TyrantROS::hasNewCommand())
    {
        TyrantROS::publishResponse(TyrantROS::getLastCommand());
    }
#endif

    if (TyrantROS::takeHostHeartbeat())
    {
        TyrantSafety::notifyHostHeartbeat();
    }

    TyrantROS::ModeRequestData mode_request {};
    if (TyrantROS::takeModeRequest(mode_request))
    {
        last_request_id = mode_request.request_id;
        last_requested_mode = mode_request.requested_mode;

        const uint8_t previous_mode =
            TyrantSafety::getMode();

        const auto result =
            TyrantSafety::requestMode(mode_request.requested_mode);

        last_request_accepted = result.accepted;
        last_reason = result.reason;

        if (
            result.accepted &&
            TyrantSafety::getMode() != previous_mode
        )
        {
            // A real mode transition must never reuse a command that
            // was received under the previous operating state.
            TyrantControl::clearManualCommand();
            TyrantControl::resetStabilizedManualController();

            if (
                previous_mode == MODE_AUTO &&
                TyrantSafety::getMode() != MODE_AUTO
            )
            {
                TyrantMission::stop();
            }
        }

        publishModeStatus();
    }

    TyrantROS::ManualCommandData manual_command_data {};
    if (TyrantROS::takeManualCommand(manual_command_data))
    {
        if (TyrantSafety::getMode() == MODE_MANUAL)
        {
            TyrantControl::ManualCommand command {};
            command.sequence = manual_command_data.sequence;
            command.surge = manual_command_data.surge;
            command.sway = manual_command_data.sway;
            command.heave = manual_command_data.heave;
            command.roll = manual_command_data.roll;
            command.pitch = manual_command_data.pitch;
            command.yaw = manual_command_data.yaw;

            (void)TyrantControl::acceptManualCommand(command);
        }
        else
        {
            TyrantControl::clearManualCommand();
            TyrantControl::resetStabilizedManualController();
        }
    }

    TyrantROS::MissionCommandData mission_command {};
    if (TyrantROS::takeMissionCommand(mission_command))
    {
        bool accepted = false;

        const uint8_t current_mode = TyrantSafety::getMode();
        const bool mission_configuration_allowed =
            current_mode == MODE_IDLE || current_mode == MODE_SAFE;

        if (mission_command.command == MISSION_CLEAR)
        {
            if (mission_configuration_allowed)
            {
                TyrantMission::clear();
                accepted = true;
            }
        }
        else if (mission_command.command == MISSION_APPEND)
        {
            if (mission_configuration_allowed)
            {
                TyrantMission::Step step {};
                step.type = static_cast<TyrantMission::StepType>(
                    mission_command.step_type
                );
                step.target = mission_command.target;
                step.effort = mission_command.effort;
                step.duration_ms = mission_command.duration_ms;
                step.tolerance = mission_command.tolerance;
                accepted = TyrantMission::appendStep(step);
            }
        }
        else if (mission_command.command == MISSION_START)
        {
            if (TyrantSafety::getMode() == MODE_AUTO)
            {
                TyrantControl::resetStabilizedManualController();
                accepted = TyrantMission::start(millis());
            }
        }
        else if (mission_command.command == MISSION_STOP)
        {
            TyrantMission::stop();
            TyrantControl::resetStabilizedManualController();

            if (TyrantSafety::getMode() == MODE_AUTO)
            {
                TyrantSafety::forceSafe();
            }

            accepted = true;
        }

        updateAutonomyReadiness();

        TyrantROS::publishMissionStatus(
            mission_command.request_id,
            mission_command.command,
            accepted,
            TyrantMission::getStatus()
        );
    }

    TyrantROS::EmergencyControlData emergency_control {};
    if (TyrantROS::takeEmergencyControl(emergency_control))
    {
        TyrantEmergency::Policy policy = TyrantEmergency::Policy::NONE;

        if (emergency_control.command == EMERGENCY_ZERO_THRUST)
        {
            policy = TyrantEmergency::Policy::ZERO_THRUST;
        }
        else if (
            emergency_control.command == EMERGENCY_CONTROLLED_SURFACE
        )
        {
            policy = TyrantEmergency::Policy::CONTROLLED_SURFACE;
        }

        TyrantSimpleEstimator::State state {};
        (void)getControlState(state, micros());

        const bool accepted =
            policy != TyrantEmergency::Policy::NONE &&
            TyrantEmergency::trigger(policy, state, millis());

        if (policy != TyrantEmergency::Policy::NONE)
        {
            // An emergency request always latches EMERGENCY. If a
            // controlled surface cannot start because state is invalid,
            // the actuation path remains zero-thrust.
            TyrantMission::stop();
            TyrantControl::clearManualCommand();
            TyrantControl::resetStabilizedManualController();
            TyrantSafety::triggerEmergency();
        }

        TyrantROS::publishEmergencyStatus(
            emergency_control.request_id,
            emergency_control.command,
            accepted,
            TyrantEmergency::getStatus(millis())
        );

        publishModeStatus();
    }

    TyrantROS::SysIdControlData sysid_control {};
    if (TyrantROS::takeSysIdControl(sysid_control))
    {
        bool accepted = false;

        if (
            sysid_control.command == SYSID_START &&
            sysid_control.experiment_id != 0
        )
        {
            TyrantSysId::startSession(
                sysid_control.experiment_id,
                sysid_control.profile_id
            );
            accepted = true;
        }
        else if (sysid_control.command == SYSID_STOP)
        {
            TyrantSysId::stopSession();
            accepted = true;
        }

        TyrantROS::publishSysIdStatus(
            sysid_control.request_id,
            sysid_control.command,
            accepted,
            TyrantSysId::getStatus()
        );
    }

    TyrantROS::DepthReferenceRequestData depth_request {};
    if (TyrantROS::takeDepthReferenceRequest(depth_request))
    {
        const auto result =
            TyrantDepthReference::handleRequest(depth_request.command);

        TyrantROS::publishDepthReferenceStatus(
            depth_request.request_id,
            depth_request.command,
            result.accepted,
            static_cast<uint8_t>(result.reason),
            result.reference_valid,
            result.surface_pressure_pa);
    }
}


// ============================================================
// TELEMETRY
// ============================================================

void publishHeartbeatAndDiagnostics()
{
    if (!TyrantConnection::connected())
    {
        return;
    }

    TyrantROS::publishHeartbeat();

    const auto connection_stats = TyrantConnection::getStats();
    const auto error_stats = TyrantROS::getErrorStats();

    TyrantROS::publishCommunicationDiagnostics(
        static_cast<uint8_t>(TyrantConnection::getState()),
        connection_stats.connection_count,
        connection_stats.disconnect_count,
        connection_stats.reconnect_count,
        error_stats.publish_failures,
        error_stats.executor_failures,
        error_stats.entity_create_failures,
        error_stats.entity_destroy_failures);
}

void publishHealthTelemetry()
{
    if (!TyrantConnection::connected())
    {
        return;
    }

    TyrantSimpleEstimator::State state {};
    const bool estimator_ready =
        getControlState(state, micros());

    TyrantSensors::ImuSample imu_sample {};
    const bool imu_available =
        TyrantSensors::getImuSnapshot(imu_sample);

    const uint64_t state_timestamp_us =
        imu_available
            ? imu_sample.timestamp_us
            : static_cast<uint64_t>(micros());

    TyrantROS::publishSimpleState(state, state_timestamp_us);

    const auto imu_health = TyrantSensors::getImuHealth();
    const auto imu_stats = TyrantSensors::getImuStats();
    TyrantROS::publishImuTelemetry(
        imu_sample,
        imu_health,
        imu_stats.bytes_received,
        imu_stats.register_updates,
        imu_stats.samples_produced,
        imu_stats.samples_dropped,
        imu_available);

    TyrantSensors::PressureSample pressure_sample {};
    const bool pressure_available =
        TyrantSensors::getPressureSnapshot(pressure_sample);

    const auto pressure_health = TyrantSensors::getPressureHealth();
    const auto pressure_stats = TyrantSensors::getPressureStats();
    TyrantROS::publishPressureTelemetry(
        pressure_sample,
        pressure_health,
        pressure_stats.read_attempts,
        pressure_stats.read_successes,
        pressure_stats.samples_produced,
        pressure_available);

    const auto actuator_status =
        TyrantActuation::getThrusterBackendStatus(micros());

    TyrantROS::publishActuatorStatus(
        actuator_status,
        static_cast<uint64_t>(micros())
    );

    TyrantROS::publishSystemHealth(
        TyrantSafety::communicationHealthy(),
        estimator_ready,
        TyrantSafety::autonomyReady(),
        TyrantSafety::propulsionAllowed(),
        TyrantSafety::getMode(),
        TyrantSafety::hostHeartbeatAgeMs());

    TyrantROS::publishMissionStatus(
        0,
        STATUS_SNAPSHOT,
        true,
        TyrantMission::getStatus()
    );

    TyrantROS::publishEmergencyStatus(
        0,
        STATUS_SNAPSHOT,
        true,
        TyrantEmergency::getStatus(millis())
    );
}


// ============================================================
// SAFETY
// ============================================================

void runSafetyTask()
{
    TyrantSafety::update();

    if (!TyrantConnection::connected())
    {
        return;
    }

    uint8_t internal_reason = 0;
    if (TyrantSafety::takeInternalModeEvent(internal_reason))
    {
        last_request_id = 0;
        last_requested_mode = MODE_SAFE;
        last_request_accepted = false;
        last_reason = internal_reason;
    }

    publishModeStatus();
}


// ============================================================
// CONTROL SOURCE + STABILIZATION
//
// MANUAL: fresh host command
// AUTO: MissionManager virtual manual command
// EMERGENCY: EmergencyRecoveryManager virtual manual command
//
// All sources share the same stabilized controller, normalized wrench,
// TAM/allocator, and actuator boundary. Production geometry/PWM are not
// enabled yet.
// ============================================================

void runControlTask()
{
    const uint32_t now_us = micros();

    float dt_s = 0.020f;

    if (last_control_update_us != 0)
    {
        dt_s =
            static_cast<float>(
                static_cast<uint32_t>(
                    now_us - last_control_update_us
                )
            ) * 1.0e-6f;
    }

    last_control_update_us = now_us;


    TyrantControl::ManualCommand command {};
    bool command_fresh = false;
    bool control_enabled = false;

    TyrantSimpleEstimator::State state {};

    (void)getControlState(
        state,
        now_us
    );

    const uint8_t mode = TyrantSafety::getMode();

    if (mode == MODE_MANUAL)
    {
        command_fresh =
            TyrantControl::getFreshManualCommand(command);

        control_enabled =
            TyrantSafety::propulsionAllowed() &&
            TyrantConnection::connected();
    }
    else if (mode == MODE_AUTO)
    {
        command_fresh =
            TyrantMission::update(
                state,
                millis(),
                command
            );

        control_enabled =
            TyrantSafety::propulsionAllowed() &&
            TyrantConnection::connected();

        const auto mission_status = TyrantMission::getStatus();
        if (
            mission_status.state == TyrantMission::State::COMPLETE ||
            mission_status.state == TyrantMission::State::FAILED ||
            mission_status.state == TyrantMission::State::STOPPED
        )
        {
            TyrantSafety::forceSafe();
            control_enabled = false;
            command_fresh = false;
        }
    }
    else if (mode == MODE_EMERGENCY)
    {
        command_fresh =
            TyrantEmergency::update(
                state,
                millis(),
                command
            );

        control_enabled =
            TyrantSafety::emergencyActuationAllowed() &&
            command_fresh;
    }


    const auto request =
        TyrantControl::updateStabilizedManualController(
            command,
            state,
            command_fresh,
            control_enabled,
            dt_s
        );


    // ============================================================
    // THRUSTER ALLOCATION + ACTUATOR BOUNDARY
    // ============================================================

    TyrantControl::ThrusterCommand allocated_command =
        TyrantControl::makeNeutralThrusterCommand(
            request.source_sequence,
            TyrantControl::ThrusterAllocationStatus::INVALID_TAM,
            false
        );

    if (allocator_ready)
    {
        allocated_command =
            TyrantControl::allocateNormalizedWrench(
                production_tam,
                request,
                allocator_config
            );
    }

    TyrantActuation::applyThrusterBackendCommand(
        allocated_command,
        now_us
    );

    const auto actuator_status =
        TyrantActuation::getThrusterBackendStatus(now_us);

    const auto &applied_thruster_command =
        actuator_status.applied_command;


    if (!TyrantConnection::connected())
    {
        if (TyrantSysId::getStatus().active)
        {
            TyrantSysId::stopSession();
        }

        return;
    }

    TyrantROS::publishWrenchRequest(request);
    TyrantROS::publishThrusterCommand(
        applied_thruster_command,
        allocator_ready,
        actuator_status.type ==
            TyrantActuation::ThrusterBackendType::MOCK,
        static_cast<uint64_t>(now_us)
    );


    // ============================================================
    // SYSID SAMPLE
    // 20 Hz synchronized input/output sample. The actuator-side
    // command now comes from the selected actuator backend. Production
    // remains disabled until verified geometry, pins, and PWM output are
    // explicitly enabled.
    // ============================================================

    if (TyrantSysId::sampleDue(now_us))
    {
        TyrantSensors::ImuSample imu_sample {};
        const bool imu_valid =
            TyrantSensors::getImuSnapshot(imu_sample);

        TyrantSensors::PressureSample pressure_sample {};
        const bool pressure_valid =
            TyrantSensors::getPressureSnapshot(pressure_sample);

        TyrantSysId::Sample sysid_sample {};

        if (
            TyrantSysId::makeSample(
                static_cast<uint64_t>(now_us),
                TyrantSafety::getMode(),
                control_enabled,
                command,
                command_fresh,
                request,
                applied_thruster_command,
                state,
                imu_sample,
                imu_valid,
                pressure_sample,
                pressure_valid,
                sysid_sample
            )
        )
        {
            TyrantROS::publishSysIdSample(sysid_sample);
        }
    }
}


} // namespace

void setup()
{
    TyrantSafety::init();

#ifdef TYRANT_USE_SIM_STATE_INPUT
    // HIL profile: no physical sensor binding is required. A stale or
    // missing simulated state fails closed through the same validity gate.
    TyrantSimulation::initSimStateSource({200000u});
#else
    TyrantSensors::bindProductionSensors();
    TyrantSensors::init();

    TyrantSimpleEstimator::init(
        TyrantSimpleEstimatorConfig::makeDevelopmentConfig());
#endif

    TyrantControl::initManualCommandManager();

    TyrantControl::initStabilizedManualController(
        TyrantControlConfig::makeDevelopmentStabilizedManualConfig());

    TyrantSysId::init();

    TyrantMission::init();
    TyrantEmergency::init(
        TyrantMissionConfig::makeDevelopmentEmergencyConfig()
    );

    initThrusterAllocation();
    updateAutonomyReadiness();

    TyrantROS::setupTransport();
    TyrantConnection::init();
    TyrantScheduler::init();
}

void loop()
{
#ifndef TYRANT_USE_SIM_STATE_INPUT
    TyrantSensors::update();
    updateEstimator();
#endif

    TyrantActuation::updateThrusterBackend(micros());

    const auto actuator_status =
        TyrantActuation::getThrusterBackendStatus(micros());

    if (
        actuator_status.fault_latched &&
        (
            TyrantSafety::getMode() == MODE_MANUAL ||
            TyrantSafety::getMode() == MODE_AUTO
        )
    )
    {
        TyrantSafety::forceSafe();
    }

    updateAutonomyReadiness();

    TyrantConnection::update();
    handleApplicationCommunication();

    if (TyrantScheduler::safetyDue())
    {
        runSafetyTask();
    }

    if (TyrantScheduler::healthDue())
    {
        publishHealthTelemetry();
    }

    if (TyrantScheduler::heartbeatDue())
    {
        publishHeartbeatAndDiagnostics();
    }

    if (TyrantScheduler::controlDue())
    {
        runControlTask();
    }
}
