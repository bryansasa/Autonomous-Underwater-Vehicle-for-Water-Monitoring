#include <cassert>
#include <iostream>
#include "payload_simulation.h"
#include "connection_health.h"
#include "ea_dsra.h"
uint64_t test_time_us=0;
std::map<int,int> test_levels,test_modes;
uint64_t payloadTimeUs() { return test_time_us; }
void setMs(uint64_t ms) { test_time_us=ms*1000; }
void setPower(PowerController &power,uint8_t id,bool enabled,bool healthy=true) {
    tyrant_payload_interfaces__msg__SensorPowerRequest req{100u+id,id,enabled};
    tyrant_payload_interfaces__msg__SensorPowerStatus res{};
    power.handleRequest(&req,&res,healthy); assert(res.accepted && res.actual_enabled==enabled);
}
int main() {
    assert(std::string(PayloadConfig::ROS_NAMESPACE)=="/tyrant/payload_sim");
    PowerController power; power.begin();
    TwoWire w1,w2; PayloadI2c b1(w1),b2(w2);
    PayloadSimulationModel model;
    SimulatedWaterQualityManager sensors(model); sensors.begin(b1,power);
    SimulatedPayloadMonitor monitor(model); monitor.begin(b1,b2);
    sensors.update();
    tyrant_payload_interfaces__msg__PayloadWaterQuality message{};
    sensors.populateRosMessage(message);
    assert(!message.ph_valid && message.ph_age_ms==UINT32_MAX);
    for (uint8_t id=1;id<=4;++id) setPower(power,id,true);
    sensors.readAll(); // scenario epoch starts at first ON, not waiting-for-agent boot time
    setMs(1000); sensors.update(); assert(!sensors.readAll().ph.valid);
    setMs(2000); monitor.update(); sensors.update(); sensors.populateRosMessage(message);
    assert(message.ph_valid && message.conductivity_valid && message.temperature_valid && message.dissolved_oxygen_valid);
    assert(message.ph_age_ms==0 && message.temperature_c==26);
    assert(test_levels.empty() && test_modes.empty() && w1.writes==0 && w2.writes==0);
    std::cout << "PASS simulation namespace, OFF/warm-up semantics, valid synthetic samples, no hardware IO\n";

    EaDsraController dsra; dsra.begin();
    assert(dsra.evaluate(sensors.readAll(),monitor.batteryVoltage()).t_ea_final_ms==5000);
    setMs(47000); monitor.update(); sensors.update();
    const float old_ph=sensors.readAll().ph.value;
    setMs(49000); monitor.update(); sensors.update();
    assert(sensors.readAll().ph.value!=old_ph);
    assert(dsra.evaluate(sensors.readAll(),monitor.batteryVoltage()).t_ea_final_ms<5000);
    setMs(92000); monitor.update(); sensors.update();
    assert(sensors.readAll().dissolved_oxygen.value==1.5f);
    assert(dsra.evaluate(sensors.readAll(),monitor.batteryVoltage()).t_ea_final_ms==1000);
    std::cout << "PASS stable, transition-gradient and critical-DO scenarios drive EA-DSRA\n";

    setMs(120000); monitor.update(); sensors.update();
    assert(isnan(monitor.batteryVoltage()));
    assert(dsra.evaluate(sensors.readAll(),monitor.batteryVoltage()).t_ea_final_ms==1000);
    setMs(124000); monitor.update(); sensors.update();
    auto low=dsra.evaluate(sensors.readAll(),monitor.batteryVoltage());
    assert(low.is_penalty_active && low.soc<30 && low.t_ea_final_ms==5000);
    std::cout << "PASS battery dropout invalidation and low-battery energy penalty scenario\n";

    setMs(151000); monitor.update(); sensors.update(); sensors.populateRosMessage(message);
    assert(!message.conductivity_valid && message.conductivity_state==STATE_ERROR && message.ph_valid);
    assert(message.conductivity_age_ms==27000);
    setMs(166000); monitor.update(); sensors.update();
    tyrant_payload_interfaces__msg__PayloadPower pm{}; monitor.populateThrusterPower(pm);
    assert(!pm.valid && pm.sensor_state==STATE_ERROR && isnan(pm.current_a));
    assert(dsra.evaluate(sensors.readAll(),monitor.batteryVoltage()).t_ea_final_ms==1000);
    setMs(181000); monitor.update(); sensors.update();
    assert(sensors.readAll().conductivity.valid && isfinite(monitor.batteryVoltage()));
    std::cout << "PASS isolated EC failure, INA failure, old sample age and recovery in repeating cycle\n";

    ConnectionHealthManager comm; comm.onConnected(); comm.onHostHeartbeatRx();
    setMs(182001); assert(!comm.isHostHealthy());
    tyrant_payload_interfaces__msg__SensorPowerRequest req{9,2,true};
    tyrant_payload_interfaces__msg__SensorPowerStatus ack{};
    power.handleRequest(&req,&ack,comm.isHostHealthy()); assert(!ack.accepted && ack.reason==5);
    setPower(power,2,false,false); sensors.populateRosMessage(message);
    assert(!message.ph_valid && message.ph_age_ms==UINT32_MAX);
    assert(test_levels.empty() && test_modes.empty() && w1.writes==0 && w2.writes==0);
    std::cout << "PASS simulation uses real heartbeat/command rules and OFF invalidates samples\n";
}
