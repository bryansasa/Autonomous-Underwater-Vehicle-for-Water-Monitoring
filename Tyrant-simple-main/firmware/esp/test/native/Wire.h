#pragma once
#include "Arduino.h"
#include <deque>
class TwoWire {
public:
    explicit TwoWire(int=0) {}
    bool online=true;
    unsigned writes=0;
    std::map<uint8_t,std::map<uint8_t,uint16_t>> registers;
    std::map<uint8_t,std::vector<uint8_t>> responses;
    bool begin(int,int,uint32_t) { return true; }
    void setTimeOut(uint16_t) {}
    void beginTransmission(uint8_t address) { address_=address; tx_.clear(); }
    size_t write(const uint8_t *data, size_t n) { tx_.assign(data,data+n); return n; }
    uint8_t endTransmission(bool=true) {
        ++writes;
        if (!online) return 2;
        if (!tx_.empty()) selected_[address_]=tx_[0];
        if (tx_.size()==3) registers[address_][tx_[0]]=(tx_[1]<<8)|tx_[2];
        return 0;
    }
    size_t requestFrom(uint8_t address, size_t count) {
        rx_.clear(); if (!online) return 0;
        if (responses.count(address)) {
            for (size_t i=0;i<count;++i) rx_.push_back(i<responses[address].size()?responses[address][i]:0);
        } else if (registers.count(address)) {
            uint16_t val=registers[address][selected_[address]];
            rx_.push_back(val>>8); rx_.push_back(val&255);
        }
        return rx_.size();
    }
    int available() { return rx_.size(); }
    int read() { const int v=rx_.front(); rx_.pop_front(); return v; }
private:
    uint8_t address_=0;
    std::vector<uint8_t> tx_;
    std::deque<uint8_t> rx_;
    std::map<uint8_t,uint8_t> selected_;
};
