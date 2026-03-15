# One2Track Home Assistant Integration

Custom Home Assistant integration for One2Track GPS tracker watches.

## Project Status

**Phase**: v2.0.0 integration built, not yet tested on HA instance.

### Done
- APK decompiled (v4.3.800, React Native app)
- Full API reverse-engineered and verified against live endpoints
- Login flow tested and working (cookie-based auth + CSRF)
- Message sending tested and confirmed received on watch
- Force location update tested and confirmed working
- All 12 watch command codes discovered
- Session persistence concept validated
- HA integration built with all entities, services, and config flow
- Applied `async_create_clientsession` fix from vandernorth/one2track PR #14

### TODO
- Test integration on actual Home Assistant instance
- Test with watch going between online/offline states
- Test session expiry and re-authentication
- Add geofence entity support (API works, entity not yet implemented)
- Test location history endpoint when watch is actively moving
- Consider adding WiFi SSID-based home/away detection

## App Info

- **Package**: `com.one2track.CaringStar_GoogleMap_One2Track`
- **Version analyzed**: 4.3.800
- **Framework**: React Native (API logic in JS bundle, not native Java)
- **Heavily obfuscated**: Single-letter package names, minified JS bundle
- **Watch model**: Connect MOVE

## API

**Base URL**: `https://www.one2trackgps.com`
**Test URL**: `https://test.one2trackgps.com`
**CDN**: `https://cdn.one2track.com`
**Backend**: Ruby on Rails (Phusion Passenger + nginx)
**Auth**: Cookie-based (`_iadmin` session cookie + CSRF tokens)

There is no separate REST API. The mobile app uses the same web endpoints with cookie auth.
The web portal IS the API.

### Authentication Flow

1. `GET /auth/users/sign_in` — extract CSRF token from `<meta name="csrf-token">` + `_iadmin` cookie
2. `POST /auth/users/sign_in` with form data (`authenticity_token`, `user[login]`, `user[password]`, `gdpr=1`, `user[remember_me]=1`) — returns 302 + new `_iadmin` cookie
3. `GET /` with cookie — 302 redirect to `/users/{account_id}/devices` — extract account_id from Location header
4. All subsequent calls use `_iadmin` cookie + `Accept: application/json`

**Important**:
- When already logged in, `GET /auth/users/sign_in` returns 302 (not 200) — get CSRF from other pages instead
- `user[remember_me]=1` gives long-lived sessions (weeks/months via Devise)
- MUST use `async_create_clientsession` (not `async_get_clientsession`) — the shared HA session has a persistent cookie jar that causes duplicate `_iadmin` cookies and auth failures (discovered independently in vandernorth/one2track PR #14)

### Verified Endpoints (tested 2026-03-15)

| Endpoint | Method | Accept Header | Status | Notes |
|----------|--------|---------------|--------|-------|
| `/auth/users/sign_in` | GET | text/html | Working | Returns login page with CSRF token |
| `/auth/users/sign_in` | POST | - | Working | Form POST, returns 302 + cookie |
| `/users/{account_id}/devices` | GET | application/json | Working | Returns full device list with locations |
| `/devices/{uuid}/geofences` | GET | application/json | Working | Returns fences + device summary |
| `/devices/{uuid}/messages` | POST | text/vnd.turbo-stream.html | Working | Sends text message, returns Turbo Stream HTML (max 30 chars) |
| `/devices/{uuid}/history?date=YYYY-MM-DD` | GET | application/json | Working | Returns location history (empty when watch offline) |
| `/devices/{uuid}/functions?list_only=true` | GET | text/html | Working | Lists available commands for this watch model |
| `/api/devices/{uuid}/functions` | POST | - | Working | Sends command to watch. Success: "Wijziging is opgeslagen". Failure (offline): "Wijziging kon niet opgeslagen worden" |

### Endpoints NOT available on web API (app-only, returned 404)

Found in the React Native JS bundle but not served by the web backend.

| Endpoint | Found in |
|----------|----------|
| `/api/command/send_command` | JS bundle (prod URL) |
| `/api/command/send_voicemail` | JS bundle (test URL only) |
| `/guardian_requests` | JS bundle |
| `/guardian_invite?serial_number=` | JS bundle |
| `/available_languages` | JS bundle |
| `/users/{id}/network_info` | JS bundle |
| `/users/{id}/update_password` | JS bundle |
| `/devices/{uuid}/device_events` | JS bundle |

### Command Codes (via `/api/devices/{uuid}/functions`)

Available for watch model "Connect MOVE" (discovered from `/devices/{uuid}/functions?list_only=true`):

| Code | Dutch Name | English | Purpose |
|------|-----------|---------|---------|
| `0001` | SOS nummer | SOS number | Configure SOS number |
| `0011` | Fabrieksinstellingen terugzetten | Factory reset | Reset to factory defaults |
| `0039` | Ververs locatie | Refresh location | Force GPS/location update (~2 min active mode) |
| `0048` | Horloge uitzetten | Shutdown watch | Power off the watch remotely |
| `0057` | Alarm instellen | Set alarm | Configure alarm on watch |
| `0067` | Wijzig toestel wachtwoord | Change device password | Change the watch admin password |
| `0078` | GPS tracking/powersave | GPS tracking/powersave | Toggle GPS tracking mode vs power save |
| `0079` | Stappenteller | Step counter | Enable/disable step counter |
| `0080` | Toegangslijst 1 | Access list 1 | Allowed phone numbers list 1 |
| `0081` | Toegangslijst 2 | Access list 2 | Allowed phone numbers list 2 |
| `0084` | Intercom | Intercom | Remote listen-in / intercom |
| `0124` | Stel taal en tijdzone in | Set language & timezone | Configure locale settings |

**Sending commands** requires:
- `X-CSRF-Token` header (get from any HTML page's `<meta name="csrf-token">`)
- `X-Requested-With: XMLHttpRequest` header
- `Content-Type: application/x-www-form-urlencoded; charset=UTF-8`
- Form body: `utf8=✓&function[code]=XXXX&function[name]=...`
- Some commands accept `function[value]=` (e.g., 0078 for GPS interval seconds)
- Commands return HTTP 200 regardless of success — parse response text for "opgeslagen" (saved) vs "niet" (not)

### Device JSON Response

```json
[
  {
    "device": {
      "id": 123456,
      "serial_number": "0901234567",
      "name": "MyWatch",
      "phone_number": "0031600000000",
      "status": "OFFLINE",
      "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "last_location": {
        "id": 12345,
        "last_communication": "2026-03-06T05:00:26.000+01:00",
        "last_location_update": "2026-03-05T10:50:13.000+01:00",
        "address": "Kerkstraat 1, 1234AB Amsterdam",
        "latitude": "52.370216",
        "longitude": "4.895168",
        "altitude": "0.0",
        "location_type": "WIFI",
        "signal_strength": 25,
        "satellite_count": 0,
        "speed": "0.0",
        "battery_percentage": 85,
        "meta_data": {
          "tumble": "0",
          "steps": "0",
          "stations": [
            {"strength": "114", "mnc": "8", "mcc": "204", "lac": "1234", "cid": "56789"}
          ],
          "routers": [
            {"signalStrength": "-61", "name": "MyWiFi", "macAddress": "aa:bb:cc:dd:ee:ff"}
          ],
          "course": 0.0,
          "accuracy_meters": 7.5,
          "accuracy": "V"
        },
        "host": "1.2.3.4",
        "port": 4000
      },
      "simcard": {
        "balance_cents": 500.0,
        "tariff_type": "prepaid"
      }
    }
  }
]
```

**Status values**: `OFFLINE`, `WIFI`, `ONLINE` (GPS)
**Location types**: `WIFI`, `GPS`, `LBS` (cell tower)
**Accuracy**: `V` = invalid/estimated, `A` = valid GPS fix

### Geofence Response

```json
{
  "fences": [],
  "device": {
    "name": "MyWatch",
    "latitude": "52.370216",
    "longitude": "4.895168",
    "status": "OFFLINE",
    "icon": "/assets/device_location_offline-....png"
  },
  "translations": { "edit": "Bewerken", "delete": "Verwijderen", "submit": "Opslaan", "copy": "Kopiëren" }
}
```

## Integration Architecture

```
custom_components/one2track/
├── __init__.py          # Entry setup, platform forwarding
├── api.py               # One2TrackApiClient (auth, devices, messages, commands)
├── config_flow.py       # UI config flow (email + password)
├── const.py             # Constants, command codes
├── coordinator.py       # DataUpdateCoordinator (60s polling)
├── device_tracker.py    # GPS map entity with accuracy
├── sensor.py            # 13 sensors (battery, steps, speed, address, etc.)
├── binary_sensor.py     # Fall/tumble detection
├── services.py          # send_message, force_update, send_command
├── services.yaml        # Service UI definitions
├── manifest.json
├── strings.json
└── translations/en.json
```

### Entities per watch device

| Type | Entity | Description |
|------|--------|-------------|
| Device tracker | `device_tracker.{watch_name}` | GPS position on map |
| Sensor | `sensor.{watch_name}_battery` | Battery percentage |
| Sensor | `sensor.{watch_name}_sim_balance` | SIM prepaid balance (EUR) |
| Sensor | `sensor.{watch_name}_signal_strength` | Signal strength % |
| Sensor | `sensor.{watch_name}_steps` | Step counter |
| Sensor | `sensor.{watch_name}_speed` | Speed (km/h) |
| Sensor | `sensor.{watch_name}_accuracy` | GPS accuracy (meters) |
| Sensor | `sensor.{watch_name}_altitude` | Altitude (meters) |
| Sensor | `sensor.{watch_name}_satellite_count` | Satellites in view |
| Sensor | `sensor.{watch_name}_status` | GPS / WiFi / Offline |
| Sensor | `sensor.{watch_name}_location_type` | GPS / WiFi / Cell tower |
| Sensor | `sensor.{watch_name}_address` | Street address |
| Sensor | `sensor.{watch_name}_last_seen` | Last communication timestamp |
| Sensor | `sensor.{watch_name}_last_gps` | Last location update timestamp |
| Binary sensor | `binary_sensor.{watch_name}_tumble` | Fall detection |

### Services

| Service | Description |
|---------|-------------|
| `one2track.send_message` | Send text to watch (max 30 chars) |
| `one2track.force_update` | Trigger location refresh (~2 min) |
| `one2track.send_command` | Send any command code with optional value |

## Reference Material

- `reference-integration/` — Cloned vandernorth/one2track HA integration (v1.2.6)
- `one2track.apk` — Downloaded APK v4.3.800
- `one2track-decompiled/` — jadx decompiled output
- `session_test.py` — Standalone API test script with session persistence
- vandernorth/one2track PR #14 — Contains fixes for deprecated HA APIs and the shared session cookie jar bug

## Key Lessons

1. **No REST API exists** — the app and web portal use the same Rails web endpoints with cookie auth
2. **Shared HA session causes auth failures** — must use `async_create_clientsession` for isolated cookie jar
3. **Commands return HTTP 200 regardless** — must parse response text for success/failure
4. **CSRF tokens rotate** — need fresh token before each POST action
5. **Watch offline = commands silently fail** — no way to queue commands for later
