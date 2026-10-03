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
5. Click **RUN OPTIMISATION**. It takes roughly 15–60 seconds, depending on the file size.

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

The tool expects **30-minute interval meter data**, like a standard TNB export.
It detects the layout automatically and handles all four competition files:

- A header row anywhere in the first 5 rows containing words like `Date`, `End Time`, `kW Import` or `Timestamp`. Title rows above it (e.g. `Solar Installed | 944.880 kWp`) are skipped.
- A timestamp column (`Date / End Time`, `start_time`, `end_time`, `timestamp`, …).
- A **kW Import** column (required) and a **kW Export** column (optional; used when solar already exists).
- Headerless files with 4–6 columns in TNB order.

Minimal CSV example:

```csv
timestamp,kW Import,kW Export
2026-01-01 00:30:00,46.2,0
2026-01-01 01:00:00,44.3,0
```

Notes:
- **Building load = kW Import − kW Export.** If the building already has solar, that solar is already reflected in the meter readings. Any PV the tool recommends is **additional** solar on top.
- Timestamps labelled "end time" are shifted to the start of each interval, so the 13:30–14:00 reading counts as off-peak and 21:30–22:00 as peak.
- Gaps are filled by interpolation, and rows are sorted, so files in reverse date order are fine.
- An existing PV size is read from the file name or title (e.g. `... 944.880 kWp ...`), but it is only shown as information.

---

## How it works

```
 meter data ──► 1. Load & clean ──► 2. Forecast ──► 3. Size PV + battery ──► 4. Optimise dispatch ──► 5. Bill & savings
                                                                                     │
                                                                          (optional) 6. EV charging schedule
```

1. **Load & clean** (`load_universal`). Reads any of the supported formats and produces a clean 30-minute series.
2. **Forecast** (`QuantileForecaster`). Three gradient-boosted models predict the 10th, 50th and 90th percentile load (P10/P50/P90) from time-of-day, day-of-week and recent-history features. P90 is a "cautious high" estimate and is used for risk-aware planning.
3. **Size** (`npv_auto_size`, `evaluate_design`). Tries 24 combinations of PV size (0–1.4× peak load), battery power (25–65% of peak) and battery duration (2 or 3 hours). It simulates each one and keeps the design with the highest 20-year NPV. Costs come from the specified equipment:
   - **PV:** Trina Vertex N 610 W panels
   - **Inverter:** Sigen Hybrid 12.0 TP2 (12 kW each, run in parallel)
   - **Battery:** SigenStor 5 kWh modules (max 6 per inverter)

   Panels, inverters and modules are rounded up to whole units, then BOS (+20% of panels), installation (+10%) and EMS software (RM 25k) are added.
4. **Optimise dispatch** (`solve_dispatch_lp`, `monthly_dispatch`). For each calendar month, a linear program decides the battery charge/discharge for every half-hour. It minimises *energy cost + MD charge*, subject to battery limits (20–95% state of charge, 90% round-trip efficiency). Because TNB bills MD monthly, solving a whole month at once gives the best schedule for that month, not just a good guess. It uses SciPy's HiGHS solver, so no extra solver install is needed.
5. **Bill** (`monthly_bill`, `compare_bills`). Calculates the RP4 bill **per calendar month** (each month has its own MD) and reports the **average month**. "Baseline" is the building as it is today. "Optimised" includes the new PV and battery.
6. **EV layer** (`run_ev_layer`, `schedule_ev_lp`). Generates realistic EV charging sessions (arrival time, departure time, kWh needed). A linear program then schedules each car's charging inside its parking window and pushes it out of peak hours where possible. EV energy is reported separately and is **not** added to the building bill.

---

## Outputs

### Command line

Files are written to the output folder:

| File | Contents |
|---|---|
| `summary.json` | Everything in one place: building stats, tariff, chosen design, forecast stats, savings (RM figures are **per average month**), EV results |
| `backtest.csv` | Half-hourly simulation on the historical data: `load_kw`, `solar_kw`, `grid_kw` (optimised), `baseline_grid_kw`, `bess_kw` (+ discharge / − charge), `soc_pct`, `is_peak` |
| `forecast_dispatch.csv` | Same columns, for the next 30 days using the P90 forecast |
| `sizing_scan.csv` | All 24 designs tested, ranked by NPV (auto-sizing only) |
| `ev_schedule.csv` | Total EV charging kW per half-hour (EV mode only) |

### Dashboard

- **Key results:** MD reduction, demand/energy/total monthly savings, annual saving.
- **Recommended system:** PV, battery, CAPEX, payback, and the equipment count (panels, inverters, battery modules).
- **Tabs:**
  - *Dispatch & SOC:* power flows and battery charge over 3–14 days, with peak hours shaded.
  - *Load Forecast:* 14-day P10/P50/P90 forecast.
  - *Bill Breakdown:* each bill component before and after, plus a savings waterfall.
  - *ROI Analysis:* 20-year NPV curve and cost breakdown.
  - *EV Load Shifting:* share of EV energy charged off-peak.

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
