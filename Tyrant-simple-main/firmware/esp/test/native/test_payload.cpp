#include <cassert>
#include <iostream>
#include <string>
#include "connection_health.h"
#include "power_controller.h"
#include "water_quality_lib.h"
#include "payload_monitor.h"
#include "ea_dsra.h"
#include "payload_config.h"
#include "transport_health.h"
uint64_t test_time_us=0;
std::map<int,int> test_levels, test_modes;
uint64_t payloadTimeUs() { return test_time_us; }
void advance(uint32_t ms) { test_time_us+=static_cast<uint64_t>(ms)*1000; }
void request(PowerController &p, uint8_t id, bool enable, bool healthy=true) {
    tyrant_payload_interfaces__msg__SensorPowerRequest req{42,id,enable};
    tyrant_payload_interfaces__msg__SensorPowerStatus res{};
    p.handleRequest(&req,&res,healthy); assert(res.accepted); assert(res.actual_enabled==enable);
}
void reply(TwoWire &w, uint8_t addr, const std::string &s, uint8_t code=1) {
    auto &v=w.responses[addr]; v={code}; v.insert(v.end(),s.begin(),s.end()); v.push_back(0);
}
void readySensor(SensorData &s, float v) { s.value=v; s.valid=true; s.state=STATE_READY; s.seen=true; s.last_sample_us=payloadTimeUs(); }
int main() {
    TransportHealth link;
    assert(!link.probeFailed()); assert(!link.probeFailed());
    link.probeSucceeded(); assert(!link.probeFailed()); // Good probe breaks failure streak.
    assert(!link.probeFailed()); assert(link.probeFailed());
    link.reset(); assert(!link.probeFailed());
    link.publishResult(false,100); assert(!link.publishingStalled(200));
    link.publishResult(true,200); assert(!link.publishingStalled(5000));
    link.publishResult(false,UINT32_MAX-100);
    assert(!link.publishingStalled(100)); assert(link.publishingStalled(3000));
    link.reset(); assert(!link.publishingStalled(4000));
    std::cout << "PASS transient transport errors tolerated; sustained loss and millis rollover trigger recovery\n";
    ConnectionHealthManager comm;
    tyrant_payload_interfaces__msg__PayloadCommunicationDiagnostics diag{};
    comm.populateDiagnostics(diag); assert(diag.connection_state==0 && diag.host_heartbeat_age_ms==UINT32_MAX);
    comm.onConnected(); comm.onHostHeartbeatRx(); assert(comm.isHostHealthy());
    advance(1001); assert(!comm.isHostHealthy()); // No diagnostic call needed to expire.
    comm.populateDiagnostics(diag); assert(diag.host_heartbeat_timeout_count==1);
    comm.isHostHealthy(); comm.populateDiagnostics(diag); assert(diag.host_heartbeat_timeout_count==1);
    comm.onDisconnected(); comm.onConnected(); assert(!comm.isHostHealthy());
    comm.populateDiagnostics(diag); assert(diag.reconnect_count==1 && diag.disconnect_count==1);
    test_time_us=(static_cast<uint64_t>(UINT32_MAX)-500)*1000;
    comm.onHostHeartbeatRx(); advance(700); assert(comm.isHostHealthy()); advance(301); assert(!comm.isHostHealthy());
    std::cout << "PASS heartbeat timeout, reconnect invalidation, millis rollover\n";

    PowerController p; p.begin();
    for (unsigned id=1;id<=4;++id) assert(!p.isEnabled(id));
    tyrant_payload_interfaces__msg__SensorPowerRequest req{7,1,true};
    tyrant_payload_interfaces__msg__SensorPowerStatus res{};
    p.handleRequest(&req,&res,false); assert(!res.accepted && res.reason==5);
    request(p,1,true); request(p,1,false,false);
    req.sensor_id=99; p.handleRequest(&req,&res,false); assert(res.reason==2);
    std::cout << "PASS independent power channels; OFF accepted without heartbeat\n";

    TwoWire wire; PayloadI2c bus(wire); assert(bus.begin(8,9));
    WaterQualityManager sensors; sensors.begin(bus,p);
    assert(test_modes[PayloadConfig::MOSFET_DO]==OUTPUT);
    assert(test_modes[PayloadConfig::TEMPERATURE_ADC]==INPUT);
    sensors.update(); assert(wire.writes==0); // No EZO transactions while switched off.
    tyrant_payload_interfaces__msg__PayloadWaterQuality wq{};
    sensors.populateRosMessage(wq); assert(!wq.ph_valid && wq.ph_age_ms==UINT32_MAX);
    for (uint8_t id=1;id<=4;++id) request(p,id,true);
    reply(wire,0x63,"7.25"); reply(wire,0x64,"1234,456,789"); reply(wire,0x61,"0.00");
    advance(1500); sensors.update(); advance(900); sensors.update();
    assert(sensors.takeSnapshotReady()); sensors.populateRosMessage(wq);
    assert(wq.ph_valid && wq.ph==7.25f && wq.conductivity_valid && wq.conductivity_us_cm==1234);
    assert(wq.dissolved_oxygen_valid && wq.dissolved_oxygen_mg_l==0);
    assert(wq.ph_age_ms==0 && !wq.temperature_valid);
    assert(wq.timestamp_us>UINT32_MAX); // Real 64-bit uptime, not cast micros().
    wire.online=false; advance(100); sensors.update(); sensors.populateRosMessage(wq);
    assert(!wq.ph_valid && wq.ph_state==STATE_ERROR && wq.ph_age_ms==100);
    wire.online=true;
    reply(wire,0x63,"nan"); reply(wire,0x64,"garbage"); reply(wire,0x61,"   ");
    advance(1000); sensors.update(); advance(900); sensors.update(); sensors.populateRosMessage(wq);
    assert(!wq.ph_valid && !wq.conductivity_valid && !wq.dissolved_oxygen_valid);
    reply(wire,0x63,"7.2"); reply(wire,0x64,"10"); reply(wire,0x61,"8");
    advance(100); sensors.update(); advance(900); sensors.update();
    assert(sensors.readAll().ph.valid);
    advance(6501); sensors.populateRosMessage(wq); assert(!wq.ph_valid && wq.ph_state==STATE_STALE);
    request(p,2,false); sensors.populateRosMessage(wq); assert(wq.ph_state==STATE_NOT_INITIALIZED && wq.ph_age_ms==UINT32_MAX);
    std::cout << "PASS EZO parsing, missing device, stale data, power-off invalidation, 64-bit time\n";
    WaterQualityManager busy; busy.begin(bus,p);
    request(p,2,true); advance(1500);
    for (uint8_t addr : {0x61,0x63,0x64}) reply(wire,addr,"",254);
    busy.update(); advance(900); busy.update();
    assert(!busy.takeSnapshotReady());
    advance(600); busy.update(); assert(busy.takeSnapshotReady());
    assert(busy.readAll().ph.state==STATE_ERROR && !busy.readAll().ph.valid);
    reply(wire,0x61,"8"); reply(wire,0x63,"7.2"); reply(wire,0x64,"123");
    busy.update(); advance(1600); busy.update();
    assert(!busy.readAll().ph.valid && busy.readAll().ph.state==STATE_ERROR);
    busy.update(); request(p,2,false); busy.readAll(); request(p,2,true);
    busy.update(); assert(!busy.readAll().ph.valid); // New ON requires new conversion after warm-up.
    std::cout << "PASS EZO busy timeout, delayed conversion rejection and power-cycle invalidation\n";

    TwoWire wi; PayloadI2c bi(wi); bi.begin(10,11);
    wi.registers[0x40]={{0xFE,0x5449},{0xFF,0x2260},{6,8},{2,19200},{1,30000}};
    Ina226Monitor ina; ina.begin(bi,0x40,PayloadConfig::THRUSTER_SHUNT_OHM,2);
    ina.sample(); advance(100); ina.sample();
    tyrant_payload_interfaces__msg__PayloadPower power{}; ina.populate(power);
    assert(power.valid && fabsf(power.current_a-200)<0.001 && fabsf(power.bus_voltage_v-24)<0.001);
    assert(fabsf(power.power_w-4800)<0.1);
    wi.registers[0x40][1]=static_cast<uint16_t>(-30000); advance(100); ina.sample(); ina.populate(power);
    assert(power.current_a < -199.99f);
    wi.online=false; ina.sample(); ina.populate(power); assert(!power.valid && isnan(ina.voltageForSampling()));
    wi.online=true; wi.registers[0x40][1]=4000;
    Ina226Monitor sensor_ina; sensor_ina.begin(bi,0x40,PayloadConfig::SENSOR_SHUNT_OHM,1);
    sensor_ina.sample(); advance(100); sensor_ina.sample(); sensor_ina.populate(power);
    assert(power.valid && fabsf(power.current_a-0.1f)<0.0001);
    wi.registers[0x40][6]=0; advance(501); sensor_ina.sample(); sensor_ina.populate(power);
    assert(!power.valid && power.sensor_state==STATE_STALE);
    Ina226Monitor uncal; uncal.begin(bi,0x40,0,1); wi.registers[0x40][6]=8;
    uncal.sample(); advance(100); uncal.sample(); uncal.populate(power);
    assert(!power.valid && isnan(power.current_a) && isfinite(uncal.voltageForSampling()));
    wi.registers[0x40][0xFF]=0;
    Ina226Monitor wrong_id; wrong_id.begin(bi,0x40,0.1,1); wrong_id.sample(); wrong_id.populate(power);
    assert(!power.valid && power.sensor_state==STATE_ERROR);
    std::cout << "PASS INA226 200A/75mV and R100 scaling, sign, stale, NACK, calibration and ID checks\n";

    TwoWire sensor_wire, thruster_wire;
    PayloadI2c sensor_bus(sensor_wire), thruster_bus(thruster_wire);
    sensor_bus.begin(8,9); thruster_bus.begin(10,11);
    for (auto *w : {&sensor_wire,&thruster_wire}) {
        w->registers[0x40]={{0xFE,0x5449},{0xFF,0x2260},{6,8},{2,19200},{1,4000}};
    }
    PayloadMonitor monitor; monitor.begin(sensor_bus,thruster_bus);
    monitor.update(); advance(200); monitor.update();
    tyrant_payload_interfaces__msg__PayloadPower sensor_power{},thruster_power{};
    monitor.populateSensorPower(sensor_power); monitor.populateThrusterPower(thruster_power);
    assert(sensor_power.valid && thruster_power.valid);
    thruster_wire.online=false; advance(200); monitor.update();
    monitor.populateSensorPower(sensor_power); monitor.populateThrusterPower(thruster_power);
    assert(sensor_power.valid && !thruster_power.valid);
    tyrant_payload_interfaces__msg__PayloadHealth health{};
    monitor.populateHealth(health,sensors.readAll(),p,sensors.errors());
    assert(health.i2c_bus1_healthy && !health.i2c_bus2_healthy && health.i2c_bus2_error_count>0);
    std::cout << "PASS independent I2C buses: failed thruster INA preserves sensor INA\n";

    EaDsraController dsra; dsra.begin(); WaterQualitySnapshot snap;
    readySensor(snap.ph,7); readySensor(snap.dissolved_oxygen,8);
    assert(dsra.evaluate(snap,25.2f).t_ea_final_ms==5000);
    advance(1000); readySensor(snap.ph,9); readySensor(snap.dissolved_oxygen,8);
    assert(dsra.evaluate(snap,25.2f).t_ea_final_ms==1000);
    readySensor(snap.dissolved_oxygen,1.9f);
    dsra.begin(); assert(dsra.evaluate(snap,19.8f).t_ea_final_ms==1000);
    readySensor(snap.dissolved_oxygen,8);
    assert(dsra.evaluate(snap,NAN).t_ea_final_ms==1000);
    snap=WaterQualitySnapshot{}; assert(dsra.evaluate(snap,25.2f).t_ea_final_ms==1000);
    std::cout << "PASS adaptive sampling, critical DO override and invalid-input fallback\n";
}
