#include <Arduino.h>
#include <unity.h>

#include "mock_pressure_source.h"

#include "sensors/sensor_manager.h"


MockPressureSource mock_pressure;


void test_no_pressure_source_enters_error()
{
    TyrantSensors::init();


    const auto health =
        TyrantSensors::getPressureHealth();


    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(
            TyrantSensors::SensorState::ERROR
        ),
        static_cast<uint8_t>(
            health.state
        )
    );


    TEST_ASSERT_FALSE(
        health.valid
    );


    TEST_ASSERT_GREATER_THAN_UINT32(
        0,
        health.error_count
    );
}


void test_pressure_becomes_ready()
{
    TyrantSensors::setPressureSource(
        mock_pressure
    );

    TyrantSensors::init();

    TyrantSensors::update();


    const auto health =
        TyrantSensors::getPressureHealth();


    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(
            TyrantSensors::SensorState::READY
        ),
        static_cast<uint8_t>(
            health.state
        )
    );


    TEST_ASSERT_TRUE(
        health.valid
    );
}


void test_pressure_sample()
{
    TyrantSensors::setPressureSource(
        mock_pressure
    );

    TyrantSensors::init();

    TyrantSensors::update();


    TyrantSensors::PressureSample sample {};


    TEST_ASSERT_TRUE(
        TyrantSensors::getPressureSnapshot(
            sample
        )
    );


    TEST_ASSERT_TRUE(
        sample.valid
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.1f,
        101325.0f,
        sample.pressure_pa
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.01f,
        25.0f,
        sample.temperature_c
    );
}


void test_pressure_stats()
{
    TyrantSensors::setPressureSource(
        mock_pressure
    );

    TyrantSensors::init();

    TyrantSensors::update();


    const auto stats =
        TyrantSensors::getPressureStats();


    TEST_ASSERT_GREATER_THAN_UINT32(
        0,
        stats.read_attempts
    );


    TEST_ASSERT_GREATER_THAN_UINT32(
        0,
        stats.read_successes
    );


    TEST_ASSERT_GREATER_THAN_UINT32(
        0,
        stats.samples_produced
    );
}


void test_pressure_becomes_stale()
{
    TyrantSensors::setPressureSource(
        mock_pressure
    );

    TyrantSensors::init();


    mock_pressure.setProducing(
        true
    );

    TyrantSensors::update();


    auto health =
        TyrantSensors::getPressureHealth();


    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(
            TyrantSensors::SensorState::READY
        ),
        static_cast<uint8_t>(
            health.state
        )
    );


    mock_pressure.setProducing(
        false
    );


    delay(1100);


    TyrantSensors::update();


    health =
        TyrantSensors::getPressureHealth();


    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(
            TyrantSensors::SensorState::STALE
        ),
        static_cast<uint8_t>(
            health.state
        )
    );


    TEST_ASSERT_FALSE(
        health.valid
    );

    TyrantSensors::PressureSample
        stale_sample {};


    TEST_ASSERT_FALSE(
        TyrantSensors::takePressureSample(
            stale_sample
        )
    );
}

void test_pressure_snapshot_is_non_destructive()
{
    TyrantSensors::setPressureSource(
        mock_pressure
    );

    TyrantSensors::init();

    TyrantSensors::update();


    TyrantSensors::PressureSample
        first_snapshot {};

    TyrantSensors::PressureSample
        second_snapshot {};


    TEST_ASSERT_TRUE(
        TyrantSensors::getPressureSnapshot(
            first_snapshot
        )
    );


    TEST_ASSERT_TRUE(
        TyrantSensors::getPressureSnapshot(
            second_snapshot
        )
    );


    TEST_ASSERT_EQUAL_UINT32(
        first_snapshot.sequence,
        second_snapshot.sequence
    );
}

void test_pressure_take_does_not_remove_snapshot()
{
    TyrantSensors::setPressureSource(
        mock_pressure
    );

    TyrantSensors::init();

    TyrantSensors::update();


    TyrantSensors::PressureSample
        stream_sample {};

    TyrantSensors::PressureSample
        snapshot {};


    TEST_ASSERT_TRUE(
        TyrantSensors::takePressureSample(
            stream_sample
        )
    );


    TEST_ASSERT_FALSE(
        TyrantSensors::takePressureSample(
            stream_sample
        )
    );


    TEST_ASSERT_TRUE(
        TyrantSensors::getPressureSnapshot(
            snapshot
        )
    );


    TEST_ASSERT_EQUAL_UINT32(
        stream_sample.sequence,
        snapshot.sequence
    );
}
void test_nan_pressure_rejected_from_processing_stream()
{
    TyrantSensors::setPressureSource(
        mock_pressure
    );

    TyrantSensors::init();


    mock_pressure.setPressurePa(
        NAN
    );


    TyrantSensors::update();


    const auto health =
        TyrantSensors::getPressureHealth();


    TEST_ASSERT_FALSE(
        health.valid
    );


    TyrantSensors::PressureSample
        snapshot {};


    TEST_ASSERT_TRUE(
        TyrantSensors::getPressureSnapshot(
            snapshot
        )
    );


    TEST_ASSERT_FALSE(
        snapshot.valid
    );


    TyrantSensors::PressureSample
        processing_sample {};


    TEST_ASSERT_FALSE(
        TyrantSensors::takePressureSample(
            processing_sample
        )
    );
}

void setup()
{
    delay(2000);


    UNITY_BEGIN();


    // Harus pertama, sebelum pressure source
    // pernah dibind.
    RUN_TEST(
        test_no_pressure_source_enters_error
    );


    RUN_TEST(
        test_pressure_becomes_ready
    );


    RUN_TEST(
        test_pressure_sample
    );


    RUN_TEST(
        test_pressure_stats
    );


    RUN_TEST(
        test_pressure_becomes_stale
    );

    RUN_TEST(
        test_pressure_snapshot_is_non_destructive
    );


    RUN_TEST(
        test_pressure_take_does_not_remove_snapshot
    );
    
    RUN_TEST(
        test_nan_pressure_rejected_from_processing_stream
    );

    UNITY_END();
}


void loop()
{
}
