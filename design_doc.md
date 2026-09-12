# Roast Profile Overlay — Design Document

## 1. Goal

Build a lightweight, local-only web application that lets a user choose one or more Artisan `.alog` roast profiles from disk and compare them in one interactive overlay chart.

The chart will support:

- Bean temperature (BT)
- Exhaust/environment temperature (ET)
- Bean-temperature rate of rise (RoR)
- Heater output
- Air/fan output
- Event pins for Charge, Turning Point, Dry End, First Crack Start, and Drop
- Checkboxes to independently show or hide each curve type and event pins
- A profile-selection table with one visibility checkbox per profile, green batch weight, combined final-weight/weight-loss value, Charge and Drop bean temperatures, and Drying, Browning, and Development phase breakdowns

## 2. Findings from `Roast Profiles/`

### 2.1 Collection

- The directory contains 34 `.alog` files and `.DS_Store`.
- Files are Artisan roast logs, primarily written by Artisan 4.0.2.
- All 34 files can be parsed as Python literals.
- Files are roughly 48–96 KB and contain approximately 342–853 samples each.
- Sampling is generally every 1.5 seconds.
- Temperature mode is Celsius in all inspected profiles (`mode: "C"`).
- Some filenames are explicitly marked `glitch`; one glitch profile has no Dry End, First Crack, or Drop event. Missing data must therefore be handled without failing the whole import.

### 2.2 Relevant `.alog` structure

The `.alog` format in this collection is a Python dictionary representation, not strict JSON. The relevant fields are:

| Purpose | `.alog` field | Notes |
|---|---|---|
| Profile name | `title` | Filename will be the fallback |
| Green/final batch weight | `weight` | `[green weight, final weight, unit]` |
| Units | `mode` | `C` in the supplied set |
| Main timestamps | `timex` | Seconds from recording start |
| Exhaust/environment temperature | `temp1` | Artisan ET channel |
| Bean temperature | `temp2` | Artisan BT channel |
| Event sample indices | `timeindex` | Artisan event index array |
| Computed event details | `computed` | Includes event times and BT/ET values |
| Extra-device timestamps | `extratimex[0]` | Heater/fan device timeline |
| Heater output | `extratemp1[0]` | 0–100% in these logs |
| Air/fan output | `extratemp2[0]` | 0–100% in these logs |
| Device declaration | `devices` | Includes `+Kaleido Heater/Fan` |

The `computed` dictionary provides:

- `CHARGE_BT`, `CHARGE_ET`
- `TP_time`, `TP_BT`, `TP_ET`
- `DRY_time`, `DRY_BT`, `DRY_ET`
- `FCs_time`, `FCs_BT`, `FCs_ET`
- `DROP_time`, `DROP_BT`, `DROP_ET`

Artisan's `timeindex` order in these files is Charge, Dry End, First Crack Start, First Crack End, Second Crack Start, Second Crack End, Drop, Cool. Turning Point is instead represented by `computed.TP_*`.

### 2.3 Time alignment

The recording can contain pre-charge and post-drop samples. For comparison, each profile will be normalized so that **Charge is time zero**:

- Main and extra-device timestamps: `display time = source time - charge time`
- Curves will be clipped to Charge through Drop when Drop exists.
- If Drop is missing, data will run from Charge to the end of the recording.

This makes roast milestones line up meaningfully across profiles while preserving differing roast durations.

## 3. User experience

### 3.1 Initial state

The page opens with:

- App title and a short purpose note: “Compare Artisan roast profiles on one chart, inspect roast milestones, and review phase timing.”
- A prominent **Choose `.alog` files** button/drop zone
- An empty-state chart area with brief instructions
- Curve visibility controls, initially enabled

The native file picker will allow multiple `.alog` files.

### 3.2 Loaded state and profile-selection table

After selection, each parsed profile appears as one row in a compact table. On narrow screens, the table remains horizontally scrollable rather than hiding temperature or phase data.

| Column | Content |
|---|---|
| Compare | Checkbox that enables/disables the entire profile in the chart without removing it |
| Profile | Derived from the source filename: remove `.alog`, replace underscores with spaces, and collapse repeated whitespace; the name itself uses the profile's assigned comparison color |
| Green weight | Green-bean batch weight and source unit, displayed to one decimal place |
| Final weight | Final roasted batch weight followed by weight-loss percentage in the format `<final weight> (-<weight loss>%)` |
| Charge temp | Bean temperature at Charge, displayed to one decimal place in °C |
| Drop temp | Bean temperature at Drop, displayed to one decimal place in °C |
| Drying | Phase duration as `mm:ss` and percentage of total roast time |
| Browning | Phase duration as `mm:ss` and percentage of total roast time |
| Development | Phase duration as `mm:ss` and percentage of total roast time |
| Actions | Remove profile button |

Example display name: `26-08-14_Baarbara_Washed_AAA_batch_5.alog` becomes `26-08-14 Baarbara Washed AAA batch 5`.

Example weight, temperature, and phase cells:

```text
Green weight  Final weight       Charge temp  Drop temp  Drying       Browning      Development
125.0 g       105.0 g (-16.0%)  207.6 °C     187.7 °C   03:49 · 41%  03:40 · 39%   01:50 · 20%
```

Green and final weights come from the Artisan roast log's structured `weight` field. Weight loss is derived from those values and appended in parentheses to the Final weight cell rather than shown in a separate column. Charge and Drop temperatures come from the normalized event BT values in the API response. If an event or its BT value is missing, its table cell displays an em dash (`—`). Drying is denoted with mid-tone green, Browning with mid-tone brown, and Development with dark brown in both the table headers and values.

Table behavior:

- Newly imported profiles are checked by default.
- Unchecking a row immediately removes all curves, pins, and tooltip entries for that profile while retaining the loaded data and phase summary.
- The header includes **Select all** and **Select none** actions for convenient multi-profile comparison.
- Additional files can be appended without clearing existing profiles.
- A **Clear all** action removes every profile.
- Duplicate files are detected by filename plus file size and are not added twice.
- Import errors appear per file and do not prevent valid files from loading.

### 3.3 Chart interaction

The chart will provide:

- Hover/crosshair tooltip showing elapsed `mm:ss` and values for visible profiles/curves near the cursor
- A fixed time range that automatically fits all enabled profiles
- Responsive resizing for desktop and tablet-sized screens
- A profile/curve legend that explains both color and line style

## 4. Visual design

### 4.1 Profile color encoding

Each profile receives a distinct color from a coordinated, muted palette built from primary and secondary hues: blue, terracotta red, green, purple, ochre, teal, berry, orange, indigo, olive, cyan-blue, and mauve. The colors are mid-toned for visibility against the warm off-white background while avoiding highly saturated combinations that cause visual dissonance. For selections beyond the base palette, lighter and darker variants are used to retain distinct profile identities. The UI will recommend comparing no more than 6–8 profiles at once for readability.

Color identifies the **profile**. Line treatment identifies the **measurement**:

| Measurement | Style |
|---|---|
| Bean temperature | Solid, strongest stroke |
| Exhaust temperature | Long dash |
| RoR | Short dash/dot |
| Heat | Stepped line |
| Air | Stepped dotted line |

This keeps all curves from one profile visually related while using a harmonious range of primary and secondary colors to distinguish profiles.

### 4.2 Axes

- Bottom: elapsed time from Charge, formatted `mm:ss`
- Left: temperature in the source unit (°C for the supplied profiles)
- Right: RoR in °C/min, fixed at 0 on the bottom and the maximum visible-profile RoR on the top
- Far left: heater/air control scale titled `AIR / HEAT %`; numeric tick labels omit repeated percent symbols

Subtle horizontal grid lines and restrained labels will keep a multi-profile chart readable. The chart uses approximately 68% of the available browser viewport height, capped at 760 px on larger screens and reduced responsively on narrow screens. This is taller than the initial version while preserving space for browser chrome and surrounding controls.

### 4.3 Event pins

Pins will be drawn at event time and BT value. Each pin uses the profile's assigned palette color and a stable abbreviation/shape:

- `CHG` — Charge
- `TP` — Turning Point
- `DE` — Dry End
- `FC` — First Crack Start
- `DROP` — Drop

Hovering a pin will show event name, elapsed time, BT, and ET. Missing events are simply omitted. Event labels will use basic collision avoidance (alternating vertical offsets) to reduce overlap.

### 4.4 Curve visibility controls

These controls are separate from the per-profile checkboxes in the selection table. A checkbox group above the chart will contain:

- Bean temp
- Exhaust temp
- RoR
- Heat
- Air
- Event pins

Changes apply immediately without reparsing files. At least one measurement may remain visible; event pins are independently optional.

## 5. Data processing

### 5.1 Safe parsing

The local Python server will parse uploads with `ast.literal_eval`, which supports the supplied Python-literal format without executing file contents. It will never use `eval`.

Validation will enforce:

- Top-level value must be a dictionary.
- `timex`, `temp1`, and `temp2` must be arrays.
- Required arrays must have usable numeric samples.
- Parallel arrays are clipped to their shortest valid length.
- Non-numeric and non-finite samples are discarded or represented as gaps.
- Uploads must have an `.alog` filename and remain below a conservative size limit (5 MB).

### 5.2 Normalized API result

The backend will return only fields needed by the browser. The table's profile label will deliberately be derived from `filename`, rather than the internal Artisan `title`, so its naming consistently follows the selected file.

```json
{
  "id": "client-generated-id",
  "filename": "profile.alog",
  "displayName": "profile",
  "title": "Internal Artisan roast title",
  "unit": "C",
  "weights": {
    "green": 125.0,
    "final": 105.0,
    "lossPercent": 16.0,
    "unit": "g"
  },
  "phases": {
    "total": 559.5,
    "drying": {"seconds": 229.5, "percent": 41.0},
    "browning": {"seconds": 220.5, "percent": 39.4},
    "development": {"seconds": 109.5, "percent": 19.6}
  },
  "series": {
    "bt": [[0.0, 194.4]],
    "et": [[0.0, 184.5]],
    "ror": [[0.0, null]],
    "heat": [[0.0, 75.0]],
    "air": [[0.0, 30.0]]
  },
  "events": [
    {"key": "charge", "time": 0.0, "bt": 194.4, "et": 184.5},
    {"key": "drop", "time": 559.5, "bt": 203.1, "et": 198.8}
  ],
  "warnings": []
}
```

The server will not retain uploads after responding.

### 5.3 Batch weight extraction and calculation

The structured Artisan `weight` value is interpreted as `[green weight, final roasted weight, unit]`. If a weight is absent there, `computed.weightin` and `computed.weightout` are used as fallbacks. Weight values retain their source unit and are displayed to one decimal place.

```text
weight loss percent = (green weight - final weight) / green weight × 100
```

The calculated percentage is used when both weights are valid. `computed.weight_loss` is the fallback when the percentage cannot be derived. Missing or invalid values display an em dash (`—`) without preventing the profile from loading.

### 5.4 Phase-time and percentage calculation

The phase table follows the standard three-phase roast model documented by Artisan: Drying ends at Dry End/yellow, Browning (also called the Maillard phase) runs from Dry End to First Crack Start, and Development runs from First Crack Start to Drop.

The values will be derived from event times, even though most supplied logs also contain `computed.dryphasetime`, `computed.midphasetime`, and `computed.finishphasetime`. Deriving the values gives consistent behavior and satisfies future logs that omit Artisan's computed summary.

With Charge normalized to time zero:

```text
total roast time = Drop - Charge
Drying time      = Dry End - Charge
Browning time    = First Crack Start - Dry End
Development time = Drop - First Crack Start
phase percent    = phase time / total roast time × 100
```

Percentages will be displayed to the nearest whole percent in the compact table; normalized API values retain one decimal place. Durations will be formatted as `mm:ss`. The three percentages may visually total 99% or 101% due to independent display rounding.

A phase cell displays an em dash (`—`) if either boundary needed for that phase is missing or invalid. Percentages are omitted if Drop is missing because total roast time cannot be established reliably. The profile still remains selectable and chartable.

References used for the phase definitions and calculation:

- [Artisan documentation — Roast Phases](https://artisan-scope.org/docs/phases/)
- [Artisan — Development Time Ratio](https://artisan-roasterscope.blogspot.com/2020/05/displaying-development-time-ratio-in.html)

The percentages are descriptive measurements, not quality targets; the app will not mark any percentage as good or bad.

### 5.5 RoR calculation

The files do not serialize the full RoR curve, so BT RoR will be derived from `temp2`.

To avoid amplifying sensor noise, each point will use a local least-squares slope over an approximately 30-second centered window:

- slope unit is converted from °C/second to °C/minute
- windows with insufficient samples become gaps
- no extrapolation beyond available data

The window will be a named constant and documented in code so it can be tuned later. This produces a more useful comparison than a noisy point-to-point derivative.

The RoR axis starts at 0 and ends at the highest non-negative RoR value across all enabled profiles. The range is recalculated when profiles are enabled, disabled, added, or removed. Negative RoR samples fall outside the displayed RoR scale.

### 5.6 Heater and air extraction

For this dataset, the first extra device is declared as `+Kaleido Heater/Fan`:

- Heater: `extratemp1[0]`
- Air/fan: `extratemp2[0]`
- Time: `extratimex[0]`

The parser will first identify an extra device whose device label contains `Heater/Fan` (case-insensitive), then fall back to index 0 for compatibility with these logs. If no valid channel exists, that profile will load with a warning and without the missing curves.

### 5.7 Mixed temperature units

The supplied set is entirely Celsius. If a future selection mixes Celsius and Fahrenheit profiles, the backend will normalize Fahrenheit profiles to Celsius and include an import warning. The chart will therefore never combine incompatible temperature scales.

## 6. Technical architecture

### 6.1 Stack

To keep the app lightweight and easy to run:

- **Backend:** Python 3 standard library only
- **Frontend:** semantic HTML, modern vanilla JavaScript, and CSS
- **Chart:** custom HTML Canvas renderer with a small DOM overlay for controls/tooltips
- **Dependencies:** none
- **Network binding:** `127.0.0.1` only

No framework, package manager, database, cloud service, or CDN is required.

### 6.2 Proposed files

```text
prophile/
├── design_doc.md
├── server.py
├── roast_parser.py
├── static/
│   ├── index.html
│   ├── app.js
│   ├── chart.js
│   └── styles.css
├── tests/
│   └── test_roast_parser.py
└── README.md
```

Responsibilities:

- `server.py`: localhost static server and `POST /api/parse`
- `roast_parser.py`: safe `.alog` parsing, normalization, events, and RoR
- `app.js`: file selection, state, profile table, controls, and API calls
- `chart.js`: canvas drawing, axes, line styles, pins, hover, and automatic range fitting
- `styles.css`: responsive visual system
- `test_roast_parser.py`: parser and normalization tests using real/synthetic fixtures
- `README.md`: prerequisites, startup command, usage instructions, feature summary, supported `.alog` fields, and test command

### 6.3 Local API

`POST /api/parse`

- Request body: raw `.alog` text
- Filename: URL-encoded `X-Filename` header
- Response: normalized JSON profile
- Errors: structured JSON with a user-safe message

Raw request bodies keep the server implementation smaller than multipart parsing. The browser will read each selected file and upload it independently, allowing one bad file to fail without affecting the rest.

### 6.4 Running

Planned command:

```bash
python3 server.py
```

The terminal will print the local URL, expected to be:

```text
http://127.0.0.1:8000
```

An optional `--port` argument will resolve port conflicts.

## 7. Accessibility and responsiveness

- Every checkbox and action has a visible label and keyboard focus state.
- File selection works without drag-and-drop.
- Colors are not the only encoding: filenames, line styles, and event labels remain present.
- Controls wrap cleanly on narrow screens.
- Canvas receives an accessible text summary listing loaded profiles and visible metrics.
- Reduced-motion preferences will be respected; the chart does not require animation.

## 8. Error handling

The UI will distinguish:

- Unsupported extension
- File too large
- Invalid or malformed `.alog`
- Missing main temperature arrays
- Missing optional heater/air channel
- Missing roast milestones
- Duplicate selection
- Server/network failure

Warnings are non-blocking when a useful partial profile can still be charted.

## 9. Testing and acceptance criteria

### 9.1 Automated parser tests

Using Python's built-in `unittest`:

- Parse a representative supplied `.alog`.
- Correctly map `temp1` to ET and `temp2` to BT.
- Correctly map the Kaleido heater/fan extra device.
- Align Charge to `00:00`.
- Extract green and final batch weights and calculate weight-loss percentage.
- Return Charge and Drop bean temperatures from normalized event data.
- Calculate Drying, Browning, and Development durations and percentages from event boundaries.
- Return unavailable phase values safely when an event boundary is missing.
- Clip ordinary profiles at Drop.
- Retain usable data when Drop or other events are absent.
- Generate finite, plausible RoR values from a known linear fixture.
- Reject executable/malformed input safely.
- Handle mismatched array lengths and missing optional channels.

### 9.2 End-to-end acceptance

The implementation is complete when:

1. `python3 server.py` starts the app with no dependency installation.
2. The initial screen clearly explains that the app compares Artisan profiles, milestones, and phase timing.
3. A user can select multiple supplied `.alog` files in one picker action.
4. Every valid file appears in the profile-selection table with a filename-derived display name.
5. Each profile shows green weight and a combined Final weight value formatted as `<final weight> (-<weight loss>%)`, or an em dash when unavailable.
6. Each profile shows Charge and Drop bean temperatures to one decimal place in °C, or an em dash when unavailable.
7. Each complete profile shows Drying, Browning, and Development time plus percentage; incomplete profiles show clear unavailable values.
8. A profile row's checkbox enables/disables all chart content for that profile without deleting it.
9. All checked profiles appear together in the overlay chart.
10. Profile identity is represented by a coordinated, muted primary/secondary color palette.
11. Drying, Browning, and Development table columns use mid-tone green, mid-tone brown, and dark brown respectively.
12. BT, ET, RoR, heat, and air have distinct line treatments.
13. The RoR axis runs from 0 at the bottom to the maximum RoR across all enabled profiles.
14. The far-left axis is titled `AIR / HEAT %`, and its numeric ticks do not repeat the percent symbol.
15. The chart is taller while remaining responsive and bounded relative to the browser viewport.
16. Each curve category can be shown or hidden with a checkbox.
17. Charge, TP, Dry End, First Crack, and Drop pins show where available.
18. Hover values, automatic chart fitting, remove-profile, and clear-all work.
19. A glitch/missing-event file does not crash or prevent other files loading.
20. No upload is persisted and the server only listens on localhost.
21. `README.md` documents how to start, use, and test the application.

## 10. Deliberate non-goals for the first version

- Editing or writing `.alog` files
- Saving comparisons between browser sessions
- Exporting chart images or CSV
- Cloud sync or remote access
- Reproducing every Artisan calculation or annotation
- User-configurable RoR smoothing
- Comparing metadata beyond what is shown in chart tooltips

These can be added later without changing the normalized profile model.

## 11. Implementation order after approval

1. Build and test the safe parser/normalizer.
2. Implement the localhost server and static file delivery.
3. Build file selection, profile state, the selection/temperature/phase table, errors, and visibility controls.
4. Implement chart scales and BT/ET rendering.
5. Add RoR and stepped heat/air series.
6. Add event pins, tooltip, legend, and automatic range fitting.
7. Apply responsive/accessibility styling.
8. Run automated tests and manually verify representative normal and glitch profiles.
9. Write concise run/use instructions in `README.md`.
