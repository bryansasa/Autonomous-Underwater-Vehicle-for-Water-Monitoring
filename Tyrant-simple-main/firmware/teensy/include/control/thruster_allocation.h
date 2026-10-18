#pragma once

#include <stdint.h>

namespace TyrantControl
{

constexpr uint8_t THRUSTER_COUNT = 8;
constexpr uint8_t WRENCH_AXIS_COUNT = 6;

struct ThrusterVector3
{
    float x;
    float y;
    float z;
};

struct ThrusterGeometry
{
    ThrusterVector3 position_b_m;
    ThrusterVector3 direction_b;
    bool enabled;
};

struct ThrusterAllocationMatrix
{
    float value[WRENCH_AXIS_COUNT][THRUSTER_COUNT];
    uint8_t enabled_thrusters;
    bool valid;
};

enum class TamBuildStatus : uint8_t
{
    OK = 0,
    NONFINITE_GEOMETRY,
    ZERO_DIRECTION,
    NO_ENABLED_THRUSTERS
};

struct TamBuildResult
{
    TamBuildStatus status;
    uint8_t invalid_thruster_index;
};

TamBuildResult buildThrusterAllocationMatrix(
    const ThrusterGeometry (&geometry)[THRUSTER_COUNT],
    ThrusterAllocationMatrix &matrix
);

} // namespace TyrantControl
