# -*- coding: utf-8 -*-
"""
Foxglove Studio WebSocket Bridge Server for Tyrant-AQ AUV GCS.
Broadcasts real-time vehicle telemetry to Foxglove Studio (https://studio.foxglove.dev)
at ws://localhost:8765 using the Foxglove WebSocket Protocol & JSON streaming.
"""
from __future__ import annotations
import asyncio
import json
import time
import threading
from typing import Set, Dict, Any, Optional
from core.event_hook import EventHook
import websockets


class FoxgloveBridgeServer:
    """
    WebSocket Server compatible with Foxglove Studio and generic WebSocket clients.
    Pure-Python implementation with zero GUI dependencies.
    """
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.is_running = False

        self.server_status_changed = EventHook()  # (is_running, message)
        self.client_count_changed = EventHook()   # (count)
        self.log_emitted = EventHook()            # (message)

        self._thread = None
        self._loop = None
        self._server = None
        self._clients: Set[websockets.WebSocketServerProtocol] = set()
        self._lock = threading.Lock()

        # Foxglove Channel Schema Definitions
        self.channels = [
            {
                "id": 1,
                "topic": "/auv/attitude",
                "encoding": "json",
                "schemaName": "auv_msgs/Attitude",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "number"},
                        "roll": {"type": "number"},
                        "pitch": {"type": "number"},
                        "yaw": {"type": "number"},
                        "depth": {"type": "number"},
                        "target_depth": {"type": "number"}
                    }
                })
            },
            {
                "id": 2,
                "topic": "/auv/water_quality",
                "encoding": "json",
                "schemaName": "auv_msgs/WaterQuality",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "number"},
                        "temp_c": {"type": "number"},
                        "ph": {"type": "number"},
                        "do_mg_l": {"type": "number"},
                        "cond_us_cm": {"type": "number"}
                    }
                })
            },
            {
                "id": 3,
                "topic": "/auv/thrusters",
                "encoding": "json",
                "schemaName": "auv_msgs/Thrusters",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "number"},
                        "pwm1": {"type": "number"},
                        "pwm2": {"type": "number"},
                        "pwm3": {"type": "number"},
                        "pwm4": {"type": "number"},
                        "pwm5": {"type": "number"},
                        "pwm6": {"type": "number"}
                    }
                })
            },
            {
                "id": 4,
                "topic": "/auv/power",
                "encoding": "json",
                "schemaName": "auv_msgs/Power",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "number"},
                        "battery_v": {"type": "number"},
                        "current_a": {"type": "number"},
                        "soc_kalman": {"type": "number"}
                    }
                })
            },
            {
                "id": 5,
                "topic": "/auv/diagnostics",
                "encoding": "json",
                "schemaName": "auv_msgs/Diagnostics",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "number"},
                        "mode": {"type": "string"},
                        "is_armed": {"type": "boolean"},
                        "lmpc_wcet_ms": {"type": "number"},
                        "disturb_surge_n": {"type": "number"},
                        "disturb_sway_n": {"type": "number"}
                    }
                })
            }
        ]

    def start_server(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
        self.server_status_changed.emit(True, f"ws://{self.host}:{self.port}")
        self.log_emitted.emit(f"[FOXGLOVE] WebSocket Server aktif di ws://127.0.0.1:{self.port}")

    def stop_server(self):
        if not self.is_running:
            return
        self.is_running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._shutdown_server(), self._loop)
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        self.server_status_changed.emit(False, "Stopped")
        self.client_count_changed.emit(0)
        self.log_emitted.emit("[FOXGLOVE] WebSocket Server dihentikan.")

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main_server_coroutine())
            self._loop.run_forever()
        except Exception as e:
            self.log_emitted.emit(f"[FOXGLOVE ERROR] {e}")
        finally:
            self._loop.close()

    async def _main_server_coroutine(self):
        self._server = await websockets.serve(
            self._client_handler,
            self.host,
            self.port,
            subprotocols=["foxglove.websocket.v1"]
        )

    async def _shutdown_server(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if self._loop:
            self._loop.stop()

    async def _client_handler(self, websocket, path=None):
        with self._lock:
            self._clients.add(websocket)
            count = len(self._clients)
        self.client_count_changed.emit(count)
        self.log_emitted.emit(f"[FOXGLOVE] Client terhubung dari {websocket.remote_address} (Total: {count})")

        try:
            # 1. Send Foxglove Server Info Handshake
            server_info = {
                "op": "serverInfo",
                "name": "Tyrant-AQ AUV GCS Bridge",
                "capabilities": ["clientPublish"],
                "supportedEncodings": ["json"]
            }
            await websocket.send(json.dumps(server_info))

            # 2. Advertise Available Channels
            advertise_msg = {
                "op": "advertise",
                "channels": self.channels
            }
            await websocket.send(json.dumps(advertise_msg))

            # Listen for incoming client messages (subscribe/unsubscribe/publish)
            async for msg_str in websocket:
                try:
                    msg = json.loads(msg_str)
                    op = msg.get("op", "")
                    if op == "subscribe":
                        # Subscriptions acknowledged
                        pass
                except Exception:
                    pass

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            self.log_emitted.emit(f"[FOXGLOVE CLIENT ERROR] {e}")
        finally:
            with self._lock:
                self._clients.discard(websocket)
                count = len(self._clients)
            self.client_count_changed.emit(count)
            self.log_emitted.emit(f"[FOXGLOVE] Client terputus (Tersisa: {count})")

    def broadcast_telemetry(self, data: Dict[str, Any]):
        """
        Broadcasts telemetry data to all connected Foxglove & WebSocket clients.
        Called from GCS Main Thread at 10 Hz.
        """
        if not self.is_running or not self._loop or not self._loop.is_running():
            return

        with self._lock:
            if not self._clients:
                return
            clients = list(self._clients)

        t_now_ns = int(time.time() * 1e9)
        t_ms = data.get("timestamp", int(time.time() * 1000))

        # Prepare sub-packets
        attitude_data = {
            "timestamp": t_ms,
            "roll": data.get("roll", 0.0),
            "pitch": data.get("pitch", 0.0),
            "yaw": data.get("yaw", 0.0),
            "depth": data.get("depth", 0.0),
            "target_depth": data.get("target_depth", 0.0)
        }
        water_data = {
            "timestamp": t_ms,
            "temp_c": data.get("temp", 0.0),
            "ph": data.get("ph", 0.0),
            "do_mg_l": data.get("do", 0.0),
            "cond_us_cm": data.get("cond", 0.0)
        }
        thruster_data = {
            "timestamp": t_ms,
            "pwm1": data.get("pwm1", 1500),
            "pwm2": data.get("pwm2", 1500),
            "pwm3": data.get("pwm3", 1500),
            "pwm4": data.get("pwm4", 1500),
            "pwm5": data.get("pwm5", 1500),
            "pwm6": data.get("pwm6", 1500)
        }
        power_data = {
            "timestamp": t_ms,
            "battery_v": data.get("battery_v", 0.0),
            "current_a": data.get("current_a", 0.0),
            "soc_kalman": data.get("soc_kalman", 100.0)
        }
        diag_data = {
            "timestamp": t_ms,
            "mode": data.get("mode", "MANUAL"),
            "is_armed": data.get("is_armed", True),
            "lmpc_wcet_ms": data.get("lmpc_wcet", 10.0),
            "disturb_surge_n": data.get("disturb_surge", 0.0),
            "disturb_sway_n": data.get("disturb_sway", 0.0)
        }

        # Foxglove WebSocket Protocol frames (Channel Messages)
        frames = [
            {"op": "message", "channelId": 1, "timestamp": t_now_ns, "data": attitude_data},
            {"op": "message", "channelId": 2, "timestamp": t_now_ns, "data": water_data},
            {"op": "message", "channelId": 3, "timestamp": t_now_ns, "data": thruster_data},
            {"op": "message", "channelId": 4, "timestamp": t_now_ns, "data": power_data},
            {"op": "message", "channelId": 5, "timestamp": t_now_ns, "data": diag_data},
            # Also raw combined telemetry message for simple generic JSON clients
            {"op": "telemetry_raw", "data": data}
        ]

        # Schedule async broadcast on event loop
        asyncio.run_coroutine_threadsafe(self._async_broadcast(clients, frames), self._loop)

    async def _async_broadcast(self, clients, frames):
        for frame in frames:
            msg_str = json.dumps(frame)
            for ws in clients:
                try:
                    await ws.send(msg_str)
                except Exception:
                    pass
