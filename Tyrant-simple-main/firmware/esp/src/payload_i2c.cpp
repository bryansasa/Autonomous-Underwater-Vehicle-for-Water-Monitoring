#include "payload_i2c.h"
#include "payload_config.h"
bool PayloadI2c::begin(int sda, int scl) {
    initialized_ = wire_.begin(sda, scl, PayloadConfig::I2C_HZ);
    wire_.setTimeOut(PayloadConfig::I2C_TIMEOUT_MS);
    if (!initialized_) record(false);
    return initialized_;
}
bool PayloadI2c::record(bool ok) {
    if (ok) seen_success_ = true;
    else { ++errors_; seen_failure_ = true; last_failure_ms_ = millis(); }
    return ok;
}
bool PayloadI2c::write(uint8_t address, const uint8_t *data, size_t size, bool stop) {
    if (!initialized_) return record(false);
    wire_.beginTransmission(address);
    const bool queued = wire_.write(data, size) == size;
    const bool ack = wire_.endTransmission(stop) == 0;
    return record(queued && ack);
}
bool PayloadI2c::read(uint8_t address, uint8_t *data, size_t size) {
    if (!initialized_) return record(false);
    const size_t received = wire_.requestFrom(address, size);
    size_t count = 0;
    while (wire_.available() && count < size) data[count++] = wire_.read();
    return record(received == size && count == size);
}
bool PayloadI2c::readRegister(uint8_t address, uint8_t reg, uint16_t &value) {
    uint8_t bytes[2];
    if (!write(address, &reg, 1, false) || !read(address, bytes, 2)) return false;
    value = static_cast<uint16_t>(bytes[0]) << 8 | bytes[1];
    return true;
}
bool PayloadI2c::writeRegister(uint8_t address, uint8_t reg, uint16_t value) {
    const uint8_t bytes[] = {reg, static_cast<uint8_t>(value >> 8), static_cast<uint8_t>(value)};
    return write(address, bytes, sizeof(bytes));
}
bool PayloadI2c::healthy() const {
    return initialized_ && seen_success_ && (!seen_failure_ ||
        static_cast<uint32_t>(millis()-last_failure_ms_) > 1000);
}
