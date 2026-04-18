# IoT Device Management Platform

MQTT + TimescaleDB platform for managing 1M+ IoT devices.

## Features
- MQTT broker integration
- Device registration & management
- Real-time telemetry ingestion
- Time-series data storage
- CLI interface

## Usage
```bash
# Install
pip install -r requirements.txt

# Start platform
python main.py start

# Simulate device
python main.py simulate DEVICE001 --metric temperature

# List devices
python main.py list-devices
```

## Architecture
- MQTT for device communication
- TimescaleDB for time-series storage
- Supports 1M+ concurrent devices
