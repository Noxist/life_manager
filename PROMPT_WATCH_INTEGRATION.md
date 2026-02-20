# Copilot Prompt — WaterTracker Watch: API Integration + Curve Fixes

> Paste this entire file as context when working on the **WaterTracker**
> HarmonyOS app (Huawei Watch Ultimate 2, HarmonyOS 5).
>
> **Do NOT modify** the bio-dashboard server code — only the watch app.

---

## Overview

The WaterTracker watch app already has HR/sleep monitoring implemented
(`HealthMonitorService.ets`, `ServerService.pushHealth()`, Settings toggles).
This prompt fixes **three display bugs** in the hydration curve panel and
documents the **complete server API** for reference.

---

## Part 1: Bugs to Fix in IndexPage.ets

### Bug A — Header shows expected-at-hour instead of daily goal

**File:** `entry/src/main/ets/pages/IndexPage.ets`
**Location:** `hydrationCurvePanel()` builder (around line 640–655)

**Current (wrong):**
```typescript
Row() {
  Text(`${this.curveData.current_ml}`)
    .fontSize(11)
    .fontWeight(FontWeight.Bold)
    .fontColor(Constants.COLOR_PRIMARY)
  Text(` / ${this.curveData.current_expected_ml} ml`)
    .fontSize(9)
    .fontColor(Constants.COLOR_TEXT_SECONDARY)
}
```

Shows `1000 / 2294 ml` — 2294 is the expected intake at the current hour,
**not** the daily goal (3733). Users read this as progress towards goal.

**Fix:**
```typescript
// Primary: actual / daily goal
Row() {
  Text(`${this.curveData.current_ml}`)
    .fontSize(11)
    .fontWeight(FontWeight.Bold)
    .fontColor(Constants.COLOR_PRIMARY)
  Text(` / ${this.curveData.goal_ml} ml`)
    .fontSize(9)
    .fontColor(Constants.COLOR_TEXT_SECONDARY)
}
.justifyContent(FlexAlign.Center)
.margin({ bottom: 1 })

// Secondary: expected at current time (colored by status)
Text(`Erwartet jetzt: ${this.curveData.current_expected_ml} ml`)
  .fontSize(7)
  .fontColor(this.curveData.current_ml >= this.curveData.current_expected_ml
    ? '#34C759'   // on track
    : '#FF9F0A')  // behind
  .margin({ bottom: 2 })
```

---

### Bug B — Actual intake is a flat horizontal line (should be step function)

**Location:** `drawHydrationCurve()` — "Actual intake" section (approx lines 570–590)

**Current (wrong):**
```typescript
// Fill area under actual intake
ctx.fillStyle = 'rgba(79, 195, 247, 0.2)';
ctx.beginPath();
ctx.moveTo(hourToX(wakeH), baseY);
ctx.lineTo(curX, baseY);
ctx.lineTo(curX, mlToY(curMl));
ctx.lineTo(hourToX(wakeH), mlToY(curMl));
ctx.closePath();
ctx.fill();

// Actual intake line (solid primary)
ctx.strokeStyle = Constants.COLOR_PRIMARY;
ctx.lineWidth = 2;
ctx.beginPath();
ctx.moveTo(hourToX(wakeH), mlToY(curMl));
ctx.lineTo(curX, mlToY(curMl));
ctx.stroke();
```

This draws a flat line at the current total, implying the user drank
everything at wake-up. It should show a **step function** that jumps
at each drink event.

**Fix:**

1. Add a state variable for today's entries:
```typescript
@State private todayEntries: WaterEntry[] = [];
```

2. Populate it in `loadMainData()`, `addWater()`, and `undoLast()`:
```typescript
this.todayEntries = log.entries;
```

3. Replace the flat-line drawing with a step function:

```typescript
// ── Actual intake as step function ──
const serverBase: number = this.currentIntake - (this.todayEntries.length > 0
  ? this.todayEntries.reduce((sum: number, e: WaterEntry) => sum + e.amount, 0)
  : 0);

interface StepPoint { hour: number; ml: number; }
const steps: StepPoint[] = [];
steps.push({ hour: wakeH, ml: serverBase });

let runningMl: number = serverBase;
for (let i = 0; i < this.todayEntries.length; i++) {
  const entryDate: Date = new Date(this.todayEntries[i].timestamp);
  const entryHour: number = entryDate.getHours() + entryDate.getMinutes() / 60;
  // Horizontal to this entry's time at previous level
  steps.push({ hour: entryHour, ml: runningMl });
  // Vertical step up
  runningMl += this.todayEntries[i].amount;
  steps.push({ hour: entryHour, ml: runningMl });
}
// Extend to current time
steps.push({ hour: curHour, ml: runningMl });

// Fill area under step function
ctx.fillStyle = 'rgba(79, 195, 247, 0.18)';
ctx.beginPath();
ctx.moveTo(hourToX(steps[0].hour), baseY);
for (let i = 0; i < steps.length; i++) {
  ctx.lineTo(hourToX(steps[i].hour), mlToY(steps[i].ml));
}
ctx.lineTo(hourToX(steps[steps.length - 1].hour), baseY);
ctx.closePath();
ctx.fill();

// Step function outline
ctx.strokeStyle = Constants.COLOR_PRIMARY;
ctx.lineWidth = 2;
ctx.setLineDash([]);
ctx.beginPath();
ctx.moveTo(hourToX(steps[0].hour), mlToY(steps[0].ml));
for (let i = 1; i < steps.length; i++) {
  ctx.lineTo(hourToX(steps[i].hour), mlToY(steps[i].ml));
}
ctx.stroke();
```

---

### Bug C — Local fallback curve is linear (should be front-loaded)

**Location:** `generateLocalCurve()` and `checkPacing()` in IndexPage.ets

The server now uses `t^0.85` (front-loaded): morning hours get ~55% of the
goal in the first 50% of waking time. But the watch's local fallback still
uses linear `t^1.0`. When the server is unreachable the watch shows the
wrong curve shape.

**Fix:** Add a helper and use it in both places:

```typescript
private getExpectedProgress(hour: number, wakeH: number, sleepH: number): number {
  if (hour <= wakeH) return 0;
  if (hour >= sleepH) return 1;
  const t: number = (hour - wakeH) / (sleepH - wakeH);
  return Math.pow(t, 0.85);  // front-loaded: steeper morning, gentler evening
}
```

Replace in `generateLocalCurve()`:
```typescript
// OLD: const progress = elapsed / waking_total;
// NEW:
const progress: number = this.getExpectedProgress(currentHour, wakeH, sleepH);
```

And in the curve points loop:
```typescript
// OLD: const p = (hr - wakeH) / (sleepH - wakeH);
// NEW:
const p: number = this.getExpectedProgress(hr, wakeH, sleepH);
```

And in `checkPacing()`:
```typescript
// OLD: const progress = (currentHour - wakeH) / (sleepH - wakeH);
// NEW:
const progress: number = this.getExpectedProgress(currentHour, wakeH, sleepH);
```

---

## Part 2: Complete Server API Reference

**Base URL:** `https://bioapi.thegrandprinterofmemesandunfinitetodosservanttonox.tech`
**Auth:** Header `x-api-key: bio_leandro_2026_secret`
(or `Authorization: Bearer bio_leandro_2026_secret`)

### 2.1 Water Endpoints

#### POST /api/water/report — Report water intake (returns instruction inline)

```json
// Request:
{ "current_intake": 1500, "daily_goal": 3733 }

// Response:
{
  "status": "ok",
  "instruction": {
    "message": "Du bist im Rückstand (800 ml). Trink jetzt 300 ml.",
    "recommended_amount": 300,
    "priority": "high",
    "deadline_minutes": 30,
    "daily_target_override": 0,
    "timestamp": "2026-02-20T14:30:00",
    "velocity_warning": null,
    "events_today": 5,
    "hydration_curve": {
      "current_ml": 1500,
      "goal_ml": 3733,
      "current_hour": 14.5,
      "current_expected_ml": 2100,
      "wake_hour": 7.0,
      "sleep_hour": 23.0,
      "targets": [
        { "minutes": 15, "target_ml": 2150, "delta_ml": 650, "label": "15'" },
        { "minutes": 30, "target_ml": 2200, "delta_ml": 700, "label": "30'" },
        { "minutes": 45, "target_ml": 2250, "delta_ml": 750, "label": "45'" },
        { "minutes": 60, "target_ml": 2300, "delta_ml": 800, "label": "1h" }
      ],
      "expected_curve": [
        { "hour": 7.0, "ml": 0 },
        { "hour": 7.5, "ml": 180 },
        ...
        { "hour": 23.0, "ml": 3733 }
      ]
    },
    "adaptive_curve": {
      "adaptive_curve": [...],
      "ideal_curve": [...],
      "catch_up_rate_ml_h": 220,
      "deficit_ml": 600,
      "remaining_ml": 2233,
      "remaining_hours": 8.5,
      "status": "behind",
      "achievable_ml": 3600,
      "adaptive_targets": [...]
    }
  }
}
```

**Key:** The `expected_curve` uses a **front-loaded** model (`t^0.85`),
not linear. Morning hours are steeper. The watch should render this
dashed line directly from the server data.

If `daily_target_override > 0`, the watch should update its local goal.

If `velocity_warning` is not null (e.g. `"Langsamer trinken — max 800 ml/h"`),
the watch should show it briefly.

#### GET /api/water/instruction — Same instruction (without reporting intake)

```
GET /api/water/instruction?current_intake=1500&daily_goal=3733
```
Returns the same instruction shape as the `instruction` field above.

#### DELETE /api/water/intake/last — Undo last water entry

```
DELETE /api/water/intake/last
// Response: { "status": "ok", "deleted_event": {...}, "new_total_ml": 1300 }
```

### 2.2 Health Endpoints

#### POST /api/health — Push HR/sleep/steps from the watch

```json
{
  "heart_rate": 72.0,       // optional
  "resting_hr": 58.0,       // optional
  "hrv": 42.0,              // optional
  "sleep_duration": 7.5,    // optional (hours)
  "sleep_confidence": 0.85, // optional (0.0–1.0)
  "spo2": 97.0,             // optional
  "respiratory_rate": 16.0, // optional
  "steps": 4200,            // optional
  "calories": 320.0,        // optional
  "source": "watch",        // MUST be "watch" for watch pushes
  "timestamp": "2026-02-20T08:30:00"  // optional
}
// Response: { "id": 42, "status": "ok" }
```

All fields optional. Send only what you collected.
Use `heart_rate: 0` for test pings from the Settings test button.

#### GET /api/health?today=true — Get today's health snapshots

```
GET /api/health?today=true
GET /api/health?today=true&source=watch    ← NEW: filter by source
GET /api/health?start=2026-02-20T00:00:00&end=2026-02-20T23:59:59
```

Returns `[{ id, timestamp, heart_rate, resting_hr, hrv, sleep_duration, ..., source }, ...]`

#### GET /api/health/latest — Most recent snapshot

Returns `{ found: true, heart_rate, resting_hr, ..., source, timestamp }`

#### GET /api/status — Server health check

Returns `{ status: "ok", ... }`. Use for `testConnection()`.

### 2.3 Weight Endpoint

#### GET /api/weight/latest — Current weight

Returns `{ found: true, weight_kg: 93.8, source: "google_fit", timestamp: "..." }`

### 2.4 Bio-Score

#### GET /api/bio-score — Composite health score (0–100)

Returns score computed from HR, HRV, sleep, hydration. Watch doesn't
need to call this directly.

---

## Part 3: HA Sensors Reference

The bio-dashboard server polls these Home Assistant sensors every 15 min.
The watch does **not** talk to HA directly — it pushes to the bio-dashboard
API, which stores data alongside HA imports.

| Sensor Entity ID | What it provides |
|---|---|
| `sensor.pixel_9_pro_xl_heart_rate_2` | HR from Google Fit (via HealthSync) |
| `sensor.pixel_9_pro_xl_resting_heart_rate_2` | Resting HR |
| `sensor.pixel_9_pro_xl_heart_rate_variability_2` | HRV (ms) |
| `sensor.pixel_9_pro_xl_sleep_duration_2` | Sleep duration |
| `sensor.pixel_9_pro_xl_oxygen_saturation_2` | SpO2 % |
| `sensor.pixel_9_pro_xl_respiratory_rate_2` | Respiratory rate |
| `sensor.pixel_9_pro_xl_daily_steps_2` | Daily step count |
| `sensor.pixel_9_pro_xl_active_calories_burned_2` | Active kcal |
| `sensor.pixel_9_pro_xl_weight_2` | Weight (grams → auto-converted to kg) |
| `input_boolean.sleepmode` | Sleep mode toggle |
| `input_boolean.inbed` | In-bed toggle |
| `sensor.water_tracker_daily` | Water from HA (not from watch) |

**Where to find these in HA:**
- Open your HA instance → Developer Tools → States
- Filter by `pixel_9_pro_xl` to see all Google Fit sensors
- Or navigate to Settings → Devices → search "Pixel 9 Pro XL"

The watch HR data will appear on the **bio-dashboard web app** under
"Vitals & Health" as a separate **cyan line** (labeled "HR (Watch)")
next to the red HA line ("HR (HA)"). The dashboard differentiates by
the `source` field in the health snapshot.

---

## Part 4: What NOT to Change

- Server code (`water_engine.py`, `routes.py`, `streamlit_app.py`) — already updated
- `HealthMonitorService.ets` — HR/sleep logic is correct
- `ServerService.ets` — push/test methods are correct
- `SettingsPage.ets` — toggles work correctly
- `EntryAbility.ets` — lifecycle hooks are correct
- `module.json5` — permissions are correct

---

## Part 5: Visual Result After Fixes

**Header:**
```
     1000 / 3733 ml          ← goal (not expected-at-hour)
   Erwartet jetzt: 2305 ml   ← green if ahead, orange if behind
```

**Canvas:**
```
ml ▲
   │            ╭─── expected (dashed, curved t^0.85)
   │      ┌─── actual (step function, solid blue)
   │      │  ╭╌╌╌╌╌╌╌╌
   │    ┌─┘╌╌╌
   │  ┌─┘
   │──┘
   └──────────────────▶ hour
   7    10   13   16   19  23
```

**Dashboard (Vitals & Health):**
```
  HR: 72 bpm | Ruhe-HR: 58 bpm | HRV: 42 ms | Schlaf: 7.5h
  Aktualisiert: 14:30 | Quelle: Huawei Watch

  [HR chart with two lines: red=HA, cyan=Watch]
  [Resting HR comparison chart if both sources present]
```

---

## Part 6: Testing Checklist

- [ ] Header shows `current_ml / goal_ml` (not current_expected_ml)
- [ ] "Erwartet jetzt" line is green when on track, orange when behind
- [ ] Actual intake renders as step function with jumps at each drink event
- [ ] Local fallback curve uses `t^0.85` (visibly curved, not straight)
- [ ] Server curve (when online) renders correctly as dashed line
- [ ] `serverBase` offset works: steps start at server-known base level
- [ ] No entries → step function sits at serverBase, no jumps
- [ ] HR toggle on → data appears on dashboard under "HR (Watch)" within 15 min
- [ ] `GET /api/health?today=true&source=watch` returns watch snapshots
