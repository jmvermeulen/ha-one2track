# One2Track GPS - Home Assistant Integration

Custom Home Assistant integration for [One2Track](https://www.one2track.nl/) GPS tracker watches.

## Features

- **Live GPS tracking** on the Home Assistant map
- **13 sensors** per watch: battery, SIM balance, signal strength, steps, speed, altitude, satellites, GPS accuracy, status, location type, address, last seen, last GPS update
- **Fall detection** binary sensor
- **Send messages** to the watch (max 30 characters)
- **Force location update** to get a fresh GPS fix
- **Send commands** to control watch settings (GPS mode, alarms, step counter, etc.)

## Installation

### Manual

1. Copy the `custom_components/one2track` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings** > **Devices & Services** > **Add Integration**
4. Search for **One2Track GPS**
5. Enter your One2Track email and password (same credentials as the app or [one2trackgps.com](https://www.one2trackgps.com))

### HACS

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) > **Custom repositories**
3. Add `https://github.com/jmvermeulen/ha-one2track` as **Integration**
4. Search for **One2Track GPS** and install
5. Restart Home Assistant

## Entities

Each watch creates the following entities:

| Entity | Description |
|--------|-------------|
| `device_tracker.{name}` | GPS position on the map |
| `sensor.{name}_battery` | Battery percentage |
| `sensor.{name}_sim_balance` | Prepaid SIM balance (EUR) |
| `sensor.{name}_signal_strength` | Signal strength (%) |
| `sensor.{name}_steps` | Step counter |
| `sensor.{name}_speed` | Speed (km/h) |
| `sensor.{name}_accuracy` | GPS accuracy (meters) |
| `sensor.{name}_altitude` | Altitude (meters) |
| `sensor.{name}_satellite_count` | Satellites in view |
| `sensor.{name}_status` | GPS / WiFi / Offline |
| `sensor.{name}_location_type` | GPS / WiFi / Cell tower |
| `sensor.{name}_address` | Street address |
| `sensor.{name}_last_seen` | Last communication |
| `sensor.{name}_last_gps` | Last location update |
| `binary_sensor.{name}_tumble` | Fall/tumble detection |

## Services

### `one2track.send_message`

Send a text message to the watch display. Maximum 30 characters.

```yaml
service: one2track.send_message
target:
  entity_id: device_tracker.my_watch
data:
  message: "Time to come home!"
```

### `one2track.force_update`

Activate positioning mode on the watch for approximately 2 minutes, triggering a fresh GPS fix.

```yaml
service: one2track.force_update
target:
  entity_id: device_tracker.my_watch
```

### `one2track.send_command`

Send a raw command to the watch. Available commands depend on the watch model.

```yaml
service: one2track.send_command
target:
  entity_id: device_tracker.my_watch
data:
  code: "0039"
  name: "Refresh location"
```

#### Available command codes

| Code | Description |
|------|-------------|
| `0039` | Refresh location |
| `0048` | Shutdown watch |
| `0057` | Set alarm |
| `0078` | GPS tracking / powersave |
| `0079` | Step counter |

## Configuration

The integration polls the One2Track API every 60 seconds. This can be adjusted in `const.py` (`DEFAULT_SCAN_INTERVAL`).

## How it works

This integration communicates with the One2Track web portal API at `one2trackgps.com`. There is no official REST API - the mobile app and this integration both use the same web endpoints with cookie-based authentication.

The watch itself communicates with One2Track's servers over cellular (2G/GSM). This integration polls those servers for the latest location data.

## Credits

- API research based on analysis of the One2Track Android app and web portal
- Inspired by [vandernorth/one2track](https://github.com/vandernorth/one2track)
