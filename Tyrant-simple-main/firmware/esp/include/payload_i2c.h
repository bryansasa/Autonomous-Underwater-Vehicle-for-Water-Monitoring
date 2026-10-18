#pragma once
#include <Wire.h>
#include <stdint.h>
// Tracks real bus transactions. A recent failure keeps health false for 1 s.
class PayloadI2c {
public:
    explicit PayloadI2c(TwoWire &wire) : wire_(wire) {}
    bool begin(int sda, int scl);
    bool write(uint8_t address, const uint8_t *data, size_t size, bool stop = true);
    bool read(uint8_t address, uint8_t *data, size_t size);
    bool readRegister(uint8_t address, uint8_t reg, uint16_t &value);
    bool writeRegister(uint8_t address, uint8_t reg, uint16_t value);
    bool healthy() const;
    uint32_t errors() const { return errors_; }
private:
    bool record(bool ok);
    TwoWire &wire_;
    bool initialized_ = false, seen_success_ = false, seen_failure_ = false;
    uint32_t errors_ = 0, last_failure_ms_ = 0;
};
