#include "power_controller.h"
#include "payload_config.h"
#ifndef PAYLOAD_SIMULATION
namespace {
const int pins[] = {PayloadConfig::MOSFET_EC, PayloadConfig::MOSFET_PH,
                   PayloadConfig::MOSFET_TEMPERATURE, PayloadConfig::MOSFET_DO};
int level(bool enable) { return (enable == PayloadConfig::MOSFET_ACTIVE_HIGH) ? HIGH : LOW; }
}
#endif
void PowerController::begin() {
    for (unsigned i=0; i<4; ++i) {
#ifndef PAYLOAD_SIMULATION
        digitalWrite(pins[i], level(false));
        pinMode(pins[i], OUTPUT);
#endif
        states_[i] = false;
    }
}
bool PowerController::isEnabled(uint8_t id) const { return id >= 1 && id <= 4 && states_[id-1]; }
uint32_t PowerController::enabledSinceMs(uint8_t id) const { return id >= 1 && id <= 4 ? enabled_since_[id-1] : 0; }
void PowerController::handleRequest(const tyrant_payload_interfaces__msg__SensorPowerRequest *req,
    tyrant_payload_interfaces__msg__SensorPowerStatus *res, bool host_healthy) {
    res->request_id = req->request_id;
    res->sensor_id = req->sensor_id;
    res->requested_enable = req->enable;
    res->accepted = false;
    res->actual_enabled = isEnabled(req->sensor_id);
    if (req->sensor_id < 1 || req->sensor_id > 4) { res->reason = 2; return; }
    // OFF tetap boleh, termasuk ketika host heartbeat telah timeout.
    if (req->enable && !host_healthy) { res->reason = 5; return; }
    const unsigned i = req->sensor_id - 1;
    if (req->enable && !states_[i]) enabled_since_[i] = millis();
#ifndef PAYLOAD_SIMULATION
    digitalWrite(pins[i], level(req->enable));
#endif
    states_[i] = req->enable;
    res->accepted = true;
    res->reason = 1;
    // Status perintah GPIO, bukan feedback kelistrikan MOSFET.
    res->actual_enabled = states_[i];
}
