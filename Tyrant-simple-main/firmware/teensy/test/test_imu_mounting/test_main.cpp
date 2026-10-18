#include <Arduino.h>
#include <unity.h>

#include "sensors/imu_mounting.h"


void test_identity_mounting()
{
    const TyrantSensors::ImuMounting
        mounting
    {
        TyrantSensors::ImuAxis::POS_X,
        TyrantSensors::ImuAxis::POS_Y,
        TyrantSensors::ImuAxis::POS_Z
    };


    TEST_ASSERT_TRUE(
        TyrantSensors::
            imuMountingValid(
                mounting
            )
    );


    float body_x = 0.0f;
    float body_y = 0.0f;
    float body_z = 0.0f;


    TyrantSensors::applyImuMounting(
        mounting,

        1.0f,
        2.0f,
        3.0f,

        body_x,
        body_y,
        body_z
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        1.0f,
        body_x
    );

    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        2.0f,
        body_y
    );

    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        3.0f,
        body_z
    );
}


void test_rotated_mounting()
{
    // Body X <- Sensor +Y
    // Body Y <- Sensor -X
    // Body Z <- Sensor +Z

    const TyrantSensors::ImuMounting
        mounting
    {
        TyrantSensors::ImuAxis::POS_Y,
        TyrantSensors::ImuAxis::NEG_X,
        TyrantSensors::ImuAxis::POS_Z
    };


    TEST_ASSERT_TRUE(
        TyrantSensors::
            imuMountingValid(
                mounting
            )
    );


    float body_x = 0.0f;
    float body_y = 0.0f;
    float body_z = 0.0f;


    TyrantSensors::applyImuMounting(
        mounting,

        1.0f,
        2.0f,
        3.0f,

        body_x,
        body_y,
        body_z
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        2.0f,
        body_x
    );

    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        -1.0f,
        body_y
    );

    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        3.0f,
        body_z
    );
}


void test_invalid_left_handed_mounting_rejected()
{
    const TyrantSensors::ImuMounting
        mounting
    {
        TyrantSensors::ImuAxis::POS_X,
        TyrantSensors::ImuAxis::POS_Y,
        TyrantSensors::ImuAxis::NEG_Z
    };


    TEST_ASSERT_FALSE(
        TyrantSensors::
            imuMountingValid(
                mounting
            )
    );
}


void test_mag_uses_same_mounting()
{
    const TyrantSensors::ImuMounting
        mounting
    {
        TyrantSensors::ImuAxis::POS_Y,
        TyrantSensors::ImuAxis::NEG_X,
        TyrantSensors::ImuAxis::POS_Z
    };


    int16_t body_x = 0;
    int16_t body_y = 0;
    int16_t body_z = 0;


    TyrantSensors::applyImuMounting(
        mounting,

        100,
        200,
        300,

        body_x,
        body_y,
        body_z
    );


    TEST_ASSERT_EQUAL_INT16(
        200,
        body_x
    );

    TEST_ASSERT_EQUAL_INT16(
        -100,
        body_y
    );

    TEST_ASSERT_EQUAL_INT16(
        300,
        body_z
    );
}


void test_production_hwt905_mounting_matches_verified_mapping()
{
    const TyrantSensors::ImuMounting mounting
    {
        TyrantSensors::ImuAxis::POS_X,
        TyrantSensors::ImuAxis::NEG_Y,
        TyrantSensors::ImuAxis::NEG_Z
    };

    TEST_ASSERT_TRUE(
        TyrantSensors::imuMountingValid(mounting)
    );

    float body_x = 0.0f;
    float body_y = 0.0f;
    float body_z = 0.0f;

    TyrantSensors::applyImuMounting(
        mounting,
        1.0f,
        2.0f,
        3.0f,
        body_x,
        body_y,
        body_z
    );

    TEST_ASSERT_FLOAT_WITHIN(0.001f, 1.0f, body_x);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -2.0f, body_y);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -3.0f, body_z);
}


void setup()
{
    delay(2000);


    UNITY_BEGIN();


    RUN_TEST(
        test_identity_mounting
    );

    RUN_TEST(
        test_rotated_mounting
    );

    RUN_TEST(
        test_invalid_left_handed_mounting_rejected
    );

    RUN_TEST(
        test_mag_uses_same_mounting
    );

    RUN_TEST(
        test_production_hwt905_mounting_matches_verified_mapping
    );


    UNITY_END();
}


void loop()
{
}