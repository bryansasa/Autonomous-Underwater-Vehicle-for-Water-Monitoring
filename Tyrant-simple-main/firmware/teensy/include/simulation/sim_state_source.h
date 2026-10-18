#pragma once

#include <stdint.h>

#include "estimation/simple_state_estimator.h"

namespace TyrantSimulation
{

struct SimStateSourceConfig
{
    uint32_t timeout_us;
};

void initSimStateSource(const SimStateSourceConfig &config);

bool acceptSimState(
    const TyrantSimpleEstimator::State &state,
    uint32_t received_at_us
);

bool getSimState(
    TyrantSimpleEstimator::State &state,
    uint32_t now_us
);

uint32_t simStateAgeUs(uint32_t now_us);
bool simStateSeen();

} // namespace TyrantSimulation
