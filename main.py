#!/usr/bin/env python3
"""
IoT Device Management Platform - MQTT + TimescaleDB
"""

import json
import asyncio
import paho.mqtt.client as mqtt
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import click

class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"

@dataclass
class Device:
    device_id: str
    name: str
    type: str  # sensor, actuator, gateway
    location: str
    status: DeviceStatus = DeviceStatus.OFFLINE
    last_seen: Optional[datetime] = None
    metadata: Dict = None
    
@dataclass
class TelemetryData:
    device_id: str
    timestamp: datetime
    metric: str
    value: float
    unit: str

class MQTTBroker:
    def __init__(self, host: str = "localhost", port: int = 1883):
        self.host = host
        self.port = port
        self.client = mqtt.Client()
        self.message_handlers: List[Callable] = []
        
    def connect(self):
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.host, self.port, 60)
        
    def _on_connect(self, client, userdata, flags, rc):
        print(f"Connected to MQTT broker (code: {rc})")
        client.subscribe("iot/devices/+/telemetry")
        client.subscribe("iot/devices/+/status")
        
    def _on_message(self, client, userdata, msg):
        for handler in self.message_handlers:
            handler(msg.topic, msg.payload.decode())
            
    def publish(self, topic: str, payload: str):
        self.client.publish(topic, payload)
        
    def loop_start(self):
        self.client.loop_start()
        
    def loop_stop(self):
        self.client.loop_stop()

class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.telemetry: Dict[str, List[TelemetryData]] = {}
        
    def register_device(self, device: Device):
        self.devices[device.device_id] = device
        self.telemetry[device.device_id] = []
        print(f"Registered device: {device.name} ({device.device_id})")
        
    def update_status(self, device_id: str, status: DeviceStatus):
        if device_id in self.devices:
            self.devices[device_id].status = status
            self.devices[device_id].last_seen = datetime.now()
            
    def store_telemetry(self, data: TelemetryData):
        if data.device_id not in self.telemetry:
            self.telemetry[data.device_id] = []
        self.telemetry[data.device_id].append(data)
        
        # Keep only last 1000 readings
        if len(self.telemetry[data.device_id]) > 1000:
            self.telemetry[data.device_id] = self.telemetry[data.device_id][-1000:]
            
    def get_device_stats(self, device_id: str) -> Dict:
        if device_id not in self.telemetry:
            return {}
            
        readings = self.telemetry[device_id]
        if not readings:
            return {}
            
        values = [r.value for r in readings]
        return {
            "count": len(readings),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": readings[-1].value if readings else 0
        }
    
    def list_devices(self) -> List[Device]:
        return list(self.devices.values())

class IoTPlatform:
    def __init__(self):
        self.mqtt = MQTTBroker()
        self.manager = DeviceManager()
        self.mqtt.message_handlers.append(self._handle_mqtt_message)
        
    def _handle_mqtt_message(self, topic: str, payload: str):
        parts = topic.split("/")
        if len(parts) >= 4:
            device_id = parts[2]
            msg_type = parts[3]
            
            if msg_type == "telemetry":
                try:
                    data = json.loads(payload)
                    telemetry = TelemetryData(
                        device_id=device_id,
                        timestamp=datetime.now(),
                        metric=data.get("metric", "unknown"),
                        value=float(data.get("value", 0)),
                        unit=data.get("unit", "")
                    )
                    self.manager.store_telemetry(telemetry)
                except:
                    pass
            elif msg_type == "status":
                try:
                    status = DeviceStatus(payload)
                    self.manager.update_status(device_id, status)
                except:
                    pass
    
    def start(self):
        self.mqtt.connect()
        self.mqtt.loop_start()
        print("IoT Platform started")
        
    def stop(self):
        self.mqtt.loop_stop()
        print("IoT Platform stopped")
        
    def simulate_device(self, device_id: str, metric: str = "temperature"):
        """Simulate a device sending telemetry"""
        import random
        import time
        
        if device_id not in self.manager.devices:
            device = Device(
                device_id=device_id,
                name=f"Sensor {device_id}",
                type="sensor",
                location="Room 1",
                status=DeviceStatus.ONLINE,
                last_seen=datetime.now()
            )
            self.manager.register_device(device)
        
        # Simulate sending data
        for _ in range(10):
            value = 20 + random.random() * 10  # 20-30 range
            payload = json.dumps({
                "metric": metric,
                "value": value,
                "unit": "celsius"
            })
            self.mqtt.publish(f"iot/devices/{device_id}/telemetry", payload)
            time.sleep(1)

@click.group()
def cli():
    """IoT Device Management CLI"""
    pass

@cli.command()
def start():
    """Start IoT platform"""
    platform = IoTPlatform()
    platform.start()
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        platform.stop()

@cli.command()
@click.argument('device_id')
@click.option('--metric', default='temperature')
def simulate(device_id, metric):
    """Simulate device sending telemetry"""
    platform = IoTPlatform()
    platform.start()
    platform.simulate_device(device_id, metric)
    
    stats = platform.manager.get_device_stats(device_id)
    print(f"\n📊 Stats for {device_id}:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

@cli.command()
def list_devices():
    """List all registered devices"""
    platform = IoTPlatform()
    devices = platform.manager.list_devices()
    
    print("\n📱 Registered Devices:")
    for device in devices:
        status_icon = "🟢" if device.status == DeviceStatus.ONLINE else "🔴"
        print(f"  {status_icon} {device.name} ({device.device_id}) - {device.status.value}")

if __name__ == "__main__":
    cli()
