#ifndef POWER_CONTROLLER_H
#define POWER_CONTROLLER_H

#include <Arduino.h>
#include <tyrant_payload_interfaces/msg/sensor_power_request.h>
#include <tyrant_payload_interfaces/msg/sensor_power_status.h>

// PIN PLACEHOLDER (Sesuaikan nanti dengan skematik hardware)
#define PIN_MOSFET_CONDUCTIVITY  4
#define PIN_MOSFET_PH            5
#define PIN_MOSFET_TEMPERATURE   6
#define PIN_MOSFET_DO            7

class PowerController {
public:
    PowerController();

    // Inisialisasi pin: Seluruh MOSFET wajib default OFF saat boot
    void begin();

    // Pemroses request & penghasil status balasan (ACK)
    void handleRequest(
        const tyrant_payload_interfaces__msg__SensorPowerRequest * req,
        tyrant_payload_interfaces__msg__SensorPowerStatus * res,
        bool system_ready
    );

    // Getter status untuk telemetri subsistem health
    bool isConductivityOn() const;
    bool isPhOn() const;
    bool isTemperatureOn() const;
    bool isDoOn() const;

private:
    bool state_conductivity;
    bool state_ph;
    bool state_temperature;
    bool state_do;

    void applyPin(uint8_t pin, bool enable);
};

#endif