#include "control/thruster_allocation.h"

#include <math.h>

namespace
{
constexpr float MIN_DIRECTION_NORM = 1.0e-6f;

bool finiteVector(
    const TyrantControl::ThrusterVector3 &vector
)
{
    return
        isfinite(vector.x) &&
        isfinite(vector.y) &&
        isfinite(vector.z);
}

void clearMatrix(
    TyrantControl::ThrusterAllocationMatrix &matrix
)
{
    for (uint8_t row = 0; row < TyrantControl::WRENCH_AXIS_COUNT; ++row)
    {
        for (uint8_t column = 0; column < TyrantControl::THRUSTER_COUNT; ++column)
        {
            matrix.value[row][column] = 0.0f;
        }
    }

    matrix.enabled_thrusters = 0;
    matrix.valid = false;
}

} // namespace

namespace TyrantControl
{

TamBuildResult buildThrusterAllocationMatrix(
    const ThrusterGeometry (&geometry)[THRUSTER_COUNT],
    ThrusterAllocationMatrix &matrix
)
{
    clearMatrix(matrix);

    for (uint8_t index = 0; index < THRUSTER_COUNT; ++index)
    {
        const auto &thruster = geometry[index];

        if (!thruster.enabled)
        {
            continue;
        }

        if (
            !finiteVector(thruster.position_b_m) ||
            !finiteVector(thruster.direction_b)
        )
        {
            return {
                TamBuildStatus::NONFINITE_GEOMETRY,
                index
            };
        }

        const float direction_norm = sqrtf(
            thruster.direction_b.x * thruster.direction_b.x +
            thruster.direction_b.y * thruster.direction_b.y +
            thruster.direction_b.z * thruster.direction_b.z
        );

        if (
            !isfinite(direction_norm) ||
            direction_norm <= MIN_DIRECTION_NORM
        )
        {
            return {
                TamBuildStatus::ZERO_DIRECTION,
                index
            };
        }

        const ThrusterVector3 direction {
            thruster.direction_b.x / direction_norm,
            thruster.direction_b.y / direction_norm,
            thruster.direction_b.z / direction_norm
        };

        const auto &position = thruster.position_b_m;

        const ThrusterVector3 moment {
            position.y * direction.z - position.z * direction.y,
            position.z * direction.x - position.x * direction.z,
            position.x * direction.y - position.y * direction.x
        };

        // ============================================================
        // TAM COLUMN
        // [ force direction ; r x direction ]
        // BODY frame is FRD: +X forward, +Y right, +Z down.
        // ============================================================

        matrix.value[0][index] = direction.x;
        matrix.value[1][index] = direction.y;
        matrix.value[2][index] = direction.z;
        matrix.value[3][index] = moment.x;
        matrix.value[4][index] = moment.y;
        matrix.value[5][index] = moment.z;

        ++matrix.enabled_thrusters;
    }

    if (matrix.enabled_thrusters == 0)
    {
        return {
            TamBuildStatus::NO_ENABLED_THRUSTERS,
            0
        };
    }

    matrix.valid = true;

    return {
        TamBuildStatus::OK,
        0
    };
}

} // namespace TyrantControl
