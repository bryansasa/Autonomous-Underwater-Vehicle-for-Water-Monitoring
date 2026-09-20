#include "power_controller.h"

PowerController::PowerController()
    : state_conductivity(false),
      state_ph(false),
      state_temperature(false),
      state_do(false) {}

void PowerController::begin() {
    pinMode(PIN_MOSFET_CONDUCTIVITY, OUTPUT);
    pinMode(PIN_MOSFET_PH, OUTPUT);
    pinMode(PIN_MOSFET_TEMPERATURE, OUTPUT);
    pinMode(PIN_MOSFET_DO, OUTPUT);

    // Default safety: Matikan seluruh daya sensor saat startup
    applyPin(PIN_MOSFET_CONDUCTIVITY, false);
    applyPin(PIN_MOSFET_PH, false);
    applyPin(PIN_MOSFET_TEMPERATURE, false);
    applyPin(PIN_MOSFET_DO, false);
}

void PowerController::applyPin(uint8_t pin, bool enable) {
    digitalWrite(pin, enable ? HIGH : LOW);
}

void PowerController::handleRequest(
    const tyrant_payload_interfaces__msg__SensorPowerRequest * req,
    tyrant_payload_interfaces__msg__SensorPowerStatus * res,
    bool system_ready
) {
    res->request_id = req->request_id;
    res->sensor_id = req->sensor_id;
    res->requested_enable = req->enable;

    // Aturan 1: Failsafe Host Disconnect
    if (!system_ready) {
        res->accepted = false;
        res->reason = 5; // SYSTEM_NOT_READY
        switch (req->sensor_id) {
            case 1: res->actual_enabled = state_conductivity; break;
            case 2: res->actual_enabled = state_ph; break;
            case 3: res->actual_enabled = state_temperature; break;
            case 4: res->actual_enabled = state_do; break;
            default: res->actual_enabled = false; break;
        }
        return;
    }

    // Aturan 2: Eksekusi Request Berdasarkan Sensor ID
    switch (req->sensor_id) {
        case 1: // CONDUCTIVITY
            state_conductivity = req->enable;
            applyPin(PIN_MOSFET_CONDUCTIVITY, state_conductivity);
            res->accepted = true;
            res->reason = 1; // REQUEST_ACCEPTED
            res->actual_enabled = state_conductivity;
            break;

        case 2: // PH
            state_ph = req->enable;
            applyPin(PIN_MOSFET_PH, state_ph);
            res->accepted = true;
            res->reason = 1; // REQUEST_ACCEPTED
            res->actual_enabled = state_ph;
            break;

        case 3: // TEMPERATURE
            state_temperature = req->enable;
            applyPin(PIN_MOSFET_TEMPERATURE, state_temperature);
            res->accepted = true;
            res->reason = 1; // REQUEST_ACCEPTED
            res->actual_enabled = state_temperature;
            break;

        case 4: // DISSOLVED_OXYGEN
            state_do = req->enable;
            applyPin(PIN_MOSFET_DO, state_do);
            res->accepted = true;
            res->reason = 1; // REQUEST_ACCEPTED
            res->actual_enabled = state_do;
            break;

        default: // Sensor ID tidak dikenal
            res->accepted = false;
            res->reason = 2; // INVALID_SENSOR
            res->actual_enabled = false;
            break;
    }
}

bool PowerController::isConductivityOn() const { return state_conductivity; }
bool PowerController::isPhOn() const { return state_ph; }
bool PowerController::isTemperatureOn() const { return state_temperature; }
bool PowerController::isDoOn() const { return state_do; }