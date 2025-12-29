# Samsung SmartThings Washer + Dryer Domoticz Plugin

A Domoticz Python plugin to retrieve and display the **status of a Samsung washing machine and a Samsung tumble dryer** via the **SmartThings Cloud API**.

It shows the core datapoints you typically need for automations:
- **Power (ON/OFF)**
- **Job/Cycle state** (washer + dryer)
- **Remaining time (min)** (forced to **0 min** when no active cycle, based on JobState)

This plugin uses **SmartThings OAuth 2.0** for secure authentication (Access Token + Refresh Token with automatic refresh).

---

## Key Features and Use Cases

- **Washer + Dryer in one plugin**: one OAuth2 token handling, two devices monitored.
- **Reliable “Remaining time”**: displayed only when an active cycle is running; otherwise shown as **0 min** (prevents stale/default values).
- **Automation-ready**: the `JobState` text device is ideal for DzVents scripts (voice notifications, push alerts, etc.).
- **Extensible**: you can easily add more Samsung capability fields later (progress, modes, energy data, etc.).

---

## 1. SmartThings OAuth 2.0 Access

You need a Client ID, Client Secret, an initial Access Token, and a Refresh Token from SmartThings.

A widely used guide to obtain OAuth 2.0 credentials/tokens is included in the original washer repository as a PDF:
- `SmartThings_Oauth2.0_by_Shashank_Mayya.pdf`

> Tip: keep the PDF in your repo so you still have the guide even if the original blog page changes.

---

## 2. Prerequisites Summary

You must obtain these OAuth values, plus your device IDs:

| Requirement | Used in Plugin As |
|---|---|
| SmartThings Client ID | Domoticz parameter **SmartThings Client ID** |
| SmartThings Client Secret | Domoticz parameter **SmartThings Client Secret** |
| Access Token (initial) | `st_tokens.json` |
| Refresh Token | `st_tokens.json` |
| Washer Device ID | Domoticz parameter **Washer Device ID (SmartThings)** |
| Dryer Device ID | Domoticz parameter **Dryer Device ID (SmartThings)** |

---

## 3. Installation

1. **Copy files** into your Domoticz plugins folder, e.g.:
   `/home/domoticz/plugins/SmartThingsWasherDryer/`

   Required files:
   - `plugin.py`
   - `token_manager.py`

2. **Create `st_tokens.json`** in the same folder:

```json
{
  "access_token": "YOUR-FIRST-ACCESS-TOKEN-HERE",
  "refresh_token": "YOUR-FIRST-REFRESH-TOKEN-HERE",
  "expiry": 0
}
```

Setting `"expiry": 0` forces an immediate refresh on startup.

3. **Restart Domoticz**.

---

## 4. Plugin Configuration

In Domoticz (`Setup` → `Hardware`) add the hardware and fill in:

| Field | Parameter | Description |
|---|---|---|
| SmartThings API URL | Address | Usually: `https://api.smartthings.com` |
| Debug | Port | `0` or `1` |
| ON State Polling Interval (sec) | Mode1 | Polling frequency when **any device is ON** |
| SmartThings Client ID | Mode2 | OAuth Client ID |
| SmartThings Client Secret | Mode3 | OAuth Client Secret |
| Washer Device ID (SmartThings) | Mode4 | Washer deviceId |
| OFF State Polling Interval (sec) | Mode5 | Polling when **both devices are OFF** |
| Dryer Device ID (SmartThings) | Mode6 | Dryer deviceId |

### Polling Logic (simple)
- If **washer OR dryer** is ON → use **ON interval**
- If **both** are OFF → use **OFF interval**

---

## 5. Created Domoticz Devices

On first run the plugin creates these Domoticz devices:

### Washer devices
| Device ID | Name | Type | Description |
|---|---|---|---|
| `WM_Power` | Washer Status (ON/OFF) | Switch | Power state |
| `WM_JobState` | Washing Cycle | Text | Cycle/job state |
| `WM_Remaining` | Washer Remaining Time (min) | Text | Remaining time, **0 min if no active cycle** |

### Dryer devices
| Device ID | Name | Type | Description |
|---|---|---|---|
| `DR_Power` | Dryer Status (ON/OFF) | Switch | Power state |
| `DR_JobState` | Drying Cycle | Text | Cycle/job state |
| `DR_Remaining` | Dryer Remaining Time (min) | Text | Remaining time, **0 min if no active cycle** |

---

## 6. Data Source (SmartThings fields)

All data comes from:

`GET /v1/devices/{deviceId}/status`

### Washer
- Power: `components.main.switch.switch.value`
- JobState: `components.main.samsungce.washerOperatingState.washerJobState.value`
- Remaining (min): `components.main.samsungce.washerOperatingState.remainingTime.value`

### Dryer
- Power: `components.main.switch.switch.value`
- JobState: `components.main.samsungce.dryerOperatingState.dryerJobState.value`
- Remaining (min): `components.main.samsungce.dryerOperatingState.remainingTime.value`

### Remaining time rule
Remaining time is shown as a real value **only when**:
- `JobState != "none"`

Otherwise it is forced to **0 min** to avoid stale/default values.

---

## 7. Automation Example (DzVents voice notification)

Typical approach:
- Trigger on `Washing Cycle` or `Drying Cycle` device change
- Detect transition from active state → `No active wash` / `No active dry`
- Execute a `.sh` that sends a Sonos command to play a prepared MP3

This keeps the plugin simple and puts all “notification logic” into DzVents.

---

## 8. Troubleshooting

### 401 Unauthorized / Token refresh errors
- The plugin automatically refreshes access tokens using the refresh token.
- If refresh fails long-term, regenerate tokens and update `st_tokens.json`, set `"expiry": 0`, restart Domoticz.

### Missing / Unknown state
- Verify the correct Device IDs for washer/dryer.
- Check that your SmartThings OAuth integration includes proper read scope(s), e.g. `r:devices:*`.

### “Remaining time looks wrong”
- Confirm JobState is not `"none"`.
- Some models report default remaining time while idle; the plugin displays **0 min** in idle state by design.

---

## Changelog

- **v2.0.0**: Added Samsung **dryer** support (washer + dryer in one plugin).
- **v2.0.1**: Remaining time logic unified: **0 min when JobState is none** (washer + dryer).

---

## License / Credits

- Built for Domoticz Python plugin framework.
- Uses SmartThings Cloud API (OAuth 2.0).
- Based on the original washer plugin structure and token handling.
