#pragma once

#include <stdint.h>


namespace TyrantSensors
{

enum class ImuAxis : int8_t
{
    POS_X =  1,
    NEG_X = -1,

    POS_Y =  2,
    NEG_Y = -2,

    POS_Z =  3,
    NEG_Z = -3
};


struct ImuMounting
{
    // Which SENSOR axis becomes each BODY axis.
    ImuAxis body_x;
    ImuAxis body_y;
    ImuAxis body_z;
};


bool imuMountingValid(
    const ImuMounting &mounting
);


void applyImuMounting(
    const ImuMounting &mounting,

    float sensor_x,
    float sensor_y,
    float sensor_z,

    float &body_x,
    float &body_y,
    float &body_z
);


void applyImuMounting(
    const ImuMounting &mounting,

    int16_t sensor_x,
    int16_t sensor_y,
    int16_t sensor_z,

    int16_t &body_x,
    int16_t &body_y,
    int16_t &body_z
);

}