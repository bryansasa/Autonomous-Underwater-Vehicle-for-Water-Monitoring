#include <Arduino.h>
#include <math.h>
#include <unity.h>

#include "control/thruster_allocation.h"
#include "control/thruster_allocator.h"
#include "config/thruster_config.h"

namespace
{
TyrantControl::ThrusterGeometry emptyThruster()
{
    return {
        {0.0f, 0.0f, 0.0f},
        {1.0f, 0.0f, 0.0f},
        false
    };
}

void clearGeometry(
    TyrantControl::ThrusterGeometry (&geometry)[TyrantControl::THRUSTER_COUNT]
)
{
    for (uint8_t i = 0; i < TyrantControl::THRUSTER_COUNT; ++i)
    {
        geometry[i] = emptyThruster();
    }
}
}

TyrantControl::ThrusterAllocationMatrix makeIdentityLikeTam()
{
    TyrantControl::ThrusterAllocationMatrix tam {};

    for (uint8_t axis = 0; axis < TyrantControl::WRENCH_AXIS_COUNT; ++axis)
    {
        tam.value[axis][axis] = 1.0f;
    }

    tam.enabled_thrusters = 6;
    tam.valid = true;
    return tam;
}

TyrantControl::ThrusterAllocatorConfig makeAllocatorConfig()
{
    return {0.05f, 1.0f};
}

TyrantControl::WrenchRequest makeEnabledWrench()
{
    TyrantControl::WrenchRequest request {};
    request.source_sequence = 9;
    request.command_fresh = true;
    request.enabled = true;
    return request;
}

void setUp() {}
void tearDown() {}

void test_tam_column_uses_force_and_cross_product()
{
    TyrantControl::ThrusterGeometry geometry[TyrantControl::THRUSTER_COUNT];
    clearGeometry(geometry);

    geometry[0] = {
        {1.0f, 0.0f, 0.0f},
        {0.0f, 1.0f, 0.0f},
        true
    };

    TyrantControl::ThrusterAllocationMatrix tam {};
    const auto result = TyrantControl::buildThrusterAllocationMatrix(geometry, tam);

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::TamBuildStatus::OK),
        static_cast<uint8_t>(result.status));
    TEST_ASSERT_TRUE(tam.valid);
    TEST_ASSERT_EQUAL_UINT8(1, tam.enabled_thrusters);

    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, tam.value[0][0]);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 1.0f, tam.value[1][0]);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, tam.value[2][0]);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, tam.value[3][0]);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, tam.value[4][0]);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 1.0f, tam.value[5][0]);
}

void test_tam_normalizes_direction_vector()
{
    TyrantControl::ThrusterGeometry geometry[TyrantControl::THRUSTER_COUNT];
    clearGeometry(geometry);

    geometry[2] = {
        {0.0f, 0.0f, 0.0f},
        {2.0f, 0.0f, 0.0f},
        true
    };

    TyrantControl::ThrusterAllocationMatrix tam {};
    const auto result = TyrantControl::buildThrusterAllocationMatrix(geometry, tam);

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::TamBuildStatus::OK),
        static_cast<uint8_t>(result.status));
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 1.0f, tam.value[0][2]);
}

void test_disabled_thruster_produces_zero_column()
{
    TyrantControl::ThrusterGeometry geometry[TyrantControl::THRUSTER_COUNT];
    clearGeometry(geometry);

    geometry[0].enabled = true;

    TyrantControl::ThrusterAllocationMatrix tam {};
    (void)TyrantControl::buildThrusterAllocationMatrix(geometry, tam);

    for (uint8_t row = 0; row < TyrantControl::WRENCH_AXIS_COUNT; ++row)
    {
        TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, tam.value[row][1]);
    }
}

void test_zero_direction_is_rejected()
{
    TyrantControl::ThrusterGeometry geometry[TyrantControl::THRUSTER_COUNT];
    clearGeometry(geometry);

    geometry[3] = {
        {0.0f, 0.0f, 0.0f},
        {0.0f, 0.0f, 0.0f},
        true
    };

    TyrantControl::ThrusterAllocationMatrix tam {};
    const auto result = TyrantControl::buildThrusterAllocationMatrix(geometry, tam);

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::TamBuildStatus::ZERO_DIRECTION),
        static_cast<uint8_t>(result.status));
    TEST_ASSERT_EQUAL_UINT8(3, result.invalid_thruster_index);
    TEST_ASSERT_FALSE(tam.valid);
}

void test_nonfinite_geometry_is_rejected()
{
    TyrantControl::ThrusterGeometry geometry[TyrantControl::THRUSTER_COUNT];
    clearGeometry(geometry);

    geometry[4] = {
        {NAN, 0.0f, 0.0f},
        {1.0f, 0.0f, 0.0f},
        true
    };

    TyrantControl::ThrusterAllocationMatrix tam {};
    const auto result = TyrantControl::buildThrusterAllocationMatrix(geometry, tam);

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::TamBuildStatus::NONFINITE_GEOMETRY),
        static_cast<uint8_t>(result.status));
    TEST_ASSERT_EQUAL_UINT8(4, result.invalid_thruster_index);
}

void test_no_enabled_thrusters_is_rejected()
{
    TyrantControl::ThrusterGeometry geometry[TyrantControl::THRUSTER_COUNT];
    clearGeometry(geometry);

    TyrantControl::ThrusterAllocationMatrix tam {};
    const auto result = TyrantControl::buildThrusterAllocationMatrix(geometry, tam);

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::TamBuildStatus::NO_ENABLED_THRUSTERS),
        static_cast<uint8_t>(result.status));
    TEST_ASSERT_FALSE(tam.valid);
}


void test_allocator_maps_identity_like_tam()
{
    const auto tam = makeIdentityLikeTam();
    auto request = makeEnabledWrench();
    request.x = 0.4f;
    request.y = -0.2f;
    request.n = 0.3f;

    const auto command =
        TyrantControl::allocateNormalizedWrench(
            tam, request, makeAllocatorConfig());

    TEST_ASSERT_TRUE(command.valid);
    TEST_ASSERT_TRUE(command.enabled);
    TEST_ASSERT_FALSE(command.saturated);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::ThrusterAllocationStatus::OK),
        static_cast<uint8_t>(command.status));
    TEST_ASSERT_FLOAT_WITHIN(2e-3f, 0.4f, command.value[0]);
    TEST_ASSERT_FLOAT_WITHIN(2e-3f, -0.2f, command.value[1]);
    TEST_ASSERT_FLOAT_WITHIN(2e-3f, 0.3f, command.value[5]);
}

void test_allocator_disabled_request_returns_valid_neutral()
{
    const auto tam = makeIdentityLikeTam();
    TyrantControl::WrenchRequest request {};
    request.source_sequence = 4;
    request.enabled = false;

    const auto command =
        TyrantControl::allocateNormalizedWrench(
            tam, request, makeAllocatorConfig());

    TEST_ASSERT_TRUE(command.valid);
    TEST_ASSERT_FALSE(command.enabled);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::ThrusterAllocationStatus::REQUEST_DISABLED),
        static_cast<uint8_t>(command.status));

    for (uint8_t i = 0; i < TyrantControl::THRUSTER_COUNT; ++i)
    {
        TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, command.value[i]);
    }
}

void test_allocator_rejects_invalid_tam()
{
    TyrantControl::ThrusterAllocationMatrix tam {};
    const auto command =
        TyrantControl::allocateNormalizedWrench(
            tam, makeEnabledWrench(), makeAllocatorConfig());

    TEST_ASSERT_FALSE(command.valid);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::ThrusterAllocationStatus::INVALID_TAM),
        static_cast<uint8_t>(command.status));
}

void test_allocator_rejects_nonfinite_request()
{
    const auto tam = makeIdentityLikeTam();
    auto request = makeEnabledWrench();
    request.z = NAN;

    const auto command =
        TyrantControl::allocateNormalizedWrench(
            tam, request, makeAllocatorConfig());

    TEST_ASSERT_FALSE(command.valid);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::ThrusterAllocationStatus::INVALID_REQUEST),
        static_cast<uint8_t>(command.status));
}

void test_allocator_rejects_invalid_config()
{
    const auto tam = makeIdentityLikeTam();
    auto config = makeAllocatorConfig();
    config.damping = 0.0f;

    const auto command =
        TyrantControl::allocateNormalizedWrench(
            tam, makeEnabledWrench(), config);

    TEST_ASSERT_FALSE(command.valid);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::ThrusterAllocationStatus::INVALID_CONFIG),
        static_cast<uint8_t>(command.status));
}

void test_allocator_uniformly_scales_when_saturated()
{
    const auto tam = makeIdentityLikeTam();
    auto request = makeEnabledWrench();
    request.x = 0.8f;
    request.y = 0.4f;

    auto config = makeAllocatorConfig();
    config.max_abs_command = 0.2f;

    const auto command =
        TyrantControl::allocateNormalizedWrench(tam, request, config);

    TEST_ASSERT_TRUE(command.valid);
    TEST_ASSERT_TRUE(command.saturated);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.2f, command.value[0]);
    TEST_ASSERT_FLOAT_WITHIN(2e-3f, 0.1f, command.value[1]);
}

void test_allocator_residual_is_finite()
{
    const auto tam = makeIdentityLikeTam();
    auto request = makeEnabledWrench();
    request.k = 0.5f;

    const auto command =
        TyrantControl::allocateNormalizedWrench(
            tam, request, makeAllocatorConfig());

    TEST_ASSERT_TRUE(command.valid);
    TEST_ASSERT_TRUE(isfinite(command.residual_norm));
    TEST_ASSERT_TRUE(command.residual_norm < 0.01f);
}


void test_synthetic_mock_geometry_is_full_rank_enough_for_mixed_wrench()
{
    TyrantControl::ThrusterGeometry geometry[TyrantControl::THRUSTER_COUNT] {};
    TEST_ASSERT_TRUE(
        TyrantThrusterConfig::loadSyntheticDevelopmentGeometry(geometry));

    TyrantControl::ThrusterAllocationMatrix tam {};
    const auto build =
        TyrantControl::buildThrusterAllocationMatrix(geometry, tam);

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantControl::TamBuildStatus::OK),
        static_cast<uint8_t>(build.status));

    auto request = makeEnabledWrench();
    request.x = 0.2f;
    request.y = -0.1f;
    request.z = 0.15f;
    request.k = 0.05f;
    request.m = -0.04f;
    request.n = 0.08f;

    const auto command =
        TyrantControl::allocateNormalizedWrench(
            tam, request, makeAllocatorConfig());

    TEST_ASSERT_TRUE(command.valid);
    TEST_ASSERT_TRUE(command.enabled);
    TEST_ASSERT_TRUE(command.residual_norm < 0.01f);
}

void setup()
{
    delay(2000);
    UNITY_BEGIN();

    RUN_TEST(test_tam_column_uses_force_and_cross_product);
    RUN_TEST(test_tam_normalizes_direction_vector);
    RUN_TEST(test_disabled_thruster_produces_zero_column);
    RUN_TEST(test_zero_direction_is_rejected);
    RUN_TEST(test_nonfinite_geometry_is_rejected);
    RUN_TEST(test_no_enabled_thrusters_is_rejected);
    RUN_TEST(test_allocator_maps_identity_like_tam);
    RUN_TEST(test_allocator_disabled_request_returns_valid_neutral);
    RUN_TEST(test_allocator_rejects_invalid_tam);
    RUN_TEST(test_allocator_rejects_nonfinite_request);
    RUN_TEST(test_allocator_rejects_invalid_config);
    RUN_TEST(test_allocator_uniformly_scales_when_saturated);
    RUN_TEST(test_allocator_residual_is_finite);
    RUN_TEST(test_synthetic_mock_geometry_is_full_rank_enough_for_mixed_wrench);

    UNITY_END();
}

void loop() {}
