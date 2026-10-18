#include "sensors/imu_mounting.h"

#include <stdint.h>


namespace
{

struct AxisVector
{
    int8_t x;
    int8_t y;
    int8_t z;
};


bool axisVector(
    TyrantSensors::ImuAxis axis,
    AxisVector &vector
)
{
    switch (axis)
    {
        case TyrantSensors::ImuAxis::POS_X:
            vector = {1, 0, 0};
            return true;

        case TyrantSensors::ImuAxis::NEG_X:
            vector = {-1, 0, 0};
            return true;

        case TyrantSensors::ImuAxis::POS_Y:
            vector = {0, 1, 0};
            return true;

        case TyrantSensors::ImuAxis::NEG_Y:
            vector = {0, -1, 0};
            return true;

        case TyrantSensors::ImuAxis::POS_Z:
            vector = {0, 0, 1};
            return true;

        case TyrantSensors::ImuAxis::NEG_Z:
            vector = {0, 0, -1};
            return true;
    }

    return false;
}


AxisVector cross(
    const AxisVector &a,
    const AxisVector &b
)
{
    return {
        static_cast<int8_t>(
            a.y * b.z -
            a.z * b.y
        ),

        static_cast<int8_t>(
            a.z * b.x -
            a.x * b.z
        ),

        static_cast<int8_t>(
            a.x * b.y -
            a.y * b.x
        )
    };
}


bool sameAxis(
    const AxisVector &a,
    const AxisVector &b
)
{
    return (
        a.x == b.x &&
        a.y == b.y &&
        a.z == b.z
    );
}


float axisValue(
    TyrantSensors::ImuAxis axis,
    float x,
    float y,
    float z
)
{
    switch (axis)
    {
        case TyrantSensors::ImuAxis::POS_X:
            return x;

        case TyrantSensors::ImuAxis::NEG_X:
            return -x;

        case TyrantSensors::ImuAxis::POS_Y:
            return y;

        case TyrantSensors::ImuAxis::NEG_Y:
            return -y;

        case TyrantSensors::ImuAxis::POS_Z:
            return z;

        case TyrantSensors::ImuAxis::NEG_Z:
            return -z;
    }

    return 0.0f;
}


int16_t negateInt16(
    int16_t value
)
{
    // +32768 cannot be represented by int16_t.
    if (value == INT16_MIN)
    {
        return INT16_MAX;
    }

    return static_cast<int16_t>(
        -value
    );
}


int16_t axisValue(
    TyrantSensors::ImuAxis axis,
    int16_t x,
    int16_t y,
    int16_t z
)
{
    switch (axis)
    {
        case TyrantSensors::ImuAxis::POS_X:
            return x;

        case TyrantSensors::ImuAxis::NEG_X:
            return negateInt16(x);

        case TyrantSensors::ImuAxis::POS_Y:
            return y;

        case TyrantSensors::ImuAxis::NEG_Y:
            return negateInt16(y);

        case TyrantSensors::ImuAxis::POS_Z:
            return z;

        case TyrantSensors::ImuAxis::NEG_Z:
            return negateInt16(z);
    }

    return 0;
}

}


namespace TyrantSensors
{

bool imuMountingValid(
    const ImuMounting &mounting
)
{
    AxisVector body_x {};
    AxisVector body_y {};
    AxisVector body_z {};


    if (
        !axisVector(
            mounting.body_x,
            body_x
        ) ||
        !axisVector(
            mounting.body_y,
            body_y
        ) ||
        !axisVector(
            mounting.body_z,
            body_z
        )
    )
    {
        return false;
    }


    // Valid mounting must remain a right-handed
    // coordinate system:
    //
    // body_x × body_y = body_z

    const AxisVector expected_z =
        cross(
            body_x,
            body_y
        );


    return sameAxis(
        expected_z,
        body_z
    );
}


void applyImuMounting(
    const ImuMounting &mounting,

    float sensor_x,
    float sensor_y,
    float sensor_z,

    float &body_x,
    float &body_y,
    float &body_z
)
{
    body_x =
        axisValue(
            mounting.body_x,
            sensor_x,
            sensor_y,
            sensor_z
        );

    body_y =
        axisValue(
            mounting.body_y,
            sensor_x,
            sensor_y,
            sensor_z
        );

    body_z =
        axisValue(
            mounting.body_z,
            sensor_x,
            sensor_y,
            sensor_z
        );
}


void applyImuMounting(
    const ImuMounting &mounting,

    int16_t sensor_x,
    int16_t sensor_y,
    int16_t sensor_z,

    int16_t &body_x,
    int16_t &body_y,
    int16_t &body_z
)
{
    body_x =
        axisValue(
            mounting.body_x,
            sensor_x,
            sensor_y,
            sensor_z
        );

    body_y =
        axisValue(
            mounting.body_y,
            sensor_x,
            sensor_y,
            sensor_z
        );

    body_z =
        axisValue(
            mounting.body_z,
            sensor_x,
            sensor_y,
            sensor_z
        );
}

}