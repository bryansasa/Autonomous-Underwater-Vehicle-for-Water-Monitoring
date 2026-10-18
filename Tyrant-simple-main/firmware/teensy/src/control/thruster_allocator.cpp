#include "control/thruster_allocator.h"

#include <math.h>

namespace
{
constexpr float MIN_PIVOT = 1.0e-7f;

bool finiteWrench(
    const TyrantControl::WrenchRequest &request
)
{
    return
        isfinite(request.x) &&
        isfinite(request.y) &&
        isfinite(request.z) &&
        isfinite(request.k) &&
        isfinite(request.m) &&
        isfinite(request.n);
}

bool finiteTam(
    const TyrantControl::ThrusterAllocationMatrix &tam
)
{
    if (!tam.valid || tam.enabled_thrusters == 0)
    {
        return false;
    }

    for (uint8_t row = 0; row < TyrantControl::WRENCH_AXIS_COUNT; ++row)
    {
        for (uint8_t column = 0; column < TyrantControl::THRUSTER_COUNT; ++column)
        {
            if (!isfinite(tam.value[row][column]))
            {
                return false;
            }
        }
    }

    return true;
}

bool validConfig(
    const TyrantControl::ThrusterAllocatorConfig &config
)
{
    return
        isfinite(config.damping) &&
        config.damping > 0.0f &&
        isfinite(config.max_abs_command) &&
        config.max_abs_command > 0.0f &&
        config.max_abs_command <= 1.0f;
}

bool solveSixBySix(
    float matrix[TyrantControl::WRENCH_AXIS_COUNT][TyrantControl::WRENCH_AXIS_COUNT],
    float rhs[TyrantControl::WRENCH_AXIS_COUNT],
    float solution[TyrantControl::WRENCH_AXIS_COUNT]
)
{
    float augmented[TyrantControl::WRENCH_AXIS_COUNT][TyrantControl::WRENCH_AXIS_COUNT + 1] {};

    for (uint8_t row = 0; row < TyrantControl::WRENCH_AXIS_COUNT; ++row)
    {
        for (uint8_t column = 0; column < TyrantControl::WRENCH_AXIS_COUNT; ++column)
        {
            augmented[row][column] = matrix[row][column];
        }

        augmented[row][TyrantControl::WRENCH_AXIS_COUNT] = rhs[row];
    }

    for (uint8_t pivot = 0; pivot < TyrantControl::WRENCH_AXIS_COUNT; ++pivot)
    {
        uint8_t best_row = pivot;
        float best_abs = fabsf(augmented[pivot][pivot]);

        for (uint8_t row = pivot + 1; row < TyrantControl::WRENCH_AXIS_COUNT; ++row)
        {
            const float candidate = fabsf(augmented[row][pivot]);
            if (candidate > best_abs)
            {
                best_abs = candidate;
                best_row = row;
            }
        }

        if (!isfinite(best_abs) || best_abs <= MIN_PIVOT)
        {
            return false;
        }

        if (best_row != pivot)
        {
            for (uint8_t column = pivot; column <= TyrantControl::WRENCH_AXIS_COUNT; ++column)
            {
                const float temporary = augmented[pivot][column];
                augmented[pivot][column] = augmented[best_row][column];
                augmented[best_row][column] = temporary;
            }
        }

        const float pivot_value = augmented[pivot][pivot];

        for (uint8_t column = pivot; column <= TyrantControl::WRENCH_AXIS_COUNT; ++column)
        {
            augmented[pivot][column] /= pivot_value;
        }

        for (uint8_t row = 0; row < TyrantControl::WRENCH_AXIS_COUNT; ++row)
        {
            if (row == pivot)
            {
                continue;
            }

            const float factor = augmented[row][pivot];

            for (uint8_t column = pivot; column <= TyrantControl::WRENCH_AXIS_COUNT; ++column)
            {
                augmented[row][column] -= factor * augmented[pivot][column];
            }
        }
    }

    for (uint8_t index = 0; index < TyrantControl::WRENCH_AXIS_COUNT; ++index)
    {
        solution[index] = augmented[index][TyrantControl::WRENCH_AXIS_COUNT];

        if (!isfinite(solution[index]))
        {
            return false;
        }
    }

    return true;
}

float computeResidualNorm(
    const TyrantControl::ThrusterAllocationMatrix &tam,
    const float target[TyrantControl::WRENCH_AXIS_COUNT],
    const float command[TyrantControl::THRUSTER_COUNT]
)
{
    float residual_squared = 0.0f;

    for (uint8_t row = 0; row < TyrantControl::WRENCH_AXIS_COUNT; ++row)
    {
        float achieved = 0.0f;

        for (uint8_t column = 0; column < TyrantControl::THRUSTER_COUNT; ++column)
        {
            achieved += tam.value[row][column] * command[column];
        }

        const float error = target[row] - achieved;
        residual_squared += error * error;
    }

    return sqrtf(residual_squared);
}

} // namespace

namespace TyrantControl
{

ThrusterCommand makeNeutralThrusterCommand(
    uint32_t source_sequence,
    ThrusterAllocationStatus status,
    bool valid
)
{
    ThrusterCommand command {};

    command.source_sequence = source_sequence;
    command.valid = valid;
    command.enabled = false;
    command.saturated = false;
    command.status = status;
    command.residual_norm = 0.0f;

    for (uint8_t index = 0; index < THRUSTER_COUNT; ++index)
    {
        command.value[index] = 0.0f;
    }

    return command;
}

ThrusterCommand allocateNormalizedWrench(
    const ThrusterAllocationMatrix &tam,
    const WrenchRequest &request,
    const ThrusterAllocatorConfig &config
)
{
    if (!finiteTam(tam))
    {
        return makeNeutralThrusterCommand(
            request.source_sequence,
            ThrusterAllocationStatus::INVALID_TAM,
            false
        );
    }

    if (!finiteWrench(request))
    {
        return makeNeutralThrusterCommand(
            request.source_sequence,
            ThrusterAllocationStatus::INVALID_REQUEST,
            false
        );
    }

    if (!validConfig(config))
    {
        return makeNeutralThrusterCommand(
            request.source_sequence,
            ThrusterAllocationStatus::INVALID_CONFIG,
            false
        );
    }

    if (!request.enabled)
    {
        return makeNeutralThrusterCommand(
            request.source_sequence,
            ThrusterAllocationStatus::REQUEST_DISABLED,
            true
        );
    }

    const float target[WRENCH_AXIS_COUNT] {
        request.x,
        request.y,
        request.z,
        request.k,
        request.m,
        request.n
    };

    // ============================================================
    // DAMPED LEAST-SQUARES ALLOCATION
    // u = B^T (B B^T + lambda^2 I)^-1 tau
    // ============================================================

    float normal[WRENCH_AXIS_COUNT][WRENCH_AXIS_COUNT] {};

    for (uint8_t row = 0; row < WRENCH_AXIS_COUNT; ++row)
    {
        for (uint8_t column = 0; column < WRENCH_AXIS_COUNT; ++column)
        {
            float value = 0.0f;

            for (uint8_t thruster = 0; thruster < THRUSTER_COUNT; ++thruster)
            {
                value +=
                    tam.value[row][thruster] *
                    tam.value[column][thruster];
            }

            normal[row][column] = value;
        }

        normal[row][row] += config.damping * config.damping;
    }

    float solved[WRENCH_AXIS_COUNT] {};
    float rhs[WRENCH_AXIS_COUNT] {};

    for (uint8_t axis = 0; axis < WRENCH_AXIS_COUNT; ++axis)
    {
        rhs[axis] = target[axis];
    }

    if (!solveSixBySix(normal, rhs, solved))
    {
        return makeNeutralThrusterCommand(
            request.source_sequence,
            ThrusterAllocationStatus::SOLVER_FAILED,
            false
        );
    }

    ThrusterCommand command {};
    command.source_sequence = request.source_sequence;
    command.valid = true;
    command.enabled = true;
    command.saturated = false;
    command.status = ThrusterAllocationStatus::OK;

    float max_abs = 0.0f;

    for (uint8_t thruster = 0; thruster < THRUSTER_COUNT; ++thruster)
    {
        float value = 0.0f;

        for (uint8_t axis = 0; axis < WRENCH_AXIS_COUNT; ++axis)
        {
            value += tam.value[axis][thruster] * solved[axis];
        }

        if (!isfinite(value))
        {
            return makeNeutralThrusterCommand(
                request.source_sequence,
                ThrusterAllocationStatus::SOLVER_FAILED,
                false
            );
        }

        command.value[thruster] = value;
        const float magnitude = fabsf(value);

        if (magnitude > max_abs)
        {
            max_abs = magnitude;
        }
    }

    if (max_abs > config.max_abs_command)
    {
        const float scale = config.max_abs_command / max_abs;

        for (uint8_t thruster = 0; thruster < THRUSTER_COUNT; ++thruster)
        {
            command.value[thruster] *= scale;
        }

        command.saturated = true;
    }

    command.residual_norm =
        computeResidualNorm(tam, target, command.value);

    if (!isfinite(command.residual_norm))
    {
        return makeNeutralThrusterCommand(
            request.source_sequence,
            ThrusterAllocationStatus::SOLVER_FAILED,
            false
        );
    }

    return command;
}

} // namespace TyrantControl
