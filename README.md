# Energy Monitoring System (RExharge RP4 EMS)

An energy-management tool for Malaysian commercial and industrial buildings on
the **TNB RP4 non-domestic tariff** (effective 1 July 2025).

You give it a building's electricity meter data. It tells you:

- **What the building's load will look like** over the next few weeks (a forecast with a low, typical and high case).
- **What size of solar panels and battery to buy**, chosen to give the best 20-year return.
- **How to run that battery** every 30 minutes to cut the electricity bill.
- **How much money that saves**: monthly bill, payback period and 20-year NPV.
- *(Optional)* **How to schedule EV charging** so most of it happens outside peak hours.

It was built for the RExharge Case Study Competition (Theme 1: *Load Shifting & Peak Shaving*).

---

## Why this matters: how a TNB RP4 bill works

Under RP4, a medium-voltage commercial building pays mainly for two things:

| Charge | What it's based on | Rate (MV Commercial) |
|---|---|---|
| **Maximum Demand (MD)** | The **single highest** half-hour power draw (kW) during peak hours in the month | RM 30.19 capacity + RM 66.87 network = **RM 97.06 per kW** |
| **Energy** | Total kWh used | Peak: RM 0.3852/kWh · Off-peak: RM 0.2237/kWh |
| AFA | Total kWh used | RM 0.0145/kWh |

**Peak hours** are weekdays 14:00–22:00, excluding public holidays. Everything else is off-peak.

Because the MD charge comes from one half-hour of the month, reducing that one
worst spike saves money for the whole month. The system saves money in two ways:

1. **Peak shaving.** The battery discharges during spikes, so the grid never sees the full peak and the MD charge falls.
2. **Load shifting.** Energy is moved from expensive peak hours to cheap off-peak hours: the battery charges off-peak, and EV charging is delayed until off-peak.

Three tariff classes are built in (see `RP4_RATES` in [backend.py](backend.py)):
`MV_COMMERCIAL_TOU` (default), `MV_INDUSTRIAL_E2` and `LV_NON_DOMESTIC_TOU` (no MD charge).

---

## Repository contents

| File | What it is |
|---|---|
| [backend.py](backend.py) | The engine: data loading, forecasting, optimisation, sizing and billing. Can be run on its own from the command line. |
| [dashboard_FINAL.py](dashboard_FINAL.py) | An interactive web dashboard (Streamlit) built on top of `backend.py`. Upload a file, click run, explore the charts. |
| [requirements.txt](requirements.txt) | Python packages needed. |

---

## Quick start

### 1. Install

You need **Python 3.10 or newer**.

```bash
git clone <this-repo-url>
cd energy-monitoring-system
python -m pip install -r requirements.txt
```

### 2a. Run the dashboard (easiest)

```bash
python -m streamlit run dashboard_FINAL.py
```

(`python dashboard_FINAL.py` also works and starts Streamlit for you.)

Your browser opens at `http://localhost:8501`. Then:

1. Upload a load-profile file (`.xlsx`, `.xls` or `.csv`) in the left sidebar.
2. Pick the tariff class.
3. Leave **Auto-size by 20-yr NPV** on, or switch it off to type your own PV/battery sizes.
4. *(Optional)* Set the number of AC/DC EV chargers.
5. Click **RUN OPTIMISATION**. It takes roughly 15–60 seconds for 1–2 months of data, or about 2 minutes for a full year.

If you change a setting afterwards, click **Run** again to refresh the results.

### 2b. Run from the command line

```bash
python backend.py --input "path/to/Load Profile.xlsx"
```

Put the path in quotes if it contains spaces. Other examples:

```bash
# Different tariff + an EV hub with 4 AC and 2 DC chargers
python backend.py --input "E.xlsx" --rate-class MV_INDUSTRIAL_E2 --ev-ac 4 --ev-dc 2

# Skip auto-sizing and test your own design (500 kWp PV, 300 kW / 600 kWh battery)
python backend.py --input "Mi2.xlsx" --pv-kwp 500 --bess-kw 300 --bess-kwh 600

# Choose where results are saved
python backend.py --input "SuN.xlsx" --output ./results
```

| Option | Meaning | Default |
|---|---|---|
| `--input` | Load-profile file (required) | — |
| `--rate-class` | `MV_COMMERCIAL_TOU`, `MV_INDUSTRIAL_E2` or `LV_NON_DOMESTIC_TOU` | `MV_COMMERCIAL_TOU` |
| `--output` | Folder for results | `~/Downloads/rexharge_out` |
| `--ev-ac` / `--ev-dc` | Number of 22 kW AC / 60 kW DC EV chargers to simulate | 0 / 0 |
| `--pv-kwp`, `--bess-kw`, `--bess-kwh` | Manual sizing of **new** PV and battery. Giving any one skips auto-sizing; the others default to 0. | auto |

**IDE mode:** running `python backend.py` with no arguments uses the
`FILE_PATH`, `RATE_CLASS` and `EV_CHARGERS_*` settings at the top of
[backend.py](backend.py). Edit those first.

Example console output:

```
Loading 3. Load Profile (No Solar) SuN.xlsx ...
  → 2,832 intervals  peak=308 kW  LF=35.1%  solar=False
[2] Probabilistic forecast (P10/P50/P90)...
[3] NPV-maximising auto-sizing ...
  → PV 431 kWp + BESS 200 kW / 400 kWh
  → CAPEX RM 2,115,330  payback 6.0 yr  NPV20 RM 1,705,836
[4] MILP monthly-horizon dispatch on historical data ...
  → avg monthly MD: 292 → 116 kW  (176 kW saved)
  → saving: RM 32,053 per month  (63.4%)
...
✓ Done.
```

---

## Input data format

The tool expects **30-minute interval meter data**, like a standard TNB export
(`.xlsx`, `.xls` or `.csv`). It figures out the layout by itself:

- **Header row.** The loader looks for the first row whose first cell is a date. The row just above it is treated as the header, and any title rows above that (e.g. `Device`, `Meter Type`, `Solar Installed | 944.880 kWp`) are ignored. A file with no header row at all is also accepted if it has 4–6 columns in standard TNB order.
- **Timestamp.** Taken from the first column, or from a column named `start_time`, `timestamp`, `datetime` or `end_time`.
- **Load column.** Any column with **`Import`** in its name (kVAR columns are ignored). If there is none, the loader uses a column named `Load`, `Load_kW`, `kW`, `Demand`, `Demand_kW`, `Power` or `Power_kW`.
- **Several meters in one file.** If there are several `kW Import` / `kW Export` columns (e.g. a main meter plus a solar meter), they are all added together:
  **building load = Σ all kW Import − Σ all kW Export.**
- **Several sheets in one file** (e.g. one sheet per month). Every sheet is read and joined in date order. Sheets without dated rows are skipped, and duplicate timestamps are dropped.

Any of these minimal files will work:

```csv
Date&Time,Load
2026/1/1 00:00,426.88
2026/1/1 00:30,422.48
```

```csv
Date / End Time,kW Export,kW Import
2026-01-01 00:30:00,0,46.2
2026-01-01 01:00:00,0,44.3
```

Notes:
- **Existing solar is already in the data.** Because load is import minus export, any solar the building already has is reflected in the readings. PV recommended by the tool is **additional** solar on top.
- **"End time" stamps are shifted.** TNB stamps each reading with the time the half-hour *ends*. When the timestamp column name contains "end", it is moved back 30 minutes so each row is labelled with the interval's *start*. This puts 13:30–14:00 in off-peak and 21:30–22:00 in peak, as RP4 intends. Columns like `Date&Time` or `start_time` are assumed to be start times already.
- **Gaps are filled.** Empty cells, `-` cells, and missing half-hours are filled by straight-line interpolation. If one meter in a multi-meter file is missing a value, that whole row is filled in, so the gap doesn't show up as a sudden drop in load. Files in reverse date order are fine.
- **Existing PV size is display-only.** It is read from the file name or title (e.g. `944.880 kWp`) and shown in the dashboard, but not used in any calculation.
- **If loading fails,** the error message lists the column names it found, so you can rename a column to one of the accepted names.

---

## How the backend works

[backend.py](backend.py) is a pipeline of six steps. The dashboard calls the same functions, so this section describes both.

```
 meter file
     │
     ▼
 1. Load & clean ─────────► 30-min series of building load (kW)
     │
     ├──► 2. Forecast ────► P10 / P50 / P90 load for the next 14–30 days
     │
     ├──► 3. Size ────────► tries 24 PV + battery designs ──► picks best 20-yr NPV
     │         │                    │
     │         │            each design is simulated with step 4
     │         ▼
     ├──► 4. Dispatch (LP) ► battery charge/discharge plan, every half-hour
     │
     ├──► 5. Bill ────────► RP4 bill before vs after, per average month
     │
     └──► 6. EV layer ────► (optional) when to charge each EV
```

### Step 1. Load & clean (`load_universal`)

The loader reads the file as described above. It then resamples the data to an
exact 30-minute grid, fills gaps, and computes summary statistics:
peak load, mean load, 95th-percentile load, **load factor** (mean ÷ peak; low
means "spiky", which is where peak shaving pays off most) and whether solar is
present.

### Step 2. Probabilistic load forecast (`QuantileForecaster`)

**Goal:** estimate what the load will look like in the coming weeks, including how much it might vary.

**Model.** Three **gradient-boosted regression** models (scikit-learn
`GradientBoostingRegressor` with quantile loss), one each for the 10th, 50th
and 90th percentile:

| Output | Meaning |
|---|---|
| **P10** | A low day: the load should be above this ~90% of the time |
| **P50** | The typical (median) value |
| **P90** | A high day: the load should exceed this only ~10% of the time |

**Features** used to predict each half-hour:

| Group | Features |
|---|---|
| Calendar | hour, day-of-week, month, weekend flag, peak-window flag |
| Cyclic | sin/cos of hour and day-of-week, so 23:30 is treated as close to 00:00 |
| Lags | load 30 min ago, 1 day ago (48 steps), 1 week ago (336 steps) |
| Rolling stats | mean of the last 3 h and 24 h; 10th and 90th percentile of the last 24 h |

**Forecasting ahead (recursive).** The model needs the previous half-hour's
load as an input, so it forecasts one step at a time and feeds each prediction
back in as the input for the next step. Each quantile keeps its **own** history,
so the P90 path is built from earlier P90 values (a consistently high
scenario) rather than mixing scenarios. Predictions are clipped to a sensible
range and sorted so that P10 ≤ P50 ≤ P90 at every step.

**How it's used.** The CLI forecasts 30 days and the dashboard 14 days. The
**P90** path is used for the "forward" battery plan (step 4), so the plan is
built for a high-load month rather than an average one.

### Step 3. Sizing PV + battery by NPV (`npv_auto_size`, `evaluate_design`)

**Goal:** choose how much new solar (kWp) and battery (kW power, kWh energy) to buy.

**Designs tested.** A grid of 4 × 3 × 2 = **24 designs**, scaled to the
building's peak load *P*:

| Choice | Options |
|---|---|
| New PV | 0, 0.5 *P*, 1.0 *P*, 1.4 *P* kWp |
| Battery power | 0.25 *P*, 0.45 *P*, 0.65 *P* kW |
| Battery duration | 2 h or 3 h (kWh = kW × hours) |

**For each design:**

1. Simulate a year's operation using the LP in step 4 on the historical data. Annual saving = (baseline monthly bill − optimised monthly bill) × 12.
2. **Convert to real hardware** (`size_equipment`), rounding **up** to whole units:
   - panels = ⌈kWp ÷ 0.61⌉ (Trina Vertex N 610 W)
   - inverters = the largest of three requirements: ⌈battery kW ÷ 12⌉, ⌈PV kWp ÷ 24⌉ and ⌈battery modules ÷ 6⌉ (Sigen Hybrid 12.0 TP2: 12 kW AC, 24 kW PV input and at most 6 battery modules each)
   - battery modules = ⌈kWh ÷ 5⌉ (SigenStor 5 kWh)
3. **CAPEX** = panels + inverters + batteries + BOS (20% of panel cost) + installation (10% of equipment) + EMS software (RM 25k).
4. **20-year NPV** at a 6% discount rate:

   ```
   net saving / yr = annual saving − O&M (1.5% of CAPEX)
   NPV = −CAPEX + Σ(year 1..20) net saving / 1.06^year
               − (60% of battery cost) / 1.06^12        ← battery replacement in year 12
   ```

The design with the **highest NPV** wins. The full ranking is saved to
`sizing_scan.csv`. If you enter your own sizes (`--pv-kwp …` or the
dashboard's manual mode), only that one design goes through the same
calculation.

**Solar output model** (`solar_profile`). There's no weather data, so each day
uses the same bell-shaped curve tuned for the Klang Valley:

- production between 06:54 and 19:12, peaking at 12:42
- a steeper afternoon side, because afternoons in the Klang Valley tend to be cloudier
- scaled by kWp × **0.886 derate**: 0.942 temperature loss × 0.95 soiling/wiring × 0.99 inverter efficiency

### Step 4. Optimal battery dispatch: the LP (`solve_dispatch_lp`, `monthly_dispatch`)

This is the core of the system. It decides, for every half-hour, how much the
battery should charge or discharge to make the electricity bill as low as
possible.

**Why "optimisation" instead of simple rules?** A rule like "discharge when
load > 80% of peak" doesn't know what's coming later in the month. It can
empty the battery early and miss the real monthly peak, or keep it full on a
day that didn't need it. The MD charge depends on the **single highest
half-hour of the month**, so the best decisions depend on the whole month at
once. A **linear program (LP)** looks at the whole month together and finds
the provably cheapest schedule.

> **LP vs MILP.** The code and dashboard call this "MILP" (Mixed-Integer
> Linear Programming). Strictly, it is a plain **LP**: there are no
> integer/yes-no variables. A MILP would add yes/no variables to forbid
> charging and discharging at the same moment. That isn't needed here,
> because doing both at once only wastes energy (round-trip losses), so the
> cheapest solution never does it. Plain LPs solve much faster and still
> give the global optimum.

**One LP per calendar month.** TNB resets MD every month, so each month is
solved separately. The battery's end-of-month charge is carried over as the
next month's starting charge (the first month starts at 50%).

**Decision variables** for each half-hour *t* in the month (H ≈ 1,440 slots):

| Variable | Meaning | Limits |
|---|---|---|
| `c[t]` | battery charging power (kW) | 0 … battery kW |
| `d[t]` | battery discharging power (kW) | 0 … battery kW |
| `g[t]` | power drawn from the grid (kW) | ≥ 0 (no export credit) |
| `soc[t]` | energy stored in the battery (kWh) | 20% … 95% of battery kWh |
| `curt[t]` | surplus solar thrown away (kW) | 0 … surplus available |
| `M` | the month's maximum demand during peak hours (kW) | ≥ 0 (one value per month) |

**Objective.** Minimise the month's bill:

```
minimise   Σ_t  price[t] × g[t] × 0.5h          ← energy cost (peak or off-peak rate)
         + (capacity + network rate) × M       ← MD charge (RM 97.06/kW for MV commercial)
         + 0.0001 × Σ_t curt[t]                ← tiny penalty: avoid wasting solar for no reason
```

**Constraints:**

1. **Power balance** (every half-hour). Grid + battery discharge must cover the load that solar doesn't:
   `g[t] + d[t] − c[t] − curt[t] = load[t] − solar[t]`
2. **Battery energy** (every half-hour). Stored energy changes by what goes in minus what comes out, after losses:
   `soc[t] = soc[t−1] + 0.5h × (η × c[t] − d[t] / η)`, where η = √0.90 ≈ 0.949 (90% round-trip efficiency, split equally between charging and discharging).
3. **Maximum demand** (peak half-hours only). `g[t] ≤ M`.
   Because `M` is multiplied by RM 97/kW in the objective, the solver pushes `M` as low as it can. That forces the battery to "shave" every peak-hour spike down to the same flat ceiling. Off-peak half-hours have no MD charge under RP4 for MV customers, so they aren't constrained.

**Behaviour this produces:**
- **Peak shaving:** the battery discharges during the month's biggest peak-hour spikes so that `M` falls.
- **Arbitrage / load shifting:** the battery charges on off-peak power (RM 0.22/kWh) and discharges in peak hours (RM 0.39/kWh), as long as the price gap beats the 10% round-trip loss.
- **Solar self-use:** surplus midday solar charges the battery instead of being wasted.

**Solver.** SciPy's `linprog` with the **HiGHS** solver, included with SciPy.
The constraint matrices are stored in sparse form, since almost all entries
are zero. Each monthly LP has about 7,000 variables and solves in well under a
second.

**Baseline vs optimised.** For every half-hour the output contains
`baseline_grid_kw` (what the building draws today: load, floored at 0) and
`grid_kw` (what it would draw with the new PV and battery).

> The LP has **perfect foresight**: it knows the whole month's load in
> advance. On historical data this gives the *maximum achievable* saving.
> A real controller would follow it using the forecast from step 2. That's why
> step 4 is also run on the P90 forecast (`forecast_dispatch.csv`), giving a
> cautious forward plan.

### Step 5. RP4 bill (`monthly_bill`, `compare_bills`)

1. Each half-hour is tagged **peak** (weekdays 14:00–22:00, excluding Malaysian public holidays in `MY_HOLIDAYS`) or **off-peak**.
2. For **each calendar month**, MD = the highest grid draw in a peak half-hour.
3. Bill components:
   - **Demand** = MD × (capacity + network rate)
   - **Energy** = peak kWh × peak rate + off-peak kWh × off-peak rate
   - **AFA** = all kWh × AFA rate
   - plus a retail charge for LV customers
4. The bill is reported as the **average month**. Partial months count by how much of the month is covered (e.g. 15 days of June counts as 0.5 month), so a few extra days of data don't distort the result.

`compare_bills` runs this for baseline and optimised, and returns the
difference: MD reduction (kW), demand saving, energy saving, total saving (RM
per month) and saving %.

### Step 6. EV load-shifting layer (`run_ev_layer`, `schedule_ev_lp`)

Optional. Simulates an EV charging hub at the building and schedules
charging to avoid peak hours.

**1. Sessions** (`synth_ev_sessions`). With no real charger logs available,
realistic sessions are generated, about **one per charger per day**:

| Charger | Arrival | Parked for | Energy needed | Max power |
|---|---|---|---|---|
| AC | around 10:00 (07:30–16:00) | 2.5–5 h | 15–50 kWh | 22 kW |
| DC fast | around 14:00 (08:00–21:00) | 0.4–1.2 h | 15–45 kWh | 60 kW |

**2. Scheduling LP.** Solved one week at a time:

- **Variables:** energy delivered to car *j* in half-hour *t*, which can only be non-zero while that car is parked, plus a peak level `M`.
- **Objective:** minimise Σ energy × (peak or off-peak price) + MD rate × `M`.
- **Constraints:**
  - every car receives its full requested energy (or as much as is physically possible while it's parked)
  - in peak hours, building grid draw + EV charging ≤ `M`
  - at all times, building + EV ≤ 1.2 × the building's historical peak (site connection limit)

So the LP pushes charging before 14:00 or into the parked hours after 22:00,
and fills in around the building's own peaks when charging has to happen in
the peak window. The headline result is the **share of EV energy charged
off-peak** (typically 85–97%).

EV energy is reported separately and is **not** added to the building's bill
or to the battery dispatch.

---

## How the dashboard works

[dashboard_FINAL.py](dashboard_FINAL.py) is a [Streamlit](https://streamlit.io)
web app. It contains no optimisation logic of its own: it calls the backend
functions above and draws the results with Plotly.

**Run flow:**

1. **Start.** Running `python dashboard_FINAL.py` automatically relaunches itself as `streamlit run dashboard_FINAL.py`.
2. **Sidebar inputs:** file upload, tariff class, auto-size on/off (or manual PV kWp / battery kW / battery kWh), and the number of AC and DC EV chargers.
3. **RUN OPTIMISATION.** The uploaded file is saved to a temporary file and steps 1–6 run with a progress bar:
   load → forecast (14 days) → sizing → monthly LP dispatch → bills → EV LP.
4. **Caching.** Results are stored in `st.session_state` together with the settings that produced them. Moving a chart slider or switching tabs does **not** re-run the optimisation. If you change a sidebar setting, a warning says the results are out of date until you click **RUN** again.

**What each part of the page shows:**

| Section | Content | Where the numbers come from |
|---|---|---|
| Building banner | Name, peak and mean load, load factor, date range, existing solar | Step 1 |
| **Key Results** | MD reduction (kW and %), demand saving, energy saving, total saving per month, annual saving (= monthly × 12) | Step 5 |
| **Recommended System Design** | PV kWp, battery kW/kWh and duration, CAPEX, payback and NPV | Step 3 |
| **Equipment Specification** | Number of panels (and roof area), inverters and battery modules; itemised CAPEX | `size_equipment` |
| Tab **Dispatch & SOC** | Top chart: load, solar, baseline vs optimised grid draw, and battery charge/discharge bars. Bottom chart: battery state of charge with the 20%/95% limits. Peak hours are shaded yellow. Below: daily peak MD, baseline vs optimised. You can view 3, 7 or 14 days. | Step 4 |
| Tab **Load Forecast** | 14-day P50 line with a P10–P90 band, plus summary stats | Step 2 |
| Tab **Bill Breakdown** | Each bill component before vs after, a waterfall of where the savings come from, and a table | Step 5 |
| Tab **ROI Analysis** | Cumulative discounted NPV over 20 years (with the year-12 battery replacement) vs simple payback; cost breakdown table | Steps 3 and 5, using `DEFAULT_CAPEX` |
| Tab **EV Load Shifting** | Sessions, kWh delivered, and an off-peak vs peak split chart | Step 6 |

**Typical run time:** 15–60 s for 1–2 months of data, and about 2 minutes for a full year.
Most of the time goes to forecasting and the 24 sizing simulations.

---

## Command-line outputs

`backend.py` writes these files to the output folder:

| File | Contents |
|---|---|
| `summary.json` | Everything in one place: building stats, tariff, chosen design, forecast stats, savings (RM figures are **per average month**), EV results |
| `backtest.csv` | Half-hourly simulation on the historical data: `load_kw`, `solar_kw`, `grid_kw` (optimised), `baseline_grid_kw`, `bess_chg_kw`, `bess_dis_kw`, `bess_kw` (+ discharge / − charge), `soc_kwh`, `soc_pct`, `is_peak` |
| `forecast_dispatch.csv` | Same columns, for the next 30 days using the P90 forecast |
| `sizing_scan.csv` | All 24 designs tested, ranked by NPV, with equipment counts and costs (auto-sizing only) |
| `ev_schedule.csv` | Total EV charging kW per half-hour (EV mode only) |

---

## Changing the assumptions

Everything is in plain dictionaries near the top of [backend.py](backend.py):

| What | Where |
|---|---|
| Tariff rates | `RP4_RATES` |
| Public holidays (treated as off-peak) | `MY_HOLIDAYS`. Holidays are listed for 2025–2026; add later years if your data extends beyond 2026. |
| Equipment specs and prices | `TRINA_PANEL`, `SIGEN_INVERTER`, `SIGENSTOR_BAT` |
| Financial assumptions (discount rate 6%, 20-yr life, O&M 1.5%/yr, battery replaced at year 12 at 60% of cost) | `DEFAULT_CAPEX` |
| Solar yield shape (no weather data; a typical Klang Valley clear-ish day curve with 88.6% derate) | `solar_profile` |

---

## Limitations

- **Solar is modelled, not measured.** Each day uses the same idealised curve, so cloudy days are not captured.
- **No export credit.** Surplus solar is assumed to be curtailed or exported for free.
- **The dispatch has perfect foresight within each month.** It shows the *best achievable* savings; a real controller running on forecasts will do somewhat worse.
- **Short data gives rough annual figures.** With 1–2 months of data, annual savings are that period's average month × 12.
- **Prices are estimates.** Equipment prices are turnkey estimates and should be replaced with real quotes.
- **EV sessions are synthetic,** generated from typical arrival patterns rather than real charger logs.
