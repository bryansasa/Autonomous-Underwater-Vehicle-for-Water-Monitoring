#pragma once
#include "sensor_types.h"
#include "payload_i2c.h"
#include "power_controller.h"
#include <tyrant_payload_interfaces/msg/payload_water_quality.h>

class WaterQualityManager {
public:
    void begin(PayloadI2c &bus, const PowerController &power);
    void update();
    void setSamplingInterval(uint32_t ms);
    bool takeSnapshotReady();
    WaterQualitySnapshot readAll();
    void populateRosMessage(tyrant_payload_interfaces__msg__PayloadWaterQuality &msg);
    uint32_t errors() const { return errors_; }
private:
    struct EzoChannel {
        uint8_t address, sensor_id;
        SensorData *data;
        bool pending = false;
        uint32_t started_ms = 0, last_poll_ms = 0;
    };
    void start(EzoChannel &channel, uint32_t now);
    void poll(EzoChannel &channel, uint32_t now);
    void fail(SensorData &data);
    void temperature();
    void refreshPowerAndAge();
    PayloadI2c *bus_ = nullptr;
    const PowerController *power_ = nullptr;
    WaterQualitySnapshot data_;
    EzoChannel channels_[3] = {};
    bool previous_power_[4] = {};
    bool cycle_active_ = false, snapshot_ready_ = false, first_cycle_ = true;
    uint32_t last_cycle_ms_ = 0, interval_ms_ = 1000, errors_ = 0;
};
