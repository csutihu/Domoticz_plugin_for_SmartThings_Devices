"""
<plugin key="SmartThingsWasher" name="Samsung SmartThings Washer/Dryer" author="csutihu" version="3.9" wikilink="https://github.com/csutihu/Smartthings_washer">
    <description>
        <h2>Samsung SmartThings Washer/Dryer</h2>
        <p>Retrieves and displays the status (ON/OFF, cycle/job state, remaining time) of Samsung appliances via the SmartThings API.</p>
        <p>Authentication is handled via SmartThings OAuth 2.0 (see token_manager.py). This plugin uses the <b>/status</b> endpoint.</p>
        <p><b>Washer:</b></p>
        <ul>
            <li>Power (ON/OFF): components.main.switch.switch.value</li>
            <li>Cycle: components.main.samsungce.washerOperatingState.washerJobState.value</li>
            <li>Remaining time (min): components.main.samsungce.washerOperatingState.remainingTime.value</li>
        </ul>
        <p><b>Dryer:</b></p>
        <ul>
            <li>Power (ON/OFF): components.main.switch.switch.value</li>
            <li>Cycle: components.main.samsungce.dryerOperatingState.dryerJobState.value</li>
            <li>Remaining time (min): components.main.samsungce.dryerOperatingState.remainingTime.value (guarded; some models return a default when idle)</li>
        </ul>
        <p><b>Token file:</b> Place <code>st_tokens.json</code> into the plugin folder (see README in repository).</p>
    </description>
    <params>
        <param field="Address" label="SmartThings API URL" width="300px" required="true" default="https://api.smartthings.com"/>
        <param field="Port" label="Debug (0 = off, 1 = on)" width="40px" required="true" default="0"/>
        <param field="Mode1" label="ON State Polling Interval (sec)" width="60px" required="true" default="60"/>
        <param field="Mode5" label="OFF State Polling Interval (sec)" width="60px" required="true" default="600"/>
        <param field="Mode2" label="SmartThings Client ID" width="300px" required="true"/>
        <param field="Mode3" label="SmartThings Client Secret" width="300px" required="true" password="true"/>
        <param field="Mode4" label="Washer Device ID (SmartThings)" width="300px" required="true"/>
        <param field="Mode6" label="Dryer Device ID (SmartThings)" width="300px" required="false"/>
    </params>
</plugin>
"""

import os
import json
import urllib.request
import Domoticz

from token_manager import TokenManager

# Domoticz DeviceID constants
WM_STATUS_ID = "WM_Power"
WM_JOBSTATE_ID = "WM_JobState"
WM_REMAINING_ID = "WM_Remaining"

DR_STATUS_ID = "DR_Power"
DR_JOBSTATE_ID = "DR_JobState"
DR_REMAINING_ID = "DR_Remaining"


class SmartThingsWMPlugin:
    def __init__(self):
        self.base_url = None
        self.device_id = None  # washer
        self.dryer_device_id = None
        self.client_id = None
        self.client_secret = None
        self.token_manager = None

        self.poll_on_sec = 60
        self.poll_off_sec = 600
        self.heartbeat_seconds = 60
        self.counter_seconds = 0
        self.debug = False

    # ---------- Helpers ----------
    def _get_device_idx(self, device_id):
        for idx in Devices:
            try:
                if Devices[idx].DeviceID == device_id:
                    return idx
            except Exception:
                pass
        return -1

    def _log_debug(self, msg):
        if self.debug:
            Domoticz.Debug(msg)

    # ---------- Domoticz callbacks ----------
    def onStart(self):
        self.base_url = Parameters["Address"].strip().rstrip("/")
        self.client_id = Parameters["Mode2"].strip()
        self.client_secret = Parameters["Mode3"].strip()
        self.device_id = Parameters["Mode4"].strip()  # washer
        self.dryer_device_id = Parameters.get("Mode6", "").strip()

        try:
            self.poll_on_sec = max(60, int(Parameters["Mode1"]))
        except Exception:
            self.poll_on_sec = 60

        try:
            self.poll_off_sec = max(60, int(Parameters["Mode5"]))
        except Exception:
            self.poll_off_sec = 600

        try:
            self.debug = int(Parameters["Port"]) == 1
        except Exception:
            self.debug = False

        if self.debug:
            Domoticz.Debugging(1)
        else:
            Domoticz.Debugging(0)

        Domoticz.Log("Starting SmartThings Washer/Dryer Plugin...")
        Domoticz.Log(f"Base URL: {self.base_url}, Washer Device ID: {self.device_id}, Dryer Device ID: {self.dryer_device_id or '(disabled)'}")
        Domoticz.Log(f"Poll ON: {self.poll_on_sec}s, Poll OFF: {self.poll_off_sec}s, Heartbeat: {self.heartbeat_seconds}s")

        plugin_dir = os.path.dirname(os.path.realpath(__file__))
        self.token_manager = TokenManager(self.client_id, self.client_secret, plugin_dir, self.base_url, debug=self.debug)

        if not self.token_manager.load_tokens():
            Domoticz.Error("st_tokens.json is missing or invalid.")
            return
        Domoticz.Log("Tokens loaded (if present).")

        # Create Washer devices if missing
        if self._get_device_idx(WM_STATUS_ID) < 0:
            Domoticz.Device(Unit=1, Name="Washer Status (ON/OFF)", Type=244, Subtype=73, Switchtype=0, DeviceID=WM_STATUS_ID).Create()
        if self._get_device_idx(WM_JOBSTATE_ID) < 0:
            Domoticz.Device(Unit=2, Name="Washing Cycle", TypeName="Text", DeviceID=WM_JOBSTATE_ID).Create()
        if self._get_device_idx(WM_REMAINING_ID) < 0:
            Domoticz.Device(Unit=3, Name="Washer Remaining Time (min)", TypeName="Text", DeviceID=WM_REMAINING_ID).Create()

        # Create Dryer devices if missing (optional)
        if self.dryer_device_id:
            if self._get_device_idx(DR_STATUS_ID) < 0:
                Domoticz.Device(Unit=4, Name="Dryer Status (ON/OFF)", Type=244, Subtype=73, Switchtype=0, DeviceID=DR_STATUS_ID).Create()
            if self._get_device_idx(DR_JOBSTATE_ID) < 0:
                Domoticz.Device(Unit=5, Name="Drying Cycle", TypeName="Text", DeviceID=DR_JOBSTATE_ID).Create()
            if self._get_device_idx(DR_REMAINING_ID) < 0:
                Domoticz.Device(Unit=6, Name="Dryer Remaining Time (min)", TypeName="Text", DeviceID=DR_REMAINING_ID).Create()
        else:
            Domoticz.Log("Dryer Device ID not set (Mode6 empty) -> Dryer integration disabled.")

        Domoticz.Heartbeat(self.heartbeat_seconds)
        Domoticz.Log(f"Heartbeat set to {self.heartbeat_seconds} seconds.")

    def onStop(self):
        Domoticz.Log("SmartThings Washer/Dryer Plugin stopped.")

    def onHeartbeat(self):
        self.counter_seconds += self.heartbeat_seconds

        is_on = False

        # Washer ON?
        idx_status = self._get_device_idx(WM_STATUS_ID)
        if idx_status >= 0:
            try:
                is_on = (Devices[idx_status].nValue == 1)
            except Exception:
                is_on = False

        # Dryer ON?
        if (not is_on) and self.dryer_device_id:
            idx_dryer = self._get_device_idx(DR_STATUS_ID)
            if idx_dryer >= 0:
                try:
                    is_on = (Devices[idx_dryer].nValue == 1)
                except Exception:
                    is_on = False

        target = self.poll_on_sec if is_on else self.poll_off_sec
        if self.counter_seconds < target:
            return

        self.counter_seconds = 0
        Domoticz.Log(f"Starting SmartThings query (is_on={is_on})...")
        self._query_and_process()

    # ---------- API Request and Processing ----------
    def _query_and_process(self):
        token = self.token_manager.get_access_token()
        if not token:
            if not self.token_manager.refresh_access_token():
                Domoticz.Error("Token refresh failed.")
                return
            token = self.token_manager.get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        # Washer query (existing behavior)
        url = f"{self.base_url}/v1/devices/{self.device_id}/status"
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                code = resp.getcode()
                body = resp.read().decode("utf-8")

            truncated = body if len(body) < 4000 else (body[:4000] + "...(truncated)")
            self._log_debug(f"[API RAW] GET {url} -> HTTP {code}. Payload (truncated): {truncated}")

            if code == 200:
                parsed = json.loads(body)
                self._update_washer_devices_from_api_data(parsed)
            elif code == 401:
                Domoticz.Error("401 Unauthorized – token refresh required.")
                self.token_manager.refresh_access_token()
                return
            else:
                Domoticz.Error(f"[Plugin] HTTP {code} error (washer).")
                return

            # Dryer query (optional)
            if self.dryer_device_id:
                url2 = f"{self.base_url}/v1/devices/{self.dryer_device_id}/status"
                req2 = urllib.request.Request(url2, headers=headers, method="GET")
                with urllib.request.urlopen(req2, timeout=15) as resp2:
                    code2 = resp2.getcode()
                    body2 = resp2.read().decode("utf-8")

                truncated2 = body2 if len(body2) < 4000 else (body2[:4000] + "...(truncated)")
                self._log_debug(f"[API RAW] GET {url2} -> HTTP {code2}. Payload (truncated): {truncated2}")

                if code2 == 200:
                    parsed2 = json.loads(body2)
                    self._update_dryer_devices_from_api_data(parsed2)
                elif code2 == 401:
                    Domoticz.Error("401 Unauthorized (dryer) – token refresh required.")
                    self.token_manager.refresh_access_token()
                else:
                    Domoticz.Error(f"[Plugin] HTTP {code2} error (dryer).")

        except Exception as e:
            Domoticz.Error(f"[Plugin] API call error: {e}")

    # ---------- Data extraction ----------
    def _update_washer_devices_from_api_data(self, data):
        """Direct extraction of washer values: Power, Job, Remaining."""
        try:
            comp = data.get("components", {}).get("main", {})

            power_value = comp.get("switch", {}).get("switch", {}).get("value")
            job_value = (
                comp.get("samsungce.washerOperatingState", {})
                .get("washerJobState", {})
                .get("value")
            )
            remaining = (
                comp.get("samsungce.washerOperatingState", {})
                .get("remainingTime", {})
                .get("value")
            )

            Domoticz.Log(f"[WASHER] Power={repr(power_value)}, Job={repr(job_value)}, Remaining={repr(remaining)}")

            # Power
            idx_power = self._get_device_idx(WM_STATUS_ID)
            is_on = str(power_value).lower() == "on"
            if idx_power >= 0:
                nValue = 1 if is_on else 0
                sValue = "On" if is_on else "Off"
                if Devices[idx_power].nValue != nValue:
                    Devices[idx_power].Update(nValue=nValue, sValue=sValue)
                    Domoticz.Log(f"[Update] Washer status: {sValue}")

            # Job state
            idx_job = self._get_device_idx(WM_JOBSTATE_ID)
            if job_value is None:
                job_text = "Unknown"
            elif job_value == "none":
                job_text = "No active wash"
            else:
                job_text = str(job_value)

            if idx_job >= 0 and Devices[idx_job].sValue != job_text:
                Devices[idx_job].Update(nValue=0, sValue=job_text)
                Domoticz.Log(f"[Update] Washing cycle: {job_text}")

            # Remaining time (0 min when idle/off; some models may keep a stale/default value)
            idx_rem = self._get_device_idx(WM_REMAINING_ID)
            active = (job_value not in (None, "none"))

            if not active:
                remaining_n = 0
                remaining_text = "0 min"
            else:
                if remaining is None:
                    remaining_text = "Unknown"
                    remaining_n = 0
                else:
                    try:
                        remaining_n = int(float(remaining))
                        remaining_text = f"{remaining_n} min"
                    except (ValueError, TypeError):
                        remaining_n = 0
                        remaining_text = str(remaining)

            if idx_rem >= 0 and Devices[idx_rem].sValue != remaining_text:
                Devices[idx_rem].Update(nValue=remaining_n, sValue=remaining_text)
                Domoticz.Log(f"[Update] Washer remaining time: {remaining_text}")

        except Exception as e:
            Domoticz.Error(f"[Plugin] Washer processing error: {e}")

    def _update_dryer_devices_from_api_data(self, data):
        """Direct extraction of dryer values: Power, Job, Remaining (guarded)."""
        try:
            comp = data.get("components", {}).get("main", {})

            power_value = comp.get("switch", {}).get("switch", {}).get("value")
            job_value = (
                comp.get("samsungce.dryerOperatingState", {})
                .get("dryerJobState", {})
                .get("value")
            )
            operating_state = (
                comp.get("samsungce.dryerOperatingState", {})
                .get("operatingState", {})
                .get("value")
            )
            remaining = (
                comp.get("samsungce.dryerOperatingState", {})
                .get("remainingTime", {})
                .get("value")
            )

            Domoticz.Log(f"[DRYER] Power={repr(power_value)}, Job={repr(job_value)}, Op={repr(operating_state)}, Remaining={repr(remaining)}")

            # Power
            idx_power = self._get_device_idx(DR_STATUS_ID)
            is_on = str(power_value).lower() == "on"
            if idx_power >= 0:
                nValue = 1 if is_on else 0
                sValue = "On" if is_on else "Off"
                if Devices[idx_power].nValue != nValue:
                    Devices[idx_power].Update(nValue=nValue, sValue=sValue)
                    Domoticz.Log(f"[Update] Dryer status: {sValue}")

            # Job state
            idx_job = self._get_device_idx(DR_JOBSTATE_ID)
            if job_value is None:
                job_text = "Unknown"
            elif job_value == "none":
                job_text = "No active dry"
            else:
                job_text = str(job_value)

            if idx_job >= 0 and Devices[idx_job].sValue != job_text:
                Devices[idx_job].Update(nValue=0, sValue=job_text)
                Domoticz.Log(f"[Update] Drying cycle: {job_text}")

            # Remaining time (guarded, because some models return a default even when idle)
            idx_rem = self._get_device_idx(DR_REMAINING_ID)
            active = (job_value not in (None, "none"))

            if not active:
                remaining_text = "0 min"
                remaining_n = 0
            else:
                if remaining is None:
                    remaining_text = "Unknown"
                    remaining_n = 0
                else:
                    try:
                        remaining_n = int(float(remaining))
                        remaining_text = f"{remaining_n} min"
                    except (ValueError, TypeError):
                        remaining_n = 0
                        remaining_text = str(remaining)

            if idx_rem >= 0 and Devices[idx_rem].sValue != remaining_text:
                Devices[idx_rem].Update(nValue=remaining_n, sValue=remaining_text)
                Domoticz.Log(f"[Update] Dryer remaining time: {remaining_text}")

        except Exception as e:
            Domoticz.Error(f"[Plugin] Dryer processing error: {e}")


_plugin = SmartThingsWMPlugin()

def onStart():
    _plugin.onStart()

def onStop():
    _plugin.onStop()

def onHeartbeat():
    _plugin.onHeartbeat()

def onCommand(Unit, Command, Level, Hue):
    # This plugin does not implement commands; keep compatibility.
    return
