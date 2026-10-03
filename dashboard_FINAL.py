"""
Train to PJ — RExharge-RP4 EMS Dashboard
Run: streamlit run dashboard_FINAL.py  OR  python dashboard_FINAL.py
"""
# ── Auto-relaunch guard ───────────────────────────────────────────────────────
import sys, subprocess, os
_in_st = "streamlit" in sys.modules or "STREAMLIT_SERVER_PORT" in os.environ
if not _in_st and __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__] + sys.argv[1:])
    sys.exit(0)
# ─────────────────────────────────────────────────────────────────────────────

try:
    import streamlit as st
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ModuleNotFoundError as e:
    pkg = str(e).split("'")[1] if "'" in str(e) else str(e)
    print(f"\n  Missing: {pkg}\n"
          f"  Fix:  python -m pip install -r requirements.txt\n"
          f"  Then: python -m streamlit run dashboard_FINAL.py\n")
    sys.exit(1)

import pandas as pd
import numpy as np
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from backend import (
    load_universal, QuantileForecaster, npv_auto_size, evaluate_design,
    monthly_dispatch, compare_bills, run_ev_layer,
    RP4_RATES, DEFAULT_CAPEX, is_peak_mask,
    size_equipment, TRINA_PANEL, SIGEN_INVERTER, SIGENSTOR_BAT,
)

# ═════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Train to PJ · EMS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0f1e 0%, #0d1b2a 100%);
    border-right: 1px solid #1e3a5f;
}
[data-testid="stSidebar"] * { color: #d0e8ff !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label { color: #7eb8f7 !important; font-size: 0.82rem !important; }

div[data-testid="metric-container"] {
    background: #f8fbff; border: 1px solid #d6eaff;
    border-radius: 12px; padding: 1rem 1.2rem;
    box-shadow: 0 2px 8px rgba(0,80,180,0.06);
}
div[data-testid="metric-container"] label {
    font-size: 0.78rem !important; color: #5a7a9a !important;
    font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.6rem !important; font-weight: 700; color: #0a1f44 !important;
}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.82rem !important;
}

.section-header {
    font-size: 1.05rem; font-weight: 700; color: #0a1f44;
    letter-spacing: 0.02em; margin: 1.4rem 0 0.6rem 0;
    padding-bottom: 0.4rem; border-bottom: 2px solid #00c97a;
    display: inline-block;
}

button[data-baseweb="tab"] {
    font-size: 0.85rem !important; font-weight: 600 !important;
    color: #5a7a9a !important; padding: 0.5rem 1.1rem !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #0055cc !important; border-bottom: 3px solid #0055cc !important;
}

div[data-testid="stAlert"] { border-radius: 10px !important; }

div[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #00c97a, #0066cc) !important;
    color: white !important; border: none !important;
    font-weight: 700 !important; border-radius: 8px !important;
    padding: 0.6rem !important; letter-spacing: 0.04em !important;
    transition: opacity 0.2s !important;
}
div[data-testid="stSidebar"] .stButton button:hover { opacity: 0.88 !important; }

.stDataFrame { border-radius: 10px !important; overflow: hidden; }

/* select_slider label */
div[data-testid="stSlider"] > label {
    font-size: 0.82rem; font-weight: 600; color: #5a7a9a;
    text-transform: uppercase; letter-spacing: 0.06em;
}
</style>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# HEADER BANNER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="background:linear-gradient(135deg,#0a1f44 0%,#0d3b8c 60%,#005c99 100%);
  border-radius:14px; padding:1.4rem 2rem;
  display:flex; align-items:center; justify-content:space-between;
  box-shadow:0 4px 24px rgba(0,30,100,0.18); margin-bottom:0.5rem;">
  <div>
    <div style="font-size:0.72rem;font-weight:600;color:#7eb8f7;
                letter-spacing:0.12em;text-transform:uppercase;margin-bottom:0.2rem;">
      RExharge Case Study Competition &middot; Theme 1
    </div>
    <div style="font-size:1.85rem;font-weight:800;color:#ffffff;line-height:1.1;">
      Train to PJ
    </div>
    <div style="font-size:0.9rem;color:#a8d4ff;margin-top:0.25rem;">
      Intelligent Energy Management System &nbsp;&middot;&nbsp; Load Shifting &amp; Peak Shaving
    </div>
  </div>
  <div style="display:flex;gap:1.4rem;text-align:center;">
    <div>
      <div style="font-size:1.3rem;font-weight:800;color:#00e68a;">RP4</div>
      <div style="font-size:0.65rem;color:#7eb8f7;letter-spacing:0.06em;">TARIFF</div>
    </div>
    <div>
      <div style="font-size:1.3rem;font-weight:800;color:#00e68a;">MILP</div>
      <div style="font-size:0.65rem;color:#7eb8f7;letter-spacing:0.06em;">DISPATCH</div>
    </div>
    <div>
      <div style="font-size:1.3rem;font-weight:800;color:#00e68a;">P90</div>
      <div style="font-size:0.65rem;color:#7eb8f7;letter-spacing:0.06em;">FORECAST</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

TARIFF_LABELS = {
    "MV_COMMERCIAL_TOU":   "MV Commercial TOU (C2)",
    "MV_INDUSTRIAL_E2":    "MV Industrial E2",
    "LV_NON_DOMESTIC_TOU": "LV Non-Domestic TOU",
}

# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""<div style="font-size:1.05rem;font-weight:700;color:#7eb8f7;
        padding:0.8rem 0 0.4rem;letter-spacing:0.04em;">⚙ CONFIGURATION</div>""",
        unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Building Load Profile", type=["xlsx", "xls", "csv"],
        help="Upload any TNB 30-min export (xlsx or csv)")

    rate_class = st.selectbox(
        "TNB Tariff Class (RP4)", list(RP4_RATES.keys()),
        format_func=lambda k: TARIFF_LABELS[k],
        help="Effective 1 July 2025 — RP4 unbundled rates")

    st.markdown("<div style='margin-top:0.9rem;font-size:0.72rem;font-weight:700;"
                "color:#7eb8f7;letter-spacing:0.1em;'>SYSTEM SIZING</div>",
                unsafe_allow_html=True)
    auto_size = st.toggle("Auto-size by 20-yr NPV", value=True)
    if not auto_size:
        pv_kwp   = st.number_input("Solar PV (kWp)",    0, 5000, 500, 50)
        bess_kw  = st.number_input("BESS Power (kW)",   0, 3000, 200, 25)
        bess_kwh = st.number_input("BESS Energy (kWh)", 0, 8000, 600, 50)
    else:
        pv_kwp = bess_kw = bess_kwh = None

    st.markdown("<div style='margin-top:0.9rem;font-size:0.72rem;font-weight:700;"
                "color:#7eb8f7;letter-spacing:0.1em;'>EV CHARGING HUB</div>",
                unsafe_allow_html=True)
    ev_ac = st.slider("AC Chargers · 22 kW", 0, 20, 0)
    ev_dc = st.slider("DC Fast Chargers · 60 kW", 0, 10, 0)

    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("▶  RUN OPTIMISATION",
                        width="stretch", disabled=(uploaded is None))

    st.markdown("""
    <div style="margin-top:2rem;padding:0.8rem;background:#0d2240;
                border-radius:8px;border:1px solid #1e3a5f;">
      <div style="font-size:0.68rem;color:#7eb8f7;font-weight:600;
                  letter-spacing:0.08em;margin-bottom:0.3rem;">RP4 DEMAND CHARGE</div>
      <div style="font-size:1.25rem;font-weight:800;color:#00e68a;">RM 97.06 / kW</div>
      <div style="font-size:0.66rem;color:#5a8ab0;margin-top:0.2rem;line-height:1.5;">
        Capacity RM 30.19 + Network RM 66.87<br>
        Effective 1 Jul 2025 &middot; mytnb.com.my
      </div>
    </div>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# LANDING PAGE  (shown until file uploaded & button clicked)
# ═════════════════════════════════════════════════════════════════════════════
# Show landing page only when: no file uploaded, OR button not yet clicked AND no cached results exist
_has_results = "_meta" in st.session_state
if uploaded is None or (not run_btn and not _has_results):
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    _card = ("background:{bg};border-radius:14px;padding:1.5rem 1.6rem;"
             "border:1px solid {bd};box-shadow:0 2px 12px rgba(0,60,180,0.06);")
    with c1:
        st.markdown(
            f'<div style="{_card.format(bg="#f0f9f4",bd="#b3e8cc")}">'
            '<div style="font-size:1.8rem;margin-bottom:0.5rem;">🔮</div>'
            '<div style="font-weight:700;font-size:0.95rem;color:#0a3320;margin-bottom:0.35rem;">'
            'Probabilistic Forecast</div>'
            '<div style="font-size:0.83rem;color:#2d6a4f;line-height:1.55;">'
            'P10 / P50 / P90 quantile gradient-boosted regression. '
            'Risk-aware dispatch on the P90 envelope.</div></div>',
            unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div style="{_card.format(bg="#f0f5ff",bd="#b3ccf5")}">'
            '<div style="font-size:1.8rem;margin-bottom:0.5rem;">⚡</div>'
            '<div style="font-weight:700;font-size:0.95rem;color:#0a1f5c;margin-bottom:0.35rem;">'
            'MILP Optimal Dispatch</div>'
            '<div style="font-size:0.83rem;color:#2d4a8c;line-height:1.55;">'
            'One linear programme per calendar month — '
            'globally optimal because TNB bills monthly.</div></div>',
            unsafe_allow_html=True)
    with c3:
        st.markdown(
            f'<div style="{_card.format(bg="#fff8f0",bd="#f5d9b3")}">'
            '<div style="font-size:1.8rem;margin-bottom:0.5rem;">🚗</div>'
            '<div style="font-weight:700;font-size:0.95rem;color:#5c2d00;margin-bottom:0.35rem;">'
            'EV Load Shifting</div>'
            '<div style="font-size:0.83rem;color:#8c4a00;line-height:1.55;">'
            'LP-scheduled EV charging sessions. '
            '85–91% of EV demand shifted to off-peak.</div></div>',
            unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👈  Upload a building load profile (xlsx / csv) and click **RUN OPTIMISATION** to begin.")
    st.stop()

# ═════════════════════════════════════════════════════════════════════════════
# PIPELINE  (runs once per button click; results cached in session_state)
# ═════════════════════════════════════════════════════════════════════════════

# Use a cache key based on the file name + size so re-runs without a new
# upload don't recompute the heavy LP / ML steps.
_file_key = f"{uploaded.name}_{uploaded.size}_{rate_class}_{auto_size}_{pv_kwp}_{bess_kw}_{bess_kwh}_{ev_ac}_{ev_dc}"

if run_btn and st.session_state.get("_cache_key") != _file_key:
    with tempfile.NamedTemporaryFile(suffix=Path(uploaded.name).suffix, delete=False) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name

    prog = st.progress(0, text="Loading building data…")
    try:
        df, meta = load_universal(tmp_path)
    finally:
        os.unlink(tmp_path)
    meta["name"] = Path(uploaded.name).stem   # temp file name is meaningless

    prog.progress(18, text="Training probabilistic forecaster (P10 / P50 / P90)…")
    qf = QuantileForecaster().fit(df)
    fut_ts = pd.date_range(
        df["timestamp"].iloc[-1] + pd.Timedelta(minutes=30),
        periods=14 * 48, freq="30min")
    fcst = qf.predict(pd.Series(fut_ts))

    prog.progress(42, text="Auto-sizing Solar + BESS by 20-yr NPV…")
    if auto_size:
        design, scan = npv_auto_size(df, rate_class)
    else:
        design = evaluate_design(df, rate_class, pv_kwp, bess_kw, bess_kwh)
        scan = pd.DataFrame()

    # Existing PV is already inside the metered load, so only NEW PV is simulated
    prog.progress(65, text="Running MILP monthly-horizon dispatch…")
    bt = monthly_dispatch(df, rate_class, design["bess_kw"], design["bess_kwh"],
                          design["pv_kwp"])
    savings = compare_bills(bt, bt, rate_class, "baseline_grid_kw", "grid_kw")

    ev = {}
    if ev_ac > 0 or ev_dc > 0:
        prog.progress(82, text="Solving EV load-shift LP…")
        ev = run_ev_layer(bt, rate_class, ev_ac, ev_dc)

    prog.progress(100, text="Done ✓")
    prog.empty()

    # Store everything in session_state so slider changes don't re-run the LP
    st.session_state.update({
        "_cache_key": _file_key,
        "_rate":     rate_class,
        "_meta":     meta,
        "_fcst":     fcst,
        "_design":   design,
        "_bt":       bt,
        "_savings":  savings,
        "_ev":       ev,
    })

# Pull from session_state (slider interactions land here without re-running LP)
if st.session_state.get("_cache_key") != _file_key:
    st.warning("Settings changed — showing previous results. "
               "Click **RUN OPTIMISATION** to update.")
rate_class = st.session_state["_rate"]   # tariff the cached results used
meta    = st.session_state["_meta"]
fcst    = st.session_state["_fcst"]
design  = st.session_state["_design"]
bt      = st.session_state["_bt"]
savings = st.session_state["_savings"]
ev      = st.session_state["_ev"]

# ═════════════════════════════════════════════════════════════════════════════
# BUILDING INFO BANNER
# ═════════════════════════════════════════════════════════════════════════════
solar_badge = (f"☀ {meta['declared_pv_kwp']:.0f} kWp installed"
               if meta.get("declared_pv_kwp") else "☀ No existing solar")
st.markdown(f"""
<div style="background:#f4f8ff;border:1px solid #cddcf7;border-radius:10px;
            padding:0.85rem 1.4rem;margin:0.6rem 0 0.4rem;
            display:flex;align-items:center;gap:2rem;flex-wrap:wrap;">
  <div>
    <span style="font-size:0.68rem;font-weight:700;color:#5a7a9a;
                 text-transform:uppercase;letter-spacing:0.08em;">Building</span><br>
    <span style="font-size:1.05rem;font-weight:700;color:#0a1f44;">{meta['name']}</span>
  </div>
  <div style="color:#cddcf7;">│</div>
  <div>
    <span style="font-size:0.68rem;color:#5a7a9a;font-weight:700;text-transform:uppercase;">Peak Load</span><br>
    <span style="font-weight:700;color:#0a1f44;">{meta['max_load_kw']:.0f} kW</span>
  </div>
  <div>
    <span style="font-size:0.68rem;color:#5a7a9a;font-weight:700;text-transform:uppercase;">Mean Load</span><br>
    <span style="font-weight:700;color:#0a1f44;">{meta['mean_load_kw']:.0f} kW</span>
  </div>
  <div>
    <span style="font-size:0.68rem;color:#5a7a9a;font-weight:700;text-transform:uppercase;">Load Factor</span><br>
    <span style="font-weight:700;color:#0a1f44;">{meta['load_factor']:.1%}</span>
  </div>
  <div>
    <span style="font-size:0.68rem;color:#5a7a9a;font-weight:700;text-transform:uppercase;">Data Range</span><br>
    <span style="font-weight:700;color:#0a1f44;">{meta['start_ts'][:10]} → {meta['end_ts'][:10]}</span>
  </div>
  <div style="margin-left:auto;background:#e8f4ff;border-radius:6px;
              padding:0.25rem 0.75rem;font-size:0.8rem;color:#0055cc;font-weight:600;">
    {solar_badge}
  </div>
</div>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# KEY RESULTS KPIs
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">KEY RESULTS</div>', unsafe_allow_html=True)

md_red       = savings["delta"]["md_reduction_kw"]
md_pct       = md_red / max(savings["baseline"]["peak_md_kw"], 1) * 100
monthly_save = savings["delta"]["total_saving_rm"]
annual_save  = monthly_save * 12

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Peak MD Reduction",    f"{md_red:.0f} kW",          f"−{md_pct:.1f}%")
k2.metric("Demand Saving",        f"RM {savings['delta']['demand_saving_rm']:,.0f}", "/month")
k3.metric("Energy Saving",        f"RM {savings['delta']['energy_saving_rm']:,.0f}", "/month")
k4.metric("Total Monthly Saving", f"RM {monthly_save:,.0f}",   f"{savings['delta']['saving_pct']:.1f}%")
k5.metric("Annual Saving",        f"RM {annual_save:,.0f}",    f"RM {annual_save/1e6:.2f}M /yr")

# ═════════════════════════════════════════════════════════════════════════════
# SYSTEM DESIGN KPIs
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">RECOMMENDED SYSTEM DESIGN</div>', unsafe_allow_html=True)

d1, d2, d3, d4, d5 = st.columns(5)
d1.metric("Solar PV",       f"{design['pv_kwp']:.0f} kWp")
d2.metric("BESS Power",     f"{design['bess_kw']:.0f} kW")
d3.metric("BESS Energy",    f"{design['bess_kwh']:.0f} kWh",
          f"{design['bess_kwh']/max(design['bess_kw'],1):.0f}h duration")
d4.metric("System CAPEX",   f"RM {design['capex_rm']:,.0f}")
d5.metric("Payback Period", f"{design['payback_yrs']:.1f} years",
          f"NPV₂₀ RM {design['npv_rm']/1e6:.2f}M")

# ═════════════════════════════════════════════════════════════════════════════
# EQUIPMENT BREAKDOWN (Trina Vertex N + Sigenergy)
# ═════════════════════════════════════════════════════════════════════════════
_equip = size_equipment(design['pv_kwp'], design['bess_kwh'], design['bess_kw'])

st.markdown('<div class="section-header">EQUIPMENT SPECIFICATION</div>',
            unsafe_allow_html=True)

eq_col1, eq_col2, eq_col3 = st.columns(3)
with eq_col1:
    st.markdown(f"""
<div style="background:#fff4e6;border:1px solid #ffd9a8;border-radius:12px;padding:1.1rem 1.3rem;">
  <div style="font-size:0.72rem;font-weight:700;color:#9c5b00;letter-spacing:0.08em;">
    SOLAR PV ARRAY
  </div>
  <div style="font-size:0.82rem;color:#5c2d00;font-weight:600;margin-top:0.3rem;">
    Trina Vertex N
  </div>
  <div style="font-size:0.78rem;color:#7c4b00;line-height:1.55;margin-top:0.5rem;">
    TSM-NEG19RC.20-610W<br>
    N-type TOPCon Bifacial<br>
    22.6% efficiency · 30-yr warranty
  </div>
  <div style="margin-top:0.9rem;padding-top:0.7rem;border-top:1px solid #ffd9a8;">
    <div style="font-size:1.5rem;font-weight:800;color:#9c5b00;">
      {_equip['n_panels']:,} panels
    </div>
    <div style="font-size:0.76rem;color:#7c4b00;">
      {_equip['actual_pv_kwp']:.1f} kWp · {_equip['panel_area_m2']:,.0f} m² roof area
    </div>
  </div>
</div>""", unsafe_allow_html=True)

with eq_col2:
    st.markdown(f"""
<div style="background:#f0f5ff;border:1px solid #b3ccf5;border-radius:12px;padding:1.1rem 1.3rem;">
  <div style="font-size:0.72rem;font-weight:700;color:#0a3aa0;letter-spacing:0.08em;">
    HYBRID INVERTERS
  </div>
  <div style="font-size:0.82rem;color:#0a1f5c;font-weight:600;margin-top:0.3rem;">
    Sigen Hybrid 12.0 TP2
  </div>
  <div style="font-size:0.78rem;color:#2d4a8c;line-height:1.55;margin-top:0.5rem;">
    Three-phase · 12 kW AC<br>
    99% peak efficiency · IP66<br>
    0 ms backup switchover
  </div>
  <div style="margin-top:0.9rem;padding-top:0.7rem;border-top:1px solid #b3ccf5;">
    <div style="font-size:1.5rem;font-weight:800;color:#0a3aa0;">
      {_equip['n_inverters']} units
    </div>
    <div style="font-size:0.76rem;color:#2d4a8c;">
      {_equip['actual_bess_kw']:.0f} kW total AC capacity (parallel)
    </div>
  </div>
</div>""", unsafe_allow_html=True)

with eq_col3:
    st.markdown(f"""
<div style="background:#f0f9f5;border:1px solid #b3e8cc;border-radius:12px;padding:1.1rem 1.3rem;">
  <div style="font-size:0.72rem;font-weight:700;color:#2d6a4f;letter-spacing:0.08em;">
    BATTERY STORAGE
  </div>
  <div style="font-size:0.82rem;color:#0a3320;font-weight:600;margin-top:0.3rem;">
    SigenStor BAT
  </div>
  <div style="font-size:0.78rem;color:#2d4a3e;line-height:1.55;margin-top:0.5rem;">
    5 kWh LFP modules<br>
    1–6 modules per inverter<br>
    95% round-trip efficiency
  </div>
  <div style="margin-top:0.9rem;padding-top:0.7rem;border-top:1px solid #b3e8cc;">
    <div style="font-size:1.5rem;font-weight:800;color:#2d6a4f;">
      {_equip['n_bat_modules']} modules
    </div>
    <div style="font-size:0.76rem;color:#2d4a3e;">
      {_equip['actual_bess_kwh']:.0f} kWh total storage
    </div>
  </div>
</div>""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background:#fafcff;border:1px solid #d6eaff;border-radius:10px;
            padding:0.7rem 1.2rem;margin-top:0.7rem;font-size:0.8rem;color:#3a5680;">
  💡  All equipment selected from <b>RExharge-supplied datasheets</b>.
  Itemised CAPEX: RM {_equip['panel_cost_rm']/1e6:.2f}M panels +
  RM {_equip['inverter_cost_rm']/1e6:.2f}M inverters +
  RM {_equip['battery_cost_rm']/1e6:.2f}M batteries +
  RM {(_equip['bos_cost_rm']+_equip['install_cost_rm']+_equip['ems_cost_rm'])/1e6:.2f}M BOS/install/EMS
  = <b>RM {_equip['total_capex_rm']/1e6:.2f}M total</b>.
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">ANALYSIS</div>', unsafe_allow_html=True)

TAB_DISPATCH, TAB_FORECAST, TAB_BILL, TAB_ROI, TAB_EV = st.tabs([
    "📊  Dispatch & SOC",
    "🔮  Load Forecast",
    "💰  Bill Breakdown",
    "📈  ROI Analysis",
    "🚗  EV Load Shifting",
])

CHART_THEME = dict(
    template="plotly_white",
    font=dict(family="Inter, sans-serif", size=12, color="#0a1f44"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#fafcff",
    hovermode="x unified",
)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — DISPATCH & SOC
# ─────────────────────────────────────────────────────────────────────────────
with TAB_DISPATCH:

    # ── View-window selector ──────────────────────────────────────────────────
    WINDOW_DAYS = {"3 days": 3, "7 days": 7, "14 days": 14}
    sel_label = st.select_slider(
        "View window",
        options=list(WINDOW_DAYS.keys()),
        value="7 days",
        key="dispatch_window",
    )

    # Slice the backtest data — always reset index so row 0 = first interval
    n_pts = min(WINDOW_DAYS[sel_label] * 48, len(bt))
    win = bt.iloc[:n_pts].reset_index(drop=True).copy()

    # Build a fresh boolean array aligned to win's index
    win_peak = is_peak_mask(pd.Series(win["timestamp"].values))  # numpy bool array

    # ── Peak shading helper ───────────────────────────────────────────────────
    def _shade(fig, ts_arr, peak_arr, n_rows=2):
        """Add yellow shading for peak windows. ts_arr and peak_arr must be same length."""
        if len(ts_arr) == 0:
            return
        ts = pd.Series(ts_arr)
        pk = peak_arr.astype(bool)
        changes = list(np.where(np.diff(pk.astype(int)) != 0)[0])
        boundaries = [0] + [c + 1 for c in changes] + [len(pk)]
        for i in range(len(boundaries) - 1):
            s, e = boundaries[i], min(boundaries[i+1], len(ts)-1)
            if pk[s]:
                for row in range(1, n_rows + 1):
                    fig.add_vrect(
                        x0=ts.iloc[s], x1=ts.iloc[e],
                        fillcolor="rgba(255,220,100,0.10)",
                        line_width=0, row=row, col=1)

    # ── Main dual-panel chart ─────────────────────────────────────────────────
    fig_d = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Power Flows (kW)", "Battery State of Charge (%)"),
        vertical_spacing=0.18,
        row_heights=[0.65, 0.35],
    )

    _shade(fig_d, win["timestamp"].values, win_peak, n_rows=2)

    fig_d.add_trace(go.Scatter(
        x=win["timestamp"], y=win["load_kw"],
        name="Building Load",
        line=dict(color="#8098b8", width=1.5, dash="dot")), 1, 1)
    fig_d.add_trace(go.Scatter(
        x=win["timestamp"], y=win["solar_kw"],
        name="Solar Generation",
        line=dict(color="#f5a623", width=2),
        fill="tozeroy", fillcolor="rgba(245,166,35,0.12)"), 1, 1)
    fig_d.add_trace(go.Scatter(
        x=win["timestamp"], y=win["baseline_grid_kw"],
        name="Grid · Baseline",
        line=dict(color="#e8003d", width=1.5, dash="dot")), 1, 1)
    fig_d.add_trace(go.Scatter(
        x=win["timestamp"], y=win["grid_kw"],
        name="Grid · Optimised",
        line=dict(color="#0055cc", width=2.5)), 1, 1)
    fig_d.add_trace(go.Bar(
        x=win["timestamp"], y=win["bess_kw"].clip(lower=0),
        name="BESS Discharge",
        marker_color="rgba(0,180,100,0.7)"), 1, 1)
    fig_d.add_trace(go.Bar(
        x=win["timestamp"], y=win["bess_kw"].clip(upper=0),
        name="BESS Charge",
        marker_color="rgba(100,100,255,0.5)"), 1, 1)
    fig_d.add_trace(go.Scatter(
        x=win["timestamp"], y=win["soc_pct"],
        name="SOC %",
        line=dict(color="#7b2fbe", width=2.5),
        fill="tozeroy", fillcolor="rgba(123,47,190,0.10)"), 2, 1)

    fig_d.add_hline(y=20, line_dash="dot", line_color="#e8003d", line_width=1,
                    annotation_text="Min SOC 20%", annotation_position="top right",
                    annotation_font=dict(size=9, color="#e8003d"), row=2, col=1)
    fig_d.add_hline(y=95, line_dash="dot", line_color="#0055cc", line_width=1,
                    annotation_text="Max SOC 95%", annotation_position="bottom right",
                    annotation_font=dict(size=9, color="#0055cc"), row=2, col=1)

    fig_d.update_yaxes(title_text="kW", row=1, col=1, gridcolor="#e8eef8")
    fig_d.update_yaxes(title_text="%", row=2, col=1, range=[0, 108], gridcolor="#e8eef8")
    fig_d.update_xaxes(gridcolor="#e8eef8", tickangle=-40)
    fig_d.update_layout(
        **CHART_THEME,
        legend=dict(orientation="h", yanchor="bottom", y=1.12,
                    xanchor="left", x=0, font=dict(size=10)),
        height=600, barmode="overlay",
        margin=dict(l=10, r=10, t=90, b=40),
    )
    st.plotly_chart(fig_d, width="stretch")

    # ── Daily peak bar — same window ──────────────────────────────────────────
    win_pk_rows = win[win_peak].copy()
    if not win_pk_rows.empty:
        win_pk_rows["_date"] = pd.to_datetime(win_pk_rows["timestamp"]).dt.date
        daily = (win_pk_rows.groupby("_date")
                            .agg(baseline=("baseline_grid_kw", "max"),
                                 optimised=("grid_kw", "max"))
                            .reset_index())

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=daily["_date"].astype(str), y=daily["baseline"],
            name="Baseline MD", marker_color="#e8003d", opacity=0.45))
        fig_bar.add_trace(go.Bar(
            x=daily["_date"].astype(str), y=daily["optimised"],
            name="Optimised MD", marker_color="#0055cc", opacity=0.88))
        fig_bar.update_layout(
            **CHART_THEME,
            legend=dict(orientation="h", yanchor="bottom", y=1.05,
                        xanchor="left", x=0, font=dict(size=11)),
            height=320, barmode="overlay",
            title=f"Daily Peak Maximum Demand — {sel_label}",
            yaxis_title="kW",
            xaxis=dict(tickangle=-55, gridcolor="#e8eef8"),
            yaxis=dict(gridcolor="#e8eef8"),
            bargap=0.2,
            margin=dict(l=50, r=30, t=60, b=110),
        )
        st.plotly_chart(fig_bar, width="stretch")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — FORECAST
# ─────────────────────────────────────────────────────────────────────────────
with TAB_FORECAST:
    cl, cr = st.columns([2, 1])

    with cl:
        fig_f = go.Figure()
        # Invisible upper trace so fill "tonexty" fills P10→P90
        fig_f.add_trace(go.Scatter(
            x=fcst["timestamp"], y=fcst["p90"],
            line=dict(color="rgba(0,0,0,0)", width=0),
            showlegend=False, hoverinfo="skip"))
        fig_f.add_trace(go.Scatter(
            x=fcst["timestamp"], y=fcst["p10"],
            name="P10–P90 Confidence Band",
            fill="tonexty", fillcolor="rgba(0,85,204,0.10)",
            line=dict(color="rgba(0,0,0,0)", width=0)))
        fig_f.add_trace(go.Scatter(
            x=fcst["timestamp"], y=fcst["p90"],
            name="P90 — High",
            line=dict(color="#0055cc", width=1, dash="dot")))
        fig_f.add_trace(go.Scatter(
            x=fcst["timestamp"], y=fcst["p10"],
            name="P10 — Low",
            line=dict(color="#00aa55", width=1, dash="dot")))
        fig_f.add_trace(go.Scatter(
            x=fcst["timestamp"], y=fcst["p50"],
            name="P50 — Median",
            line=dict(color="#0a1f44", width=2.5)))
        fig_f.update_layout(
            **CHART_THEME,
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        xanchor="left", x=0, font=dict(size=11)),
            height=480,
            title="14-Day Probabilistic Load Forecast",
            yaxis_title="Load (kW)", xaxis_title="Date",
            yaxis=dict(gridcolor="#e8eef8"),
            xaxis=dict(gridcolor="#e8eef8", tickangle=-55),
            margin=dict(l=60, r=30, t=60, b=110),
        )
        st.plotly_chart(fig_f, width="stretch")

    with cr:
        st.markdown("""
<div style="background:#f4f8ff;border:1px solid #cddcf7;border-radius:12px;padding:1.2rem;margin-bottom:0.8rem;">
  <div style="font-size:0.72rem;font-weight:700;color:#5a7a9a;letter-spacing:0.08em;margin-bottom:0.7rem;">
    FORECAST STATISTICS
  </div>""", unsafe_allow_html=True)
        spread = float(fcst["p90"].mean() - fcst["p10"].mean())
        st.metric("P50 Mean",         f"{fcst['p50'].mean():.0f} kW")
        st.metric("P90 Peak",         f"{fcst['p90'].max():.0f} kW")
        st.metric("P10 Trough",       f"{fcst['p10'].min():.0f} kW")
        st.metric("P10–P90 Spread",   f"{spread:.0f} kW avg")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
<div style="background:#f0f9f5;border:1px solid #b3e8cc;border-radius:12px;padding:1.2rem;">
  <div style="font-size:0.72rem;font-weight:700;color:#2d6a4f;letter-spacing:0.08em;margin-bottom:0.5rem;">
    METHODOLOGY
  </div>
  <div style="font-size:0.81rem;color:#2d4a3e;line-height:1.6;">
    Quantile Gradient Boosting trained on historical load with calendar,
    cyclic, and lag features. Each quantile maintains its own autoregressive
    trajectory. Empirical coverage: ~83% of actuals fall inside the
    P10–P90 envelope.
  </div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — BILL BREAKDOWN
# ─────────────────────────────────────────────────────────────────────────────
with TAB_BILL:
    r_   = RP4_RATES[rate_class]
    b_   = savings["baseline"]
    o_   = savings["optimised"]

    comp = ["Capacity Charge", "Network Charge",
            "Energy (Peak)", "Energy (Off-Peak)", "AFA"]
    bv = [
        b_["capacity_rm"],
        b_["network_rm"],
        b_["energy_peak_kwh"]    * r_["energy_peak_rm_kwh"],
        b_["energy_offpeak_kwh"] * r_["energy_offpeak_rm_kwh"],
        b_["afa_rm"],
    ]
    ov = [
        o_["capacity_rm"],
        o_["network_rm"],
        o_["energy_peak_kwh"]    * r_["energy_peak_rm_kwh"],
        o_["energy_offpeak_kwh"] * r_["energy_offpeak_rm_kwh"],
        o_["afa_rm"],
    ]
    sv = [bi - oi for bi, oi in zip(bv, ov)]

    fl, fr = st.columns([3, 2])

    with fl:
        fig_bill = go.Figure()
        fig_bill.add_trace(go.Bar(
            name="Baseline", x=comp, y=bv,
            marker_color="#e8003d", opacity=0.70,
            text=[f"RM {v:,.0f}" for v in bv],
            textposition="outside",
            textfont=dict(size=10),
        ))
        fig_bill.add_trace(go.Bar(
            name="Optimised", x=comp, y=ov,
            marker_color="#0055cc", opacity=0.88,
            text=[f"RM {v:,.0f}" for v in ov],
            textposition="outside",
            textfont=dict(size=10),
        ))
        fig_bill.update_layout(
            **CHART_THEME,
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        xanchor="left", x=0, font=dict(size=11)),
            height=500, barmode="group",
            title="Monthly Bill Component Breakdown (RM)",
            yaxis_title="RM / month",
            yaxis=dict(gridcolor="#e8eef8"),
            xaxis=dict(tickangle=-55),
            margin=dict(l=60, r=30, t=60, b=130),
            uniformtext_minsize=8, uniformtext_mode="hide",
        )
        st.plotly_chart(fig_bill, width="stretch")

    with fr:
        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative"] * len(comp) + ["total"],
            x=comp + ["Total Saving"],
            y=[-s for s in sv] + [None],
            connector={"line": {"color": "#cddcf7"}},
            decreasing={"marker": {"color": "#00aa55"}},
            increasing={"marker": {"color": "#e8003d"}},
            totals={"marker":   {"color": "#0055cc"}},
            text=[f"RM {s:,.0f}" for s in sv] + [f"RM {sum(sv):,.0f}"],
            textposition="outside",
            textfont=dict(size=10),
        ))
        fig_wf.update_layout(
            **CHART_THEME,
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        xanchor="left", x=0, font=dict(size=11)),
            height=500,
            title="Savings Waterfall (RM / month)",
            yaxis_title="RM",
            yaxis=dict(gridcolor="#e8eef8"),
            xaxis=dict(tickangle=-55),
            margin=dict(l=60, r=30, t=60, b=130),
        )
        st.plotly_chart(fig_wf, width="stretch")

    bill_df = pd.DataFrame({
        "Component":      comp,
        "Baseline (RM)":  [f"{v:,.0f}" for v in bv],
        "Optimised (RM)": [f"{v:,.0f}" for v in ov],
        "Saving (RM)":    [f"{v:,.0f}" for v in sv],
        "Saving %":       [f"{v/max(b,1)*100:.1f}%" for v, b in zip(sv, bv)],
    })
    st.dataframe(bill_df, hide_index=True, width="stretch")

    st.markdown("<br>", unsafe_allow_html=True)
    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("Baseline Total",  f"RM {b_['total_rm']:,.0f} /mo")
    tc2.metric("Optimised Total", f"RM {o_['total_rm']:,.0f} /mo")
    tc3.metric("Monthly Saving",
               f"RM {b_['total_rm']-o_['total_rm']:,.0f}",
               f"{savings['delta']['saving_pct']:.1f}%")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — ROI
# ─────────────────────────────────────────────────────────────────────────────
with TAB_ROI:
    # Same assumptions as backend.evaluate_design (DEFAULT_CAPEX)
    equip    = size_equipment(design['pv_kwp'], design['bess_kwh'], design['bess_kw'])
    life     = DEFAULT_CAPEX["system_life_yrs"]
    rep_yr   = DEFAULT_CAPEX["battery_replace_yrs"]
    capex    = design["capex_rm"]
    ann_save = monthly_save * 12
    opm_ann  = capex * DEFAULT_CAPEX["annual_opm_pct"]
    net_ann  = ann_save - opm_ann
    disc_r   = DEFAULT_CAPEX["discount_rate"]
    years    = list(range(0, life + 1))
    cum_save = [0] + [net_ann * y for y in range(1, life + 1)]
    npv_running = -capex
    npv_path = [-capex]
    for y in range(1, life + 1):
        npv_running += net_ann / ((1 + disc_r) ** y)
        if y == rep_yr:
            npv_running -= equip["battery_cost_rm"] * 0.6 / ((1 + disc_r) ** rep_yr)
        npv_path.append(npv_running)
    payback_yr = next((y for y, c in enumerate(cum_save) if c >= capex), None)

    rl, rr = st.columns([3, 2])

    with rl:
        fig_roi = go.Figure()
        if max(npv_path) > 0:
            fig_roi.add_hrect(
                y0=0, y1=max(npv_path) * 1.05,
                fillcolor="rgba(0,180,100,0.04)", line_width=0,
                annotation_text="Profitable zone",
                annotation_position="top left",
                annotation_font=dict(size=10, color="#00aa55"))
        fig_roi.add_trace(go.Scatter(
            x=years, y=npv_path, name="Cumulative NPV (RM)",
            line=dict(color="#0055cc", width=3),
            fill="tozeroy", fillcolor="rgba(0,85,204,0.08)"))
        fig_roi.add_trace(go.Scatter(
            x=years, y=[c - capex for c in cum_save],
            name="Simple Payback (undiscounted)",
            line=dict(color="#00aa55", width=2, dash="dot")))
        if payback_yr:
            fig_roi.add_vline(
                x=payback_yr, line_dash="dash", line_color="#f5a623",
                annotation_text=f"Payback yr {payback_yr}",
                annotation_position="top right",
                annotation_font=dict(color="#a07800", size=11))
        fig_roi.add_hline(y=0, line_color="#8098b8", line_width=1)
        fig_roi.update_layout(
            **CHART_THEME,
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        xanchor="left", x=0, font=dict(size=11)),
            height=480,
            title="20-Year Financial Model (6% Discount Rate)",
            yaxis_title="RM", xaxis_title="Year",
            yaxis=dict(gridcolor="#e8eef8"),
            xaxis=dict(gridcolor="#e8eef8", dtick=2),
            margin=dict(l=80, r=30, t=60, b=90),
        )
        st.plotly_chart(fig_roi, width="stretch")

    with rr:
        st.markdown("""
<div style="background:#f4f8ff;border:1px solid #cddcf7;border-radius:12px;
            padding:1.2rem;margin-bottom:0.8rem;">
  <div style="font-size:0.72rem;font-weight:700;color:#5a7a9a;
              letter-spacing:0.08em;margin-bottom:0.7rem;">INVESTMENT SUMMARY</div>
""", unsafe_allow_html=True)
        st.metric("Total CAPEX",        f"RM {capex:,.0f}")
        st.metric("Annual Net Saving",  f"RM {net_ann:,.0f}")
        st.metric("Simple Payback",     f"{capex/max(net_ann,1):.1f} years")
        st.metric("20-Year NPV",
                  f"RM {npv_path[-1]:,.0f}",
                  "Positive ✓" if npv_path[-1] > 0 else "Negative")
        st.markdown("</div>", unsafe_allow_html=True)

        # Real equipment breakdown from Trina + Sigenergy datasheets
        roi_df = pd.DataFrame({
            "Item": [
                f"Trina Vertex N panels (× {equip['n_panels']:,})",
                f"Sigen Hybrid 12.0 TP2 (× {equip['n_inverters']})",
                f"SigenStor BAT modules (× {equip['n_bat_modules']})",
                "BOS / mounting / cabling",
                "Installation & commissioning",
                "EMS software",
                "O&M /yr (1.5%)",
            ],
            "Cost (RM)": [
                f"{equip['panel_cost_rm']:,.0f}",
                f"{equip['inverter_cost_rm']:,.0f}",
                f"{equip['battery_cost_rm']:,.0f}",
                f"{equip['bos_cost_rm']:,.0f}",
                f"{equip['install_cost_rm']:,.0f}",
                f"{equip['ems_cost_rm']:,.0f}",
                f"{opm_ann:,.0f}",
            ],
        })
        st.dataframe(roi_df, hide_index=True, width="stretch")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — EV LOAD SHIFTING
# ─────────────────────────────────────────────────────────────────────────────
with TAB_EV:
    if ev.get("n_sessions"):
        el, er = st.columns([1, 2])

        with el:
            st.markdown("""
<div style="background:#f0f9f5;border:1px solid #b3e8cc;border-radius:12px;padding:1.2rem;">
  <div style="font-size:0.72rem;font-weight:700;color:#2d6a4f;
              letter-spacing:0.08em;margin-bottom:0.7rem;">EV CHARGING RESULTS</div>
""", unsafe_allow_html=True)
            st.metric("Sessions Scheduled",    f"{ev['n_sessions']}")
            st.metric("Total Energy Delivered", f"{ev['total_ev_kwh']:.0f} kWh")
            st.metric("Off-Peak Fraction",      f"{ev['offpeak_fraction']:.1%}")
            pct_peak = ev["peak_ev_kwh"] / max(ev["total_ev_kwh"], 1) * 100
            st.metric("Peak Window Share",
                      f"{ev['peak_ev_kwh']:.0f} kWh",
                      f"{pct_peak:.0f}% during peak window")
            st.markdown("</div>", unsafe_allow_html=True)

        with er:
            fig_ev = go.Figure(go.Pie(
                labels=["Off-Peak Charging", "Peak-Window Charging"],
                values=[ev["offpeak_ev_kwh"], ev["peak_ev_kwh"]],
                marker_colors=["#00aa55", "#e8003d"],
                hole=0.55,
                textinfo="label+percent",
                textfont=dict(size=12, family="Inter"),
                insidetextorientation="radial",
            ))
            fig_ev.update_layout(
                **CHART_THEME,
                legend=dict(orientation="h", yanchor="top", y=-0.15,
                            xanchor="center", x=0.5, font=dict(size=11)),
                height=340,
                title="EV Charging Distribution by TOU Window",
                annotations=[dict(
                    text=f"{ev['offpeak_fraction']:.0%}<br>off-peak",
                    x=0.5, y=0.5,
                    font=dict(size=15, color="#0a1f44"),
                    showarrow=False,
                )],
                showlegend=True,
                margin=dict(l=10, r=10, t=50, b=60),
            )
            st.plotly_chart(fig_ev, width="stretch")

        st.info(
            f"✅  {ev['offpeak_fraction']:.0%} of EV energy scheduled during off-peak hours "
            f"(before 14:00 or after 22:00 on weekdays). "
            f"This is the **load shifting** half of Theme 1.")
    else:
        st.markdown("""
<div style="background:#f4f8ff;border:1px solid #cddcf7;border-radius:14px;
            padding:2.5rem;text-align:center;">
  <div style="font-size:2.2rem;margin-bottom:0.8rem;">🚗</div>
  <div style="font-size:1rem;font-weight:700;color:#0a1f44;margin-bottom:0.5rem;">
    EV Load-Shifting Ready
  </div>
  <div style="font-size:0.86rem;color:#5a7a9a;line-height:1.65;">
    Enable AC or DC chargers in the sidebar to model EV charging sessions.<br>
    The LP scheduler shifts 85–91% of EV demand into off-peak hours,<br>
    reducing both peak demand charges and energy cost.
  </div>
</div>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin-top:2.5rem;padding:0.9rem 1.4rem;background:#0a1f44;
            border-radius:10px;display:flex;justify-content:space-between;
            align-items:center;flex-wrap:wrap;gap:0.5rem;">
  <div>
    <span style="color:#7eb8f7;font-weight:700;font-size:0.88rem;">Train to PJ</span>
    <span style="color:#3a6899;font-size:0.82rem;">
      &nbsp;&middot;&nbsp;RExharge Case Study Competition
      &nbsp;&middot;&nbsp;Theme 1: Load Shifting &amp; Peak Shaving
    </span>
  </div>
  <div style="display:flex;gap:1.5rem;">
    <span style="color:#3a6899;font-size:0.76rem;">TNB RP4 Tariff &middot; 1 Jul 2025</span>
    <span style="color:#3a6899;font-size:0.76rem;">
      {TARIFF_LABELS[rate_class]}
    </span>
  </div>
</div>
""", unsafe_allow_html=True)
