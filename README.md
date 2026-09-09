# NEELA YAAN · Autonomous Polar Ocean Mission Control

A runnable SIH **software-system prototype**, not a certified ocean vehicle controller. React + TypeScript, FastAPI, WebSocket, optional MQTT ingress, SQLite, Recharts, Leaflet, and an STM32 firmware sample.


## Version 1.1 — Marine-department interface update

### World navigation and coordinates
- Referenced world map with OpenStreetMap tiles; optional Esri/GEBCO/NOAA ocean bathymetry.
- Locally bundled, public-domain Natural Earth reference coastline remains visible if online tiles fail. It is **not** a nautical chart.
- WGS84 decimal coordinates to six places, signed values, DMS format, N/S/E/W hemispheres, course, speed in m/s and knots, satellite count and reported fix accuracy.
- Latitude/longitude grid, inspect-at-cursor coordinates, World and Locate controls, metric map scale, last valid fix and timestamped track table.
- Antimeridian segments are split; invalid points are omitted. Web Mercator cannot represent positions above ±85.0511°; these coordinates remain displayed numerically without a misleading clamped marker.
- Display precision is not GNSS accuracy. Demo positions are still clearly labeled simulated.

### Accurate, explicitly zoned time
- `/api/time` provides server UTC; the UI estimates server/browser clock offset using the request midpoint and resynchronizes every minute.
- Top-bar clock displays the **date and time**, with UTC, IST (Asia/Kolkata) and browser-local zone options. All stored telemetry and report windows remain UTC.
- Server-clock status is **not an NTP-lock claim**. Correct absolute time requires the deployment host clock to be disciplined by NTP or GNSS. The browser falls back to its local clock with a visible label if synchronization fails.

### Recording every seven seconds
- Backend uses monotonic deadlines at a fixed **7.0-second** cadence; processing time is not cumulatively added to the period.
- Mission state and fault injection do not change that recording cadence. Paused acquisition and unavailable hardware are gaps, never fabricated samples.
- HTTP/MQTT ingress validates and queues the latest external frame. The scheduler records the most recent fresh frame on the next seven-second slot. Faster external frames are coalesced; they are not all archived. Without a fresh frame, nothing is synthesized or duplicated.
- HTTP acceptance means **queued**, not yet recorded. Frame timestamps retain sensor/gateway sample time; `received_at` in the processed envelope is the backend processing/record time.
- STM32 source and rebuilt binaries now use a 7,000 ms cycle. Physical scheduling still needs runtime verification on Wokwi/real hardware.
- The low-rate motion spectrum has a Nyquist limit near **0.071 Hz**. An 8-second ocean wave cannot be resolved from this 7-second stream without aliasing; use an independent high-rate IMU buffer for validated wave processing.

### Day, Dark Ocean and Night Watch
Use the top-bar theme switch. Themes and timezone persist in browser local storage. Day mode uses white surfaces and marine teal; Dark Ocean uses deep navy; Night Watch uses subdued warm, low-glare colors.

### Automatic ten-day ocean-condition bulletins
Open **Ocean Reports**. The first automatic bulletin is due exactly **240 hours after the reporting schedule is first initialized**, followed by fixed ten-day UTC windows. `report_schedule` and `reports` are persisted in SQLite.

Aggregation runs in a background worker with its own SQLite WAL connection, rather than blocking the seven-second acquisition loop.

The backend scheduler delivers bulletins to the **dashboard inbox** (the selected delivery destination), with ocean and atmospheric ranges/averages, valid sample counts, source provenance, unavailable-channel counts, mission/ice-state counts and last navigation position. JSON/CSV downloads are available. No email, webhook or real satellite report delivery is implied.

A clearly marked **Generate preview** creates a partial-window report without changing the automatic due date. Empty windows produce an explicit no-data bulletin. After downtime, the scheduler catches up once per completed window, without duplicate scheduled reports. The backend must be running to deliver on time; it checks due windows approximately every 30 seconds.

New routes:
- `GET /api/time`
- `GET /api/reports` — inbox and next delivery schedule
- `POST /api/reports/preview` — labeled, partial-window digest
- `GET /api/reports/{id}`
- `POST /api/reports/{id}/read`
- `GET /api/reports/{id}/download?format=csv|json`

Tests added: schedule persistence, idempotent restart catch-up, aggregation/provenance, exact window boundaries, preview/read behavior. Chromium verified all 14 views, three themes, timezone persistence, report generation/download and mobile overflow. Measured live recording intervals: **6.999, 7.001, 6.999 seconds** in the smoke test. This is ordinary OS scheduling, not a hard-real-time guarantee.

---

## What is working, and what is simulated?

| Component | Implementation / boundary |
|---|---|
| Dashboard | All 14 pages (including Ocean Reports), live WebSocket stream, telemetry-driven map, charts, fault controls, CSV and historical data |
| Backend | Validation, missing/invalid quality flags, EMA filtering, motion FFT, autonomous state logic, prototype ice score, durable SQLite logging |
| Demo platform | **SIMULATED HARDWARE**: Python models the controller cycle. **SIMULATED SENSORS**: all environmental and navigation readings |
| STM32 firmware | Compilable modular Arduino-framework C++ for **STM32F103C8 Blue Pill**. Analog potentiometers control modeled temperature and battery; other sensors are software models |
| Wokwi | Project configuration and UART-to-HTTP/MQTT bridge supplied. **No authenticated Wokwi simulation was run in this workspace; wiring and serial capture need verification in your Wokwi environment.** Selecting Wokwi does not fabricate a connection |
| Real hardware | **NOT CONNECTED / NOT VERIFIED**. Sensor drivers, calibration, EMC, pressure qualification and hardware-in-loop tests remain |
| Satellite | Persistent pending queue and recovery demonstrated against a **simulated satellite sink**, not an Iridium modem or real satellite network |
| Local storage | SQLite on backend is durable. Firmware has a two-slot **volatile RAM journal**, not an SD/FRAM driver |
| Buoyancy | Requested software actions shown; no physical pump, valve or motor actuation |
| Low power | Software sample scheduling changes. Hardware STOP/STANDBY and actual power savings are not implemented |
| Ice forecast | **Unvalidated deterministic decision-support heuristic**. Not an operational ice forecast |

## 1. Quick start

Python 3.11+ and Node.js 20+ recommended. Run commands from project root unless indicated.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cp .env.example .env
# Edit .env; choose a private INGEST_TOKEN before using external ingress.
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

Open **http://localhost:5173**. The hosted workspace exposes this as **Neela Yaan Mission Control** in the live preview. FastAPI docs: `http://localhost:8000/docs`.

Demo sampling starts automatically at fixed seven-second intervals. The **Pause mission / Start mission** control is real and affects backend acquisition. Start re-runs INITIALIZATION → DEPLOYED → condition-driven state. Reset also clears faults without deleting history.

Browser code uses same-origin `/api` and `/ws`; Vite proxies these to the backend. The browser never attempts to reach a sandbox-local backend address. In deployment put both behind a TLS reverse proxy; preserve WebSocket Upgrade headers.

## 2. Architecture

```text
SIMULATED PHYSICAL PLATFORM / future real sensors
                  ↓
STM32 firmware → UART JSON → host bridge → MQTT or HTTP
                  ↓                              ↓
     DEMO Python sensor source ───────────→ single ingestion function
                                                 ↓
Pydantic schema → acquisition timestamp → validation / quality
                                                 ↓
EMA processing + IMU spectrum → ice heuristic → mission state machine
                                                 ↓
SQLite samples + events + pending queue → simulated satellite sink
                                                 ↓
WebSocket /ws → React dashboard (history via REST)
```

The dashboard does not own any mission state calculation. Fault buttons issue REST commands, causing subsequent **backend samples** to change. In Wokwi mode the dashboard does not override external sensor frames with demo faults.

The initial sensor generation logic is in `backend/simulator.py`; it is never represented as measured ocean truth. Temperature, salinity, oxygen and atmosphere include small Gaussian noise. A periodic motion model drives IMU data. The simulated GNSS track uses a spherical forward-geodesic calculation at 0.74 m/s, not a calibrated drift model. Navigation distance is calculated from valid fixes using the Haversine formula within the loaded history.

### Code layout

```text
backend/
  main.py                  lifecycle, routes, unified ingress, simulator task
  telemetry_models.py      centralized input contract
  data_processor.py        bounds, quality flags, EMA, motion FFT
  mission_manager.py       priority-based autonomous states
  ice_algorithm.py         prototype environmental score
  storage.py               SQLite WAL persistence and event journal
  communication_manager.py durable queue + emulated satellite delivery
  mqtt_client.py           optional authenticated/TLS MQTT subscriber
  websocket_manager.py     broadcasts, slow/disconnected client handling
  simulator.py             modeled physical measurements
frontend/src/
  types.ts                 generated sensor interfaces + processed envelope
  main.tsx                 scientific views, stream lifecycle, operator controls
  style.css                responsive mission-control design
firmware/
  src/main.cpp             embedded acquisition loop
  include/                 ten modular firmware components
  platformio.ini           verified compile target
  diagram.json             Wokwi board and two sensor-model potentiometers
  wokwi.toml               local firmware/ELF references
  artifacts/               compiled firmware copy for convenience
bridge/
  uart_bridge.py           actively appended UART file or real serial → ingress
  example-packet.json      sample only; replace timestamp before ingress
scripts/generate_schema.py regenerate JSON schema and frontend sensor interfaces
tests/test_pipeline.py     validation, state, persistence and buffering tests
```

## 3. Telemetry contract

`backend/telemetry_models.py` is the canonical contract; `telemetry.schema.json` is generated from it. `frontend/src/types.ts` centralizes frontend fields; presentation metadata lives in one dictionary in `main.tsx`.

```bash
python scripts/generate_schema.py
```

Each frame contains a timezone-aware ISO 8601 `timestamp` and nested `ocean`, `atmosphere`, `navigation`, `imu`, `waves`, `power`, `communication` objects; optional input `mission` is preserved in the validated input but backend state is recalculated, not trusted.

Units: water temperature °C, conductivity mS/cm, salinity PSU, pressure dbar, depth m, DO mg/L, speed/current m/s, pressure hPa, humidity %, wind direction/heading degrees, acceleration m/s², angular velocity rad/s, wave height m, period s, frequency Hz, battery %, voltage V, solar/load W. Latitude/longitude are signed decimal degrees WGS84.

Numeric fields may be omitted or null (MISSING). Values outside per-channel physical bounds are stored as null with INVALID quality. Non-finite JSON numbers and unknown fields reject the frame. EMA filtering is applied only to valid ocean/atmospheric channels; large steps receive WARNING. Raw fields are retained. The frontend does not interpolate across invalid samples.

Ingress rejects samples more than 30 seconds away from server UTC and duplicate/out-of-order frames for the current source. Sync the host clock. The gateway timestamps UART frames **at gateway receipt**, not at the instant of embedded acquisition: there is no RTC driver in this sample. A production protocol needs sequence IDs, boot IDs, calibrated device timestamps and quality provenance.

Derived envelope adds `id`, `source`, `received_at`, `quality`, `raw`, `mission`, `ice`, `motion`, `pipeline`, and communication counters.

## 4. Create the Wokwi STM32 project

Use **VS Code + PlatformIO + Wokwi extension** with the local `firmware/` directory. Wokwi CLI/VS Code access may require your own license or token; none is bundled.

1. Install PlatformIO (`pip install platformio`) and the Wokwi extension.
2. Open `firmware/` as the VS Code project folder.
3. Build the firmware:

   ```bash
   pio run
   ```

4. `wokwi.toml` references `.pio/build/bluepill_f103c8/firmware.bin` and `.elf`.
5. Open `diagram.json`, invoke **Wokwi: Start Simulator**, and inspect the UART console at **115200 baud**.
6. Check the Blue Pill pin names against your installed board definition. The supplied wiring intends:

   | Signal | STM32 pin |
   |---|---|
   | Temperature-model potentiometer SIG | PA0 / A0 |
   | Battery-model potentiometer SIG | PA1 / A1 |
   | Potentiometer VCC / GND | 3.3 V / GND |
   | UART TX → serial monitor RX | PA9 (USART1 TX) |
   | UART RX ← serial monitor TX | PA10 (USART1 RX) |

7. Temperature mapping is `-2 + 40 × ADC/4095` °C. Battery mapping is `100 × ADC/4095` %. Changing these potentiometers changes serialized fields, not frontend text.
8. CTD chemistry, DO, IMU, GNSS, waves, atmospheric conditions and power load are **software sensor models**. They are not claimed as real Wokwi CTD/DO parts.

The sample uses Arduino STM32 core, not generated STM32Cube HAL/RTOS project files. It demonstrates module boundaries and a scheduling loop. Full sensor drivers, embedded persistence and all production fault states still need porting and verification.

## 5. How Wokwi reaches the backend

**An STM32 Blue Pill has no built-in network connection. A Wokwi UART console does not automatically publish MQTT. The host bridge is required.**

Supported bridge inputs:
- A live-growing UART log from a Wokwi CLI session.
- A physical serial port from a real STM32/USB-UART adapter.

For CLI users, install Wokwi CLI following its official instructions, supply your own `WOKWI_CLI_TOKEN`, and use its serial-log option:

```bash
# Terminal A, from firmware/ (verify option availability with wokwi-cli --help):
wokwi-cli --serial-log-file uart.log .

# Terminal B, from project root, after uart.log exists:
python bridge/uart_bridge.py --follow firmware/uart.log --backend http://localhost:8000
```

The bridge starts at **end-of-file** and forwards only newly appended complete JSON lines. Do not feed it an archived logfile and call it live telemetry. If your Wokwi version only exposes an interactive UART console, it must first be connected to a continuously streamed serial-log transport; copy/paste is not real-time integration.

From **Mission Control → Telemetry source**, choose **Wokwi / STM32 interface**, then Start if paused. The backend stops generating demo readings and waits. Until actual frames arrive, the UI shows awaiting telemetry/stale rather than pretending the connection works.

### HTTP transport

Configure `INGEST_TOKEN` in `.env`, then restart the backend. The bridge reads it from the same `.env` when launched from project root.

```http
POST /api/telemetry
Content-Type: application/json
X-Ingest-Token: <your private token>

{ "timestamp": "<current timezone-aware UTC>", "ocean": { ... }, ... }
```

Responses: 200 accepted; 401 unauthorized; 422 structural validation failure; 409 wrong selected source, paused mission, stale timestamp or out-of-order sample. Source is assigned by ingress, never blindly accepted from a JSON field. This is provenance labeling, not cryptographic proof of physical hardware origin.

For actual STM32 serial on Linux:

```bash
pip install pyserial
python bridge/uart_bridge.py --serial /dev/ttyACM0 --baud 115200 --backend http://localhost:8000
```

Choose the real device path on your machine. For external hosts replace the backend URL with the reachable HTTPS API host, not the sandbox's localhost. The current UI labels this ingress WOKWI/STM32; certify and extend provenance to REAL before claiming real measurements.

### MQTT transport

Run your own Mosquitto-compatible broker. Example `.env`:

```dotenv
MQTT_HOST=your-broker-host
MQTT_PORT=8883
MQTT_USERNAME=your-user
MQTT_PASSWORD=your-private-password
MQTT_TLS=true
MQTT_TOPIC=neela/telemetry
TELEMETRY_SOURCE=WOKWI
```

Restart the backend after changing broker configuration. `mqtt_client.py` subscribes to the configured topic. The bridge publishes the identical JSON contract with QoS 1:

```bash
python bridge/uart_bridge.py --follow firmware/uart.log --mqtt
```

Do not use retained telemetry as a live source. A stale retained frame is rejected by the timestamp gate. MQTT uses broker credentials/ACLs, not the HTTP token. Use TLS with certificate verification. The bridge reports failures but does not durably retry ingress; production needs a separate upstream spool and backpressure. Accepted frames are queued for the next seven-second recording slot.

**MQTT adapter is implemented but was not tested against a provisioned external broker in this delivery. Wokwi execution was not verified.**

## 6. Verify the actual live data path

1. In Demo, confirm **DEMO SIMULATOR / SIMULATED SENSOR DATA**. `WS LIVE` describes the transport only.
2. Switch to Wokwi. Demo generation must stop, and old source data must be marked stale.
3. Start your simulator and live UART bridge. Check successful ingress logs.
4. Turn PA0 potentiometer. Inspect UART JSON, then `GET /api/latest`, then the ocean-temperature card and chart. Values are filtered so a step settles across several samples.
5. Turn PA1 below 20%. Once initialization completes, verify LOW_POWER. The recording interval remains seven seconds.
6. Stop simulator or bridge. Within 15 seconds **DATA STALE** appears even if the WebSocket itself is still connected.
7. Restart backend: WebSocket reconnects automatically; historical rows persist. In Wokwi mode old rows are not fresh arrivals.

WebSocket clients send `ping` every three seconds; backend returns a heartbeat with health metadata. Network close triggers 2.5-second reconnect attempts. Values are based on packet age and source match, not on a green socket alone.

## 7. Final demonstration sequence

Use **Demo Simulator** for the fully self-contained walkthrough:

1. Mission Control → Reset mission. Observe INITIALIZATION → DEPLOYED → NORMAL_OPERATION over successive samples.
2. Mission Timeline shows acquisition, validation, processing, GPS, ice evaluation, mission evaluation, SQLite store and emulated transmit events.
3. **Simulate high ice risk** sets modeled cold water/air. Allow several samples for EMA settling. Risk becomes HIGH and state ICE_WARNING; recording remains at seven seconds.
4. **Simulate satellite failure**. Acquisition, processing and storage continue. Pending packets increase. If ice is still high, mission state remains ICE_WARNING because it has higher priority; the satellite panel independently shows OFFLINE.
5. **Restore satellite**. Pending SQLite packets drain to the **simulated sink** on the next cycle.
6. Clear the ice fault or Reset mission. Return to nominal operation without deleting logs.
7. Test GPS failure, sensor failure and low battery separately. All commands alter the backend, not UI-only variables.
8. Refresh the browser. Data Explorer history and transmission events remain available.
9. Pause acquisition for >15 seconds to demonstrate stale-data handling.

### Autonomous state priorities

After INITIALIZATION / DEPLOYED:

1. EMERGENCY: battery <5%.
2. SAFE_MODE: more than 12 missing/invalid numeric channels.
3. ICE_AVOIDANCE: critical ice risk.
4. ICE_WARNING: high ice risk.
5. LOW_POWER: battery <20%.
6. SENSOR_FAULT: missing/invalid temperature, salinity or pressure.
7. GPS_LOSS: no fix.
8. COMMUNICATION_LOSS: simulated satellite offline.
9. NORMAL_OPERATION otherwise.

All simultaneous faults remain visible even when only the highest-priority state is selected. Recording cadence is fixed at 7 seconds in all mission states. Safety actions are displayed intents, not executed buoyancy commands.

### Ice algorithm and wave limits

Risk is a sum of explicit contributions: water 5–35; air 0–25; salinity 5–10; latitude 5–15; waves 0–10; depth 0–5. LOW 0–30, MODERATE 31–60, HIGH 61–80, CRITICAL 81–100. Missing required inputs → UNKNOWN. No trained model, trend inference, satellite imagery or scientific calibration is used.

RMS and the Hann-window FFT derive from received vertical acceleration. A minimum of 8 valid samples is required. The FFT assumes approximately uniform sampling, and changing power schedules or gaps undermines spectral interpretation. Telemetry-provided wave height/period/frequency are modeled inputs, not reconstructed from this low-rate stream. Production should use high-rate buffered IMU data, attitude compensation and validated spectral processing.

## 8. APIs

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | source, acquisition, MQTT and storage state |
| GET | `/api/latest` | most recent processed frame |
| GET | `/api/ocean`, `/api/atmosphere`, `/api/navigation`, `/api/waves`, `/api/power`, `/api/mission`, `/api/ice` | latest subsystem data |
| GET | `/api/history?limit=600&since=<ISO>` | chronological persisted rows; max 10,000 per request |
| GET | `/api/events` | latest 200 stored events |
| GET | `/api/export?parameter=ocean.temperature&since=<ISO>&limit=100000` | CSV; numeric values, quality, source and state |
| POST | `/api/telemetry` | authenticated HTTP ingress |
| POST | `/api/control/{action}` | demo/operator commands |
| WS | `/ws` | telemetry envelopes + recent events + heartbeat |

Actions: `start`, `pause`, `reset`, `DEMO`, `WOKWI`, `fail_gps`, `restore_gps`, `fail_satellite`, `restore_satellite`, `fail_battery`, `restore_battery`, `fail_sensor`, `restore_sensor`, `fail_ice`, `restore_ice`.

SQLite stores complete processed/raw frames, event timestamps and a persistent `sent` flag. Browser initially loads the last 1,800 frames. Data Explorer range queries load up to 10,000; CSV caps at 100,000. These are prototype limits, not unlimited archive queries. The live view keeps a bounded history. For large missions add pagination, indexes, retention and archival jobs.

## 9. Tests and validation record

```bash
python -m unittest discover -s tests -v
pip install httpx
python tests/test_api.py
cd frontend && npx tsc --noEmit
# Optional browser smoke test, with both servers running:
npm install --no-save @playwright/test
npx playwright install --with-deps chromium
node check-marine.mjs
# Firmware build, from root:
pio run -d firmware
```

Verified in this workspace:
- 16 unit tests covering normal/high/critical ice, low battery, emergency/safe mode, GPS/satellite loss, invalid/missing/nonfinite values, restart-safe storage and queue draining.
- HTTP/WebSocket integration test passed: authenticated ingress, heartbeat, duplicate rejection, source isolation, subsystem APIs, export and pause.
- TypeScript type check passed.
- Chromium navigated all 14 pages with no page exceptions and confirmed `WS LIVE`.
- Browser-driven high-ice injection → ICE_WARNING; satellite failure increased pending packets; restoration drained them to zero; history survived refresh.
- STM32F103C8 firmware compiled successfully (PlatformIO ST STM32 core).

Not verified: Wokwi runtime/wiring, external MQTT broker, physical sensors/modem, hardware power modes, under-ice safety, long-duration reliability, multi-vehicle operation.

## 10. Deployment and safety boundaries

This is a **single-process, single-platform lab prototype**. Run one Uvicorn worker: each process otherwise creates an independent demo controller. Health labels infer channel availability rather than reading actual device heartbeats. Pipeline timestamps represent backend execution, not STM32 profiler measurements. Firmware state and backend state are not command-synchronized.

Operator controls, history and WebSocket are intentionally accessible for the SIH demo; **they are not protected by production user authentication**. Do not expose this prototype to an untrusted network. Before deployment add identity/RBAC, CSRF/origin policy, command signatures, MQTT topic ACLs, rate/size limits, TLS, schema versioning, immutable audit IDs and fail-safe actuator interlocks. Never put secrets in frontend code or commit `.env`.

OpenStreetMap tiles and optional web fonts need internet access. If tiles fail, the map retains a coordinate grid and telemetry trajectory with a warning. Offline field deployment should use a licensed, locally hosted map source. Do not use this interface for operational navigation or collision/ice avoidance.
