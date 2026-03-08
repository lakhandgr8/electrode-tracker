import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================
PAGE_TITLE  = "Electrode Consumption Tracker"
PAGE_ICON   = "⚡"
DATE_FORMAT = "%d-%b-%Y"

COLUMNS_E   = ["E1", "E2", "E3"]
MAKES       = ["HEG", "GIL", "Other"]
TYPES       = ["SHP", "UHP"]

# Electrode Additions sheet columns
EA_COLS = [
    "Entry ID", "Date", "Heat No", "Column",
    "Electrode ID", "Electrode Wt (Kg)", "Make", "Type",
    "Total Consumption (Kg)", "Remarks"
]

# Daily Summary sheet columns
DS_COLS = [
    "Date", "Electrode Cons (MT)", "Electrode Cons (PCs)",
    "Power Cons (KWh)", "LM Produced EAF (MT)", "LM Produced QP (MT)",
    "Sp Cons on LM (kg/MT)", "Sp Cons on Power (kg/KWh)", "Remarks"
]

GSHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")

# ============================================================
# AUTHENTICATION
# ============================================================
try:
    with open("config.yaml") as f:
        config = yaml.load(f, Loader=SafeLoader)
except FileNotFoundError:
    st.error("🚨 Missing 'config.yaml'. Please create it to enable login.")
    st.stop()

if not st.session_state.get("authentication_status"):
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(160deg, #0a1628 0%, #112240 60%, #1a1a2e 100%) !important;
    }
    [data-testid="stMain"] { background: transparent !important; }
    header[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }
    #MainMenu, footer { visibility: hidden !important; }
    [data-testid="block-container"] {
        max-width: 380px !important;
        padding-top: 40px !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        margin: 0 auto !important;
    }
    div[data-testid="stForm"] {
        background: white !important;
        border-radius: 14px !important;
        padding: 22px 24px 16px !important;
        box-shadow: 0 16px 50px rgba(0,0,0,0.45) !important;
        border-top: 4px solid #00bcd4 !important;
    }
    div[data-testid="stForm"] h2 { display: none !important; }
    div[data-testid="stForm"] input {
        border-radius: 7px !important;
        border: 1.5px solid #e0e4f0 !important;
        background: #f7f9ff !important;
        font-size: 13px !important;
        padding: 7px 10px !important;
    }
    div[data-testid="stForm"] input:focus {
        border-color: #0077b6 !important;
        box-shadow: 0 0 0 3px rgba(0,119,182,0.1) !important;
    }
    div[data-testid="stForm"] label p {
        font-weight: 600 !important; color: #1a3a5c !important; font-size: 12px !important;
    }
    div[data-testid="stForm"] button[kind="primaryFormSubmit"],
    div[data-testid="stForm"] button[data-testid="baseButton-primaryFormSubmit"] {
        background: linear-gradient(135deg, #0077b6, #023e8a) !important;
        color: white !important; border-radius: 8px !important;
        font-weight: 700 !important; font-size: 13px !important;
        border: none !important; width: 100% !important; padding: 10px !important;
        box-shadow: 0 4px 14px rgba(0,119,182,0.4) !important; margin-top: 4px !important;
    }
    div[data-testid="stForm"] [data-baseweb="input"] button {
        width: 26px !important; height: 26px !important;
        min-height: 26px !important; padding: 0 !important;
    }
    div[data-testid="stForm"] [data-baseweb="input"] button svg {
        width: 14px !important; height: 14px !important;
    }
    [data-testid="stCheckbox"] label p,
    [data-testid="stCheckbox"] span {
        color: rgba(255,255,255,0.7) !important; font-size: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; padding:0 0 24px 0;">
        <div style="display:inline-flex; align-items:center; justify-content:center;
                    width:68px; height:68px;
                    background:linear-gradient(135deg,#0077b6,#023e8a);
                    border-radius:16px; font-size:32px;
                    box-shadow:0 8px 28px rgba(0,119,182,0.5); margin-bottom:14px;">⚡</div>
        <h1 style="color:white; font-size:1.6rem; font-weight:900; margin:0 0 5px 0;">
            Electrode Consumption Tracker
        </h1>
        <p style="color:rgba(255,255,255,0.45); font-size:.85rem; margin:0 0 14px 0;">
            EAF Operations &nbsp;·&nbsp; Electrode Management System
        </p>
        <div style="display:flex; justify-content:center; gap:8px; flex-wrap:wrap;">
            <span style="background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.14);
                         border-radius:50px; padding:4px 11px; color:rgba(255,255,255,0.65); font-size:11px;">
                ⚡ Electrode Additions</span>
            <span style="background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.14);
                         border-radius:50px; padding:4px 11px; color:rgba(255,255,255,0.65); font-size:11px;">
                📊 Daily Summary</span>
            <span style="background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.14);
                         border-radius:50px; padding:4px 11px; color:rgba(255,255,255,0.65); font-size:11px;">
                ☁️ Cloud Sync</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    remember_me = st.checkbox("🔒 Remember me for 30 days",
                               value=st.session_state.get("remember_me_pref", False),
                               key="remember_me_checkbox")
    st.session_state["remember_me_pref"] = remember_me
    expiry_days = 30 if remember_me else 1

    authenticator = stauth.Authenticate(
        config["credentials"], config["cookie"]["name"],
        config["cookie"]["key"], expiry_days
    )
    try:
        authenticator.login()
    except Exception as e:
        st.error(str(e))

    if st.session_state["authentication_status"] is False:
        st.error("❌ Incorrect username or password.")

    st.markdown("""<p style="text-align:center;color:rgba(255,255,255,0.18);
        font-size:11px;margin-top:28px;">© 2025 EAF Electrode Management System</p>""",
        unsafe_allow_html=True)
    st.stop()

remember_me   = st.session_state.get("remember_me_pref", False)
expiry_days   = 30 if remember_me else 1
authenticator = stauth.Authenticate(
    config["credentials"], config["cookie"]["name"],
    config["cookie"]["key"], expiry_days
)

# ============================================================
# APP CSS (post-login)
# ============================================================
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#f0f4f8; }
[data-testid="stSidebar"]          { background:#0a1628; }
[data-testid="stSidebar"] * { color:#d0d8e8 !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color:#ffffff !important; }

.main-header {
    background: linear-gradient(135deg,#0a1628 0%,#0077b6 60%,#023e8a 100%);
    padding:24px 20px; border-radius:14px;
    margin-bottom:22px; text-align:center; color:white;
    box-shadow:0 4px 20px rgba(0,0,0,.3);
}
.main-header h1 { font-size:1.8rem; margin:0 0 4px 0; letter-spacing:1px; }
.main-header p  { margin:0; opacity:.8; font-size:.95rem; }

.kpi-card {
    background:white; border-radius:12px;
    padding:16px 14px; text-align:center;
    box-shadow:0 2px 10px rgba(0,0,0,.07);
    border-top:4px solid #0077b6; margin-bottom:8px;
}
.kpi-card .kpi-val   { font-size:1.5rem; font-weight:700; color:#0077b6; }
.kpi-card .kpi-sub   { font-size:.82rem; color:#0077b6; opacity:.7; font-weight:600; }
.kpi-card .kpi-label { font-size:.72rem; color:#888;
                        text-transform:uppercase; letter-spacing:.5px; margin-top:4px; }

.section-header {
    font-size:1.05rem; font-weight:700; color:#0077b6;
    border-bottom:2px solid #e0e8f0;
    padding-bottom:6px; margin-bottom:14px;
}
.form-section {
    background:white; border-radius:12px;
    padding:20px; margin-bottom:16px;
    box-shadow:0 2px 8px rgba(0,0,0,.06);
}
.download-card {
    background:white; border-radius:12px;
    padding:22px; margin-bottom:14px;
    box-shadow:0 2px 10px rgba(0,0,0,.07);
    border-left:5px solid #0077b6;
}
.download-card h3 { color:#0077b6; margin-bottom:4px; }
.download-card p  { color:#666; font-size:13px; margin-bottom:12px; }

.badge {
    display:inline-block; border-radius:10px;
    padding:2px 9px; font-size:11px; font-weight:700;
}
.badge-e1 { background:#e3f2fd; color:#1565c0; border:1px solid #90caf9; }
.badge-e2 { background:#e8f5e9; color:#2e7d32; border:1px solid #a5d6a7; }
.badge-e3 { background:#fff3e0; color:#e65100; border:1px solid #ffcc80; }
.badge-heg { background:#f3e5f5; color:#6a1b9a; border:1px solid #ce93d8; }
.badge-gil { background:#e0f7fa; color:#00695c; border:1px solid #80cbc4; }

.alert-info {
    background:#e3f2fd; border-left:4px solid #1976d2;
    padding:10px 14px; border-radius:8px; color:#0d47a1;
    font-weight:600; margin-bottom:10px;
}
.del-btn button {
    background:#ef5350 !important; color:white !important;
    border:none !important; border-radius:6px !important;
    font-size:13px !important; min-height:30px !important;
    width:100% !important;
}
div[data-testid="stHorizontalBlock"] { align-items:center; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# GOOGLE SHEETS PERSISTENCE
# ============================================================
def _get_client():
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    for k in ("spreadsheet", "type", "allow_programmatic_writes"):
        creds_dict.pop(k, None)
    creds = Credentials.from_service_account_info(creds_dict, scopes=GSHEETS_SCOPES)
    return gspread.authorize(creds)


def _get_ws(tab_name: str, headers: list):
    client = _get_client()
    url    = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh     = client.open_by_url(url)
    try:
        ws = sh.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab_name, rows=2000, cols=len(headers) + 2)
        ws.append_row(headers)
    return ws


def _safe_rows(df: pd.DataFrame, cols: list) -> list:
    rows = []
    for row in df[cols].values.tolist():
        safe = []
        for v in row:
            if v is None or (isinstance(v, float) and pd.isna(v)):
                safe.append("")
            elif isinstance(v, (int, float, str, bool)):
                safe.append(v)
            else:
                safe.append(str(v))
        rows.append(safe)
    return rows


def load_electrode_additions() -> pd.DataFrame:
    try:
        ws      = _get_ws("ElectrodeAdditions", EA_COLS)
        records = ws.get_all_records(expected_headers=EA_COLS)
        if not records:
            return pd.DataFrame(columns=EA_COLS)
        df = pd.DataFrame(records).dropna(how="all").reset_index(drop=True)
        if len(df) == 0:
            return pd.DataFrame(columns=EA_COLS)
        df["Date"]               = pd.to_datetime(df["Date"], errors="coerce")
        df["Entry ID"]           = pd.to_numeric(df["Entry ID"], errors="coerce").fillna(0).astype(int)
        df["Electrode Wt (Kg)"]  = pd.to_numeric(df["Electrode Wt (Kg)"], errors="coerce").fillna(0.0)
        df["Total Consumption (Kg)"] = pd.to_numeric(df["Total Consumption (Kg)"], errors="coerce").fillna(0.0)
        df["Remarks"]            = df["Remarks"].fillna("").astype(str)
        return df
    except Exception as e:
        import traceback
        st.error(f"❌ LOAD ERROR (Additions) — {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
        return pd.DataFrame(columns=EA_COLS)


def save_electrode_additions(df: pd.DataFrame) -> bool:
    try:
        ws  = _get_ws("ElectrodeAdditions", EA_COLS)
        out = df.copy()
        out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
        for c in ["Electrode Wt (Kg)", "Total Consumption (Kg)", "Entry ID"]:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
        out["Remarks"] = out["Remarks"].fillna("").astype(str)
        ws.clear()
        ws.update("A1", [EA_COLS] + _safe_rows(out, EA_COLS))
        return True
    except Exception as e:
        import traceback
        st.error(f"❌ SAVE ERROR (Additions) — {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
        return False


def load_daily_summary() -> pd.DataFrame:
    try:
        ws      = _get_ws("DailySummary", DS_COLS)
        records = ws.get_all_records(expected_headers=DS_COLS)
        if not records:
            return pd.DataFrame(columns=DS_COLS)
        df = pd.DataFrame(records).dropna(how="all").reset_index(drop=True)
        if len(df) == 0:
            return pd.DataFrame(columns=DS_COLS)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        for c in ["Electrode Cons (MT)", "Electrode Cons (PCs)", "Power Cons (KWh)",
                  "LM Produced EAF (MT)", "LM Produced QP (MT)",
                  "Sp Cons on LM (kg/MT)", "Sp Cons on Power (kg/KWh)"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        df["Remarks"] = df["Remarks"].fillna("").astype(str)
        return df
    except Exception as e:
        import traceback
        st.error(f"❌ LOAD ERROR (Daily Summary) — {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
        return pd.DataFrame(columns=DS_COLS)


def save_daily_summary(df: pd.DataFrame) -> bool:
    try:
        ws  = _get_ws("DailySummary", DS_COLS)
        out = df.copy()
        out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
        for c in ["Electrode Cons (MT)", "Electrode Cons (PCs)", "Power Cons (KWh)",
                  "LM Produced EAF (MT)", "LM Produced QP (MT)",
                  "Sp Cons on LM (kg/MT)", "Sp Cons on Power (kg/KWh)"]:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
        out["Remarks"] = out["Remarks"].fillna("").astype(str)
        ws.clear()
        ws.update("A1", [DS_COLS] + _safe_rows(out, DS_COLS))
        return True
    except Exception as e:
        import traceback
        st.error(f"❌ SAVE ERROR (Daily Summary) — {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
        return False


# ============================================================
# SESSION STATE INIT
# ============================================================
if "ea_data" not in st.session_state:
    st.session_state.ea_data = load_electrode_additions()
if "ds_data" not in st.session_state:
    st.session_state.ds_data = load_daily_summary()


# ============================================================
# HELPERS
# ============================================================
def fmt_date(dt) -> str:
    try:
        return pd.to_datetime(dt).strftime(DATE_FORMAT)
    except Exception:
        return ""


def kpi(label: str, val: str, sub: str = "") -> str:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (f'<div class="kpi-card">'
            f'<div class="kpi-val">{val}</div>{sub_html}'
            f'<div class="kpi-label">{label}</div></div>')


def next_ea_id() -> int:
    df = st.session_state.ea_data
    return int(df["Entry ID"].max()) + 1 if len(df) > 0 else 1


def build_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode()


def build_excel(sheets: dict) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in sheets.items():
            df.to_excel(w, index=False, sheet_name=name[:31])
    return buf.getvalue()


def build_pdf(title: str, sections: list) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, Image as RLImage,
                                    HRFlowable)
    import tempfile, os

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                             leftMargin=1.5*cm, rightMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles  = getSampleStyleSheet()
    s_title = ParagraphStyle("T", parent=styles["Title"], fontSize=17,
                              textColor=colors.HexColor("#0077b6"), spaceAfter=4)
    s_h2    = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12,
                              spaceBefore=12, spaceAfter=4,
                              textColor=colors.HexColor("#023e8a"))
    s_meta  = ParagraphStyle("M", parent=styles["Normal"], fontSize=8,
                              textColor=colors.grey)
    s_body  = ParagraphStyle("B", parent=styles["Normal"], fontSize=9, spaceAfter=4)

    story = [
        Paragraph("⚡ Electrode Consumption Tracker", s_title),
        Paragraph(title, s_h2),
        Paragraph(f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}  |  EAF Operations", s_meta),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0077b6"), spaceAfter=10),
    ]
    for sec in sections:
        if sec["type"] == "heading":
            story.append(Paragraph(sec["text"], s_h2))
        elif sec["type"] == "text":
            story.append(Paragraph(sec["text"], s_body))
        elif sec["type"] == "table":
            df_t = sec["df"].fillna("").astype(str)
            data = [list(df_t.columns)] + df_t.values.tolist()
            cw   = (landscape(A4)[0] - 3*cm) / max(len(df_t.columns), 1)
            tbl  = Table(data, colWidths=[cw]*len(df_t.columns), repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",  (0,0),(-1,0),  colors.HexColor("#0077b6")),
                ("TEXTCOLOR",   (0,0),(-1,0),  colors.white),
                ("FONTNAME",    (0,0),(-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",    (0,0),(-1,-1), 7),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f0f8ff")]),
                ("GRID",        (0,0),(-1,-1), 0.3, colors.HexColor("#cccccc")),
                ("LEFTPADDING", (0,0),(-1,-1), 4),
                ("RIGHTPADDING",(0,0),(-1,-1), 4),
                ("TOPPADDING",  (0,0),(-1,-1), 3),
                ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 8))
        elif sec["type"] == "fig":
            try:
                img_bytes = sec["fig"].to_image(format="png", width=900, height=380, scale=2)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                tmp.write(img_bytes); tmp.close()
                iw = landscape(A4)[0] - 3*cm
                story.append(RLImage(tmp.name, width=iw, height=iw*380/900))
                story.append(Spacer(1, 8))
                os.unlink(tmp.name)
            except Exception:
                pass
    doc.build(story)
    return buf.getvalue()


# ============================================================
# MODULE 1 — DASHBOARD
# ============================================================
def render_dashboard():
    st.markdown("""<div class="main-header">
        <h1>⚡ Electrode Consumption Tracker</h1>
        <p>EAF Operations · Real-time Electrode Management</p>
    </div>""", unsafe_allow_html=True)

    ea = st.session_state.ea_data.copy()
    ds = st.session_state.ds_data.copy()

    if len(ea) == 0 and len(ds) == 0:
        st.info("No data yet. Start by logging electrode additions or entering a daily summary.")
        return

    # ── KPIs ──
    total_kg   = ea["Electrode Wt (Kg)"].sum() if len(ea) > 0 else 0
    total_pcs  = len(ea)
    total_heats = ea["Heat No"].nunique() if len(ea) > 0 else 0

    sp_lm    = ds["Sp Cons on LM (kg/MT)"].replace(0, np.nan).mean() if len(ds) > 0 else 0
    sp_pwr   = ds["Sp Cons on Power (kg/KWh)"].replace(0, np.nan).mean() if len(ds) > 0 else 0
    total_lm = ds["LM Produced EAF (MT)"].sum() if len(ds) > 0 else 0

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.markdown(kpi("Total Electrode Wt", f"{total_kg:,.0f}", "Kg"), unsafe_allow_html=True)
    k2.markdown(kpi("Electrodes Added", f"{total_pcs:,}", "pieces"), unsafe_allow_html=True)
    k3.markdown(kpi("Heats Covered", f"{total_heats:,}", "unique heats"), unsafe_allow_html=True)
    k4.markdown(kpi("LM Produced (EAF)", f"{total_lm:,.0f}", "MT"), unsafe_allow_html=True)
    k5.markdown(kpi("Avg Sp. Cons (LM)", f"{sp_lm:.2f}" if sp_lm else "—", "kg/MT"), unsafe_allow_html=True)
    k6.markdown(kpi("Avg Sp. Cons (Pwr)", f"{sp_pwr:.4f}" if sp_pwr else "—", "kg/KWh"), unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    # ── Chart: Daily electrode weight added ──
    with col1:
        if len(ea) > 0:
            st.markdown('<div class="section-header">📅 Daily Electrode Weight Added</div>',
                        unsafe_allow_html=True)
            daily = ea.groupby(ea["Date"].dt.date)["Electrode Wt (Kg)"].sum().reset_index()
            daily.columns = ["Date", "Electrode Wt (Kg)"]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=daily["Date"], y=daily["Electrode Wt (Kg)"],
                                 marker_color="#0077b6", name="Weight (Kg)"))
            fig.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white",
                               xaxis_title="Date", yaxis_title="Kg", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # ── Chart: Specific consumption trend ──
    with col2:
        if len(ds) > 0:
            st.markdown('<div class="section-header">📈 Specific Consumption Trend (kg/MT)</div>',
                        unsafe_allow_html=True)
            ds_plot = ds[ds["Sp Cons on LM (kg/MT)"] > 0].copy()
            ds_plot["Date"] = pd.to_datetime(ds_plot["Date"])
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=ds_plot["Date"], y=ds_plot["Sp Cons on LM (kg/MT)"],
                                      mode="lines+markers", line=dict(color="#00bcd4", width=2.5),
                                      fill="tozeroy", fillcolor="rgba(0,188,212,0.08)",
                                      name="kg/MT"))
            avg_sp = ds_plot["Sp Cons on LM (kg/MT)"].mean()
            fig2.add_hline(y=avg_sp, line_dash="dot", line_color="#e53935",
                           annotation_text=f"Avg: {avg_sp:.2f}")
            fig2.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white",
                                xaxis_title="Date", yaxis_title="kg/MT", showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    # ── Recent additions table ──
    if len(ea) > 0:
        st.markdown('<div class="section-header">🕐 Recent Electrode Additions</div>',
                    unsafe_allow_html=True)
        recent = ea.sort_values("Date", ascending=False).head(10).copy()
        recent["Date"] = recent["Date"].apply(fmt_date)
        st.dataframe(recent.drop(columns=["Entry ID"]), width="stretch", hide_index=True)

    # ── Column breakdown pie ──
    if len(ea) > 0:
        st.markdown("---")
        pc1, pc2, pc3 = st.columns(3)

        with pc1:
            col_grp = ea.groupby("Column")["Electrode Wt (Kg)"].sum().reset_index()
            fig_pie = go.Figure(go.Pie(labels=col_grp["Column"], values=col_grp["Electrode Wt (Kg)"],
                                        hole=0.45, marker_colors=["#0077b6", "#00bcd4", "#e65100"]))
            fig_pie.update_layout(title="By Column", height=260, paper_bgcolor="white")
            st.plotly_chart(fig_pie, use_container_width=True)

        with pc2:
            make_grp = ea.groupby("Make")["Electrode Wt (Kg)"].sum().reset_index()
            fig_make = go.Figure(go.Pie(labels=make_grp["Make"], values=make_grp["Electrode Wt (Kg)"],
                                         hole=0.45, marker_colors=["#6a1b9a", "#00695c", "#888"]))
            fig_make.update_layout(title="By Make", height=260, paper_bgcolor="white")
            st.plotly_chart(fig_make, use_container_width=True)

        with pc3:
            type_grp = ea.groupby("Type")["Electrode Wt (Kg)"].sum().reset_index()
            fig_type = go.Figure(go.Pie(labels=type_grp["Type"], values=type_grp["Electrode Wt (Kg)"],
                                         hole=0.45, marker_colors=["#1976d2", "#43a047"]))
            fig_type.update_layout(title="By Type", height=260, paper_bgcolor="white")
            st.plotly_chart(fig_type, use_container_width=True)


# ============================================================
# MODULE 2 — LOG ELECTRODE ADDITION
# ============================================================
def render_log_addition():
    st.header("⚡ Log Electrode Addition")

    with st.form("log_addition_form", clear_on_submit=True):
        st.markdown('<div class="section-header">📝 Electrode Details</div>',
                    unsafe_allow_html=True)

        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            entry_date  = st.date_input("Date", value=date.today())
        with r1c2:
            heat_no     = st.text_input("Heat No", placeholder="e.g. 2603J0003")
        with r1c3:
            column      = st.selectbox("Column", COLUMNS_E)

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1:
            elec_id     = st.text_input("Electrode ID", placeholder="e.g. UID8-159055")
        with r2c2:
            elec_wt     = st.number_input("Electrode Weight (Kg)", min_value=0.0,
                                           max_value=2000.0, step=1.0, value=0.0)
        with r2c3:
            make        = st.selectbox("Make", MAKES)
        with r2c4:
            elec_type   = st.selectbox("Type", TYPES)

        remarks = st.text_input("Remarks (optional)", placeholder="Any additional notes")
        submitted = st.form_submit_button("➕ Add Electrode Entry", type="primary", width="stretch")

    if submitted:
        if not heat_no.strip():
            st.error("Heat No is required.")
            return
        if not elec_id.strip():
            st.error("Electrode ID is required.")
            return
        if elec_wt <= 0:
            st.error("Electrode Weight must be greater than 0.")
            return

        ea = st.session_state.ea_data
        total_so_far = ea["Electrode Wt (Kg)"].sum()
        total_cons   = total_so_far + elec_wt

        new_row = {
            "Entry ID":              next_ea_id(),
            "Date":                  pd.Timestamp(entry_date),
            "Heat No":               heat_no.strip().upper(),
            "Column":                column,
            "Electrode ID":          elec_id.strip(),
            "Electrode Wt (Kg)":     elec_wt,
            "Make":                  make,
            "Type":                  elec_type,
            "Total Consumption (Kg)": total_cons,
            "Remarks":               remarks.strip(),
        }

        updated = pd.concat([ea, pd.DataFrame([new_row])], ignore_index=True)
        st.session_state.ea_data = updated
        if save_electrode_additions(updated):
            st.success(f"✅ Entry added — {heat_no} | {column} | {elec_wt:.0f} Kg | Total: {total_cons:,.0f} Kg")
            st.rerun()

    # ── View today's additions ──
    ea = st.session_state.ea_data
    if len(ea) > 0:
        st.markdown("---")
        st.markdown('<div class="section-header">📋 All Electrode Additions</div>',
                    unsafe_allow_html=True)

        # Filter
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_date = st.date_input("Filter by date (optional)", value=None, key="ea_filter_date")
        with fc2:
            f_col  = st.selectbox("Filter by Column", ["All"] + COLUMNS_E, key="ea_filter_col")
        with fc3:
            f_make = st.selectbox("Filter by Make", ["All"] + MAKES, key="ea_filter_make")

        view = ea.copy()
        if f_date:
            view = view[view["Date"].dt.date == f_date]
        if f_col != "All":
            view = view[view["Column"] == f_col]
        if f_make != "All":
            view = view[view["Make"] == f_make]

        view_disp = view.sort_values("Date", ascending=False).copy()
        view_disp["Date"] = view_disp["Date"].apply(fmt_date)
        st.dataframe(view_disp.drop(columns=["Entry ID"]), width="stretch", hide_index=True)
        st.caption(f"Showing {len(view_disp)} entries | Total weight: {view['Electrode Wt (Kg)'].sum():,.0f} Kg")

    # ── Delete entry ──
    if len(ea) > 0:
        st.markdown("---")
        st.markdown('<div class="section-header">🗑️ Delete Entry</div>', unsafe_allow_html=True)
        del_id = st.selectbox("Select Entry ID to delete",
                               options=ea.sort_values("Date", ascending=False)["Entry ID"].tolist(),
                               key="ea_del_id",
                               format_func=lambda x: f"ID {x} — {ea[ea['Entry ID']==x]['Heat No'].values[0]} | "
                                                      f"{ea[ea['Entry ID']==x]['Column'].values[0]} | "
                                                      f"{ea[ea['Entry ID']==x]['Electrode Wt (Kg)'].values[0]:.0f} Kg")
        if st.button("🗑️ Delete Selected Entry", type="secondary"):
            updated = ea[ea["Entry ID"] != del_id].reset_index(drop=True)
            # Recalculate cumulative total
            updated = updated.sort_values("Date").reset_index(drop=True)
            updated["Total Consumption (Kg)"] = updated["Electrode Wt (Kg)"].cumsum()
            st.session_state.ea_data = updated
            if save_electrode_additions(updated):
                st.success("✅ Entry deleted and totals recalculated.")
                st.rerun()


# ============================================================
# MODULE 3 — DAILY SUMMARY
# ============================================================
def render_daily_summary():
    st.header("📅 Daily Summary")

    ds = st.session_state.ds_data

    with st.form("daily_summary_form", clear_on_submit=True):
        st.markdown('<div class="section-header">📝 Enter Daily Summary</div>',
                    unsafe_allow_html=True)

        s_date = st.date_input("Date", value=date.today())

        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            e_cons_mt  = st.number_input("Electrode Cons (MT)", min_value=0.0, step=0.1, format="%.2f")
        with r1c2:
            e_cons_pcs = st.number_input("Electrode Cons (PCs)", min_value=0, step=1)
        with r1c3:
            pwr_cons   = st.number_input("Power Cons (KWh)", min_value=0.0, step=100.0, format="%.0f")

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            lm_eaf     = st.number_input("LM Produced EAF (MT)", min_value=0.0, step=10.0, format="%.1f")
        with r2c2:
            lm_qp      = st.number_input("LM Produced QP (MT)", min_value=0.0, step=10.0, format="%.1f")
        with r2c3:
            remarks    = st.text_input("Remarks", placeholder="SHUTDOWN / notes etc.")

        submitted = st.form_submit_button("💾 Save Daily Summary", type="primary", width="stretch")

    if submitted:
        # Auto-calculate specific consumption
        e_cons_kg = e_cons_mt * 1000.0
        sp_lm     = round(e_cons_kg / lm_eaf, 3)   if lm_eaf  > 0 else 0.0
        sp_pwr    = round(e_cons_kg / pwr_cons, 6)  if pwr_cons > 0 else 0.0

        # Check if date already exists — update if so
        existing = ds[pd.to_datetime(ds["Date"]).dt.date == s_date]
        new_row = {
            "Date":                     pd.Timestamp(s_date),
            "Electrode Cons (MT)":      e_cons_mt,
            "Electrode Cons (PCs)":     e_cons_pcs,
            "Power Cons (KWh)":         pwr_cons,
            "LM Produced EAF (MT)":     lm_eaf,
            "LM Produced QP (MT)":      lm_qp,
            "Sp Cons on LM (kg/MT)":    sp_lm,
            "Sp Cons on Power (kg/KWh)":sp_pwr,
            "Remarks":                  remarks.strip(),
        }

        if len(existing) > 0:
            ds_upd = ds.copy()
            for k, v in new_row.items():
                ds_upd.loc[pd.to_datetime(ds_upd["Date"]).dt.date == s_date, k] = v
            updated = ds_upd
            msg = f"✅ Daily summary for {fmt_date(pd.Timestamp(s_date))} updated."
        else:
            updated = pd.concat([ds, pd.DataFrame([new_row])], ignore_index=True)
            msg = (f"✅ Daily summary saved — Sp Cons: {sp_lm:.2f} kg/MT | "
                   f"{sp_pwr:.4f} kg/KWh")

        updated = updated.sort_values("Date").reset_index(drop=True)
        st.session_state.ds_data = updated
        if save_daily_summary(updated):
            st.success(msg)
            st.rerun()

    # ── View all daily summaries ──
    if len(ds) > 0:
        st.markdown("---")
        st.markdown('<div class="section-header">📋 Daily Summary Register</div>',
                    unsafe_allow_html=True)
        view = ds.sort_values("Date", ascending=False).copy()
        view["Date"] = view["Date"].apply(fmt_date)
        for c in ["Electrode Cons (MT)", "Power Cons (KWh)", "LM Produced EAF (MT)",
                  "LM Produced QP (MT)", "Sp Cons on LM (kg/MT)", "Sp Cons on Power (kg/KWh)"]:
            view[c] = pd.to_numeric(view[c], errors="coerce").round(4)
        st.dataframe(view, width="stretch", hide_index=True)

        # Totals row
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Total Electrode (MT)", f"{ds['Electrode Cons (MT)'].sum():.2f}")
        t2.metric("Total Power (KWh)",    f"{ds['Power Cons (KWh)'].sum():,.0f}")
        t3.metric("Total LM EAF (MT)",    f"{ds['LM Produced EAF (MT)'].sum():,.0f}")
        avg_sp = ds[ds['Sp Cons on LM (kg/MT)'] > 0]['Sp Cons on LM (kg/MT)'].mean()
        t4.metric("Avg Sp Cons (kg/MT)",  f"{avg_sp:.3f}" if avg_sp else "—")


# ============================================================
# MODULE 4 — ANALYTICS
# ============================================================
def render_analytics():
    st.header("📊 Analytics")

    ea = st.session_state.ea_data.copy()
    ds = st.session_state.ds_data.copy()

    if len(ea) == 0 and len(ds) == 0:
        st.warning("No data available for analytics.")
        return

    tab1, tab2, tab3 = st.tabs(["⚡ Electrode Additions", "📅 Daily Performance", "🔥 Heat Analysis"])

    # ── Tab 1: Electrode Additions ──────────────────────────────────────────
    with tab1:
        if len(ea) == 0:
            st.info("No electrode addition data yet.")
        else:
            ea["Date"] = pd.to_datetime(ea["Date"])

            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(kpi("Total Weight", f"{ea['Electrode Wt (Kg)'].sum():,.0f}", "Kg"), unsafe_allow_html=True)
            k2.markdown(kpi("Total Pieces", f"{len(ea):,}", "additions"), unsafe_allow_html=True)
            k3.markdown(kpi("Avg Weight", f"{ea['Electrode Wt (Kg)'].mean():.0f}", "Kg/piece"), unsafe_allow_html=True)
            k4.markdown(kpi("Unique Heats", f"{ea['Heat No'].nunique():,}", "heats"), unsafe_allow_html=True)

            st.markdown("---")
            c1, c2 = st.columns(2)

            with c1:
                # Weight by column
                col_grp = ea.groupby("Column")["Electrode Wt (Kg)"].agg(["sum","count","mean"]).reset_index()
                col_grp.columns = ["Column", "Total (Kg)", "Count", "Avg (Kg)"]
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(x=col_grp["Column"], y=col_grp["Total (Kg)"],
                                      marker_color=["#0077b6","#00bcd4","#e65100"],
                                      text=col_grp["Total (Kg)"].astype(int),
                                      textposition="outside"))
                fig1.update_layout(title="Total Weight by Column", height=320,
                                   plot_bgcolor="white", paper_bgcolor="white", showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)

            with c2:
                # Weight over time line
                daily_wt = ea.groupby(ea["Date"].dt.date)["Electrode Wt (Kg)"].sum().reset_index()
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=daily_wt["Date"], y=daily_wt["Electrode Wt (Kg)"],
                                          mode="lines+markers", line=dict(color="#0077b6", width=2.5),
                                          fill="tozeroy", fillcolor="rgba(0,119,182,0.08)"))
                fig2.update_layout(title="Daily Electrode Weight Added", height=320,
                                   plot_bgcolor="white", paper_bgcolor="white", showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

            c3, c4 = st.columns(2)
            with c3:
                # Per column over time (stacked bar)
                ea["DateOnly"] = ea["Date"].dt.date
                pivot = ea.pivot_table(index="DateOnly", columns="Column",
                                        values="Electrode Wt (Kg)", aggfunc="sum").fillna(0).reset_index()
                fig3 = go.Figure()
                colors_col = {"E1":"#0077b6","E2":"#00bcd4","E3":"#e65100"}
                for col in COLUMNS_E:
                    if col in pivot.columns:
                        fig3.add_trace(go.Bar(x=pivot["DateOnly"], y=pivot[col],
                                              name=col, marker_color=colors_col.get(col, "#aaa")))
                fig3.update_layout(barmode="stack", title="Weight by Column (Daily)",
                                   height=320, plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig3, use_container_width=True)

            with c4:
                # Make comparison
                make_grp = ea.groupby(["Make","Type"])["Electrode Wt (Kg)"].sum().reset_index()
                fig4 = px.bar(make_grp, x="Make", y="Electrode Wt (Kg)", color="Type",
                               barmode="group", title="Weight by Make & Type",
                               color_discrete_map={"SHP":"#0077b6","UHP":"#43a047"})
                fig4.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig4, use_container_width=True)

            # Summary table
            st.markdown('<div class="section-header">📋 Column Summary Table</div>', unsafe_allow_html=True)
            st.dataframe(col_grp.round(2), width="stretch", hide_index=True)

    # ── Tab 2: Daily Performance ─────────────────────────────────────────────
    with tab2:
        if len(ds) == 0:
            st.info("No daily summary data yet.")
        else:
            ds["Date"] = pd.to_datetime(ds["Date"])
            ds_valid   = ds[ds["Sp Cons on LM (kg/MT)"] > 0]

            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(kpi("Total Electrode (MT)", f"{ds['Electrode Cons (MT)'].sum():.2f}", "MT"), unsafe_allow_html=True)
            k2.markdown(kpi("Total Power (KWh)",    f"{ds['Power Cons (KWh)'].sum():,.0f}", "KWh"), unsafe_allow_html=True)
            k3.markdown(kpi("Total LM EAF (MT)",    f"{ds['LM Produced EAF (MT)'].sum():,.0f}", "MT"), unsafe_allow_html=True)
            avg_sp = ds_valid["Sp Cons on LM (kg/MT)"].mean() if len(ds_valid) > 0 else 0
            k4.markdown(kpi("Avg Sp Cons",          f"{avg_sp:.3f}" if avg_sp else "—", "kg/MT"), unsafe_allow_html=True)

            st.markdown("---")
            c1, c2 = st.columns(2)

            with c1:
                # Sp cons LM trend
                fig5 = go.Figure()
                fig5.add_trace(go.Scatter(x=ds_valid["Date"], y=ds_valid["Sp Cons on LM (kg/MT)"],
                                          mode="lines+markers+text",
                                          text=ds_valid["Sp Cons on LM (kg/MT)"].round(2).astype(str),
                                          textposition="top center",
                                          line=dict(color="#0077b6", width=2.5),
                                          name="kg/MT"))
                if avg_sp:
                    fig5.add_hline(y=avg_sp, line_dash="dot", line_color="#e53935",
                                   annotation_text=f"Avg {avg_sp:.2f}")
                fig5.update_layout(title="Sp. Consumption on LM (kg/MT)", height=320,
                                   plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig5, use_container_width=True)

            with c2:
                # Power vs LM dual axis
                fig6 = go.Figure()
                fig6.add_trace(go.Bar(x=ds["Date"], y=ds["Power Cons (KWh)"],
                                      name="Power (KWh)", marker_color="#e0e0e0", opacity=0.8))
                fig6.add_trace(go.Scatter(x=ds["Date"], y=ds["LM Produced EAF (MT)"],
                                          mode="lines+markers", name="LM EAF (MT)",
                                          line=dict(color="#0077b6", width=2), yaxis="y2"))
                fig6.update_layout(
                    title="Power vs LM Produced", height=320,
                    yaxis=dict(title="KWh"),
                    yaxis2=dict(title="MT", overlaying="y", side="right"),
                    plot_bgcolor="white", paper_bgcolor="white"
                )
                st.plotly_chart(fig6, use_container_width=True)

            c3, c4 = st.columns(2)
            with c3:
                # Electrode cons MT trend
                fig7 = px.bar(ds, x="Date", y="Electrode Cons (MT)",
                               color="Electrode Cons (MT)", color_continuous_scale="Blues",
                               title="Daily Electrode Consumption (MT)")
                fig7.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig7, use_container_width=True)

            with c4:
                # Sp cons on power
                ds_pwr = ds[ds["Sp Cons on Power (kg/KWh)"] > 0]
                fig8 = go.Figure()
                fig8.add_trace(go.Scatter(x=ds_pwr["Date"], y=ds_pwr["Sp Cons on Power (kg/KWh)"],
                                          mode="lines+markers", line=dict(color="#43a047", width=2),
                                          name="kg/KWh"))
                fig8.update_layout(title="Sp. Consumption on Power (kg/KWh)", height=300,
                                   plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig8, use_container_width=True)

    # ── Tab 3: Heat Analysis ─────────────────────────────────────────────────
    with tab3:
        if len(ea) == 0:
            st.info("No electrode addition data yet.")
        else:
            ea["Date"] = pd.to_datetime(ea["Date"])
            heat_grp = (ea.groupby("Heat No")
                          .agg(Date=("Date","first"),
                               Total_Wt=("Electrode Wt (Kg)","sum"),
                               Pieces=("Electrode Wt (Kg)","count"),
                               Columns=("Column", lambda x: "/".join(sorted(x.unique()))))
                          .reset_index().sort_values("Date", ascending=False))
            heat_grp.columns = ["Heat No","Date","Total Wt (Kg)","Pieces","Columns Used"]
            heat_grp["Date"] = heat_grp["Date"].apply(fmt_date)

            c1, c2 = st.columns(2)
            with c1:
                fig9 = px.bar(heat_grp.head(20), x="Heat No", y="Total Wt (Kg)",
                               color="Total Wt (Kg)", color_continuous_scale="Blues",
                               title="Top 20 Heats by Electrode Weight")
                fig9.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
                                   xaxis_tickangle=-45)
                st.plotly_chart(fig9, use_container_width=True)

            with c2:
                # Distribution of electrode weights
                fig10 = px.histogram(ea, x="Electrode Wt (Kg)", nbins=20,
                                      color="Column",
                                      color_discrete_map={"E1":"#0077b6","E2":"#00bcd4","E3":"#e65100"},
                                      title="Electrode Weight Distribution by Column")
                fig10.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig10, use_container_width=True)

            st.markdown('<div class="section-header">📋 Heat-wise Summary</div>', unsafe_allow_html=True)
            st.dataframe(heat_grp.round(2), width="stretch", hide_index=True)


# ============================================================
# MODULE 5 — REPORTS
# ============================================================
def _report_filters_ea(key: str, ea: pd.DataFrame):
    st.markdown('<div class="section-header">🔍 Filters</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    dmin = pd.to_datetime(ea["Date"]).min().date()
    dmax = pd.to_datetime(ea["Date"]).max().date()
    with c1: dfrom = st.date_input("From", value=dmin, key=key+"_from")
    with c2: dto   = st.date_input("To",   value=dmax, key=key+"_to")
    with c3: f_col = st.selectbox("Column", ["All"]+COLUMNS_E, key=key+"_col")
    with c4: f_make= st.selectbox("Make",   ["All"]+MAKES,     key=key+"_make")

    out = ea.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out = out[(out["Date"].dt.date >= dfrom) & (out["Date"].dt.date <= dto)]
    if f_col  != "All": out = out[out["Column"] == f_col]
    if f_make != "All": out = out[out["Make"]   == f_make]
    st.caption(f"**{len(out)}** entries after filters")
    return out.reset_index(drop=True)


def render_reports():
    st.header("📋 Reports")
    ea = st.session_state.ea_data.copy()
    ds = st.session_state.ds_data.copy()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    tab1, tab2, tab3 = st.tabs(["⚡ Electrode Additions Report",
                                  "📅 Daily Performance Report",
                                  "📊 Monthly Summary Report"])

    # ── Report 1: Electrode Additions ─────────────────────────────────────
    with tab1:
        if len(ea) == 0:
            st.warning("No electrode addition data.")
        else:
            ddf = _report_filters_ea("r1", ea)
            st.markdown("---")

            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(kpi("Total Weight",  f"{ddf['Electrode Wt (Kg)'].sum():,.0f}", "Kg"), unsafe_allow_html=True)
            k2.markdown(kpi("Total Pieces",  f"{len(ddf):,}", "additions"),                   unsafe_allow_html=True)
            k3.markdown(kpi("Unique Heats",  f"{ddf['Heat No'].nunique():,}", "heats"),        unsafe_allow_html=True)
            k4.markdown(kpi("Avg Wt/Piece",  f"{ddf['Electrode Wt (Kg)'].mean():.0f}", "Kg"), unsafe_allow_html=True)

            col_s = ddf.groupby("Column")["Electrode Wt (Kg)"].agg(["sum","count","mean"]).reset_index()
            col_s.columns = ["Column","Total (Kg)","Count","Avg (Kg)"]

            c1, c2 = st.columns(2)
            with c1:
                fig_a = px.bar(col_s, x="Column", y="Total (Kg)",
                                color="Column", color_discrete_map={"E1":"#0077b6","E2":"#00bcd4","E3":"#e65100"},
                                title="Weight by Column")
                fig_a.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white", showlegend=False)
                st.plotly_chart(fig_a, use_container_width=True)
            with c2:
                daily_w = ddf.groupby(ddf["Date"].dt.date)["Electrode Wt (Kg)"].sum().reset_index()
                fig_b   = go.Figure(go.Bar(x=daily_w["Date"], y=daily_w["Electrode Wt (Kg)"],
                                            marker_color="#0077b6"))
                fig_b.update_layout(title="Daily Weight Added", height=300,
                                    plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig_b, use_container_width=True)

            st.markdown('<div class="section-header">📋 Detail Table</div>', unsafe_allow_html=True)
            tdf = ddf.copy()
            tdf["Date"] = tdf["Date"].apply(fmt_date)
            st.dataframe(tdf.drop(columns=["Entry ID"]).round(2), width="stretch", hide_index=True)

            st.markdown("---")
            ex1, ex2, ex3 = st.columns(3)
            with ex1:
                st.download_button("📥 CSV", data=build_csv(tdf),
                                   file_name=f"Electrode_Additions_{ts}.csv", mime="text/csv", width="stretch")
            with ex2:
                st.download_button("📥 Excel", data=build_excel({"Additions": tdf, "By Column": col_s.round(2)}),
                                   file_name=f"Electrode_Additions_{ts}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   width="stretch")
            with ex3:
                try:
                    pdf = build_pdf("Electrode Additions Report", [
                        {"type":"text", "text": f"Entries: {len(ddf)} | Total: {ddf['Electrode Wt (Kg)'].sum():,.0f} Kg"},
                        {"type":"heading","text":"Weight by Column"},
                        {"type":"fig","fig":fig_a},
                        {"type":"heading","text":"Daily Weight Added"},
                        {"type":"fig","fig":fig_b},
                        {"type":"heading","text":"Detail Table"},
                        {"type":"table","df":tdf.drop(columns=["Entry ID"]).round(2)},
                    ])
                    st.download_button("📄 PDF", data=pdf,
                                       file_name=f"Electrode_Additions_{ts}.pdf",
                                       mime="application/pdf", width="stretch")
                except Exception as e:
                    st.warning(f"PDF needs `kaleido` + `reportlab`. Error: {e}")

    # ── Report 2: Daily Performance ───────────────────────────────────────
    with tab2:
        if len(ds) == 0:
            st.warning("No daily summary data.")
        else:
            ds["Date"] = pd.to_datetime(ds["Date"])
            dc1, dc2 = st.columns(2)
            with dc1: dfrom2 = st.date_input("From", value=ds["Date"].min().date(), key="r2_from")
            with dc2: dto2   = st.date_input("To",   value=ds["Date"].max().date(), key="r2_to")
            ddf2 = ds[(ds["Date"].dt.date >= dfrom2) & (ds["Date"].dt.date <= dto2)]

            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(kpi("Total Electrode", f"{ddf2['Electrode Cons (MT)'].sum():.2f}", "MT"), unsafe_allow_html=True)
            k2.markdown(kpi("Total Power",     f"{ddf2['Power Cons (KWh)'].sum():,.0f}", "KWh"), unsafe_allow_html=True)
            k3.markdown(kpi("Total LM (EAF)",  f"{ddf2['LM Produced EAF (MT)'].sum():,.0f}", "MT"), unsafe_allow_html=True)
            avg2 = ddf2[ddf2["Sp Cons on LM (kg/MT)"]>0]["Sp Cons on LM (kg/MT)"].mean()
            k4.markdown(kpi("Avg Sp Cons", f"{avg2:.3f}" if avg2 else "—", "kg/MT"), unsafe_allow_html=True)

            fig_c = go.Figure()
            fig_c.add_trace(go.Scatter(x=ddf2["Date"],
                                        y=ddf2["Sp Cons on LM (kg/MT)"].replace(0, np.nan),
                                        mode="lines+markers", line=dict(color="#0077b6", width=2.5),
                                        name="Sp Cons (kg/MT)"))
            fig_c.update_layout(title="Sp. Consumption Trend (kg/MT)", height=300,
                                 plot_bgcolor="white", paper_bgcolor="white")

            fig_d = go.Figure()
            fig_d.add_trace(go.Bar(x=ddf2["Date"], y=ddf2["Electrode Cons (MT)"],
                                    marker_color="#0077b6", name="Electrode (MT)"))
            fig_d.update_layout(title="Daily Electrode Consumption (MT)", height=300,
                                 plot_bgcolor="white", paper_bgcolor="white")

            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(fig_c, use_container_width=True)
            with c2: st.plotly_chart(fig_d, use_container_width=True)

            tdf2 = ddf2.copy()
            tdf2["Date"] = tdf2["Date"].apply(fmt_date)
            st.markdown('<div class="section-header">📋 Daily Summary Table</div>', unsafe_allow_html=True)
            st.dataframe(tdf2.round(4), width="stretch", hide_index=True)

            st.markdown("---")
            ex1, ex2, ex3 = st.columns(3)
            with ex1:
                st.download_button("📥 CSV", data=build_csv(tdf2),
                                   file_name=f"Daily_Performance_{ts}.csv", mime="text/csv", width="stretch")
            with ex2:
                st.download_button("📥 Excel", data=build_excel({"Daily Performance": tdf2.round(4)}),
                                   file_name=f"Daily_Performance_{ts}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   width="stretch")
            with ex3:
                try:
                    pdf = build_pdf("Daily Performance Report", [
                        {"type":"fig","fig":fig_c},
                        {"type":"fig","fig":fig_d},
                        {"type":"heading","text":"Daily Summary Table"},
                        {"type":"table","df":tdf2.round(4)},
                    ])
                    st.download_button("📄 PDF", data=pdf,
                                       file_name=f"Daily_Performance_{ts}.pdf",
                                       mime="application/pdf", width="stretch")
                except Exception as e:
                    st.warning(f"PDF needs `kaleido` + `reportlab`. Error: {e}")

    # ── Report 3: Monthly Summary ─────────────────────────────────────────
    with tab3:
        if len(ds) == 0:
            st.warning("No daily summary data.")
        else:
            ds["Date"]  = pd.to_datetime(ds["Date"])
            ds["Month"] = ds["Date"].dt.to_period("M").astype(str)
            monthly = ds.groupby("Month").agg(
                Days         = ("Date","count"),
                Electrode_MT = ("Electrode Cons (MT)","sum"),
                Electrode_Pcs= ("Electrode Cons (PCs)","sum"),
                Power_KWh    = ("Power Cons (KWh)","sum"),
                LM_EAF       = ("LM Produced EAF (MT)","sum"),
                LM_QP        = ("LM Produced QP (MT)","sum"),
            ).reset_index()
            monthly["Sp Cons (kg/MT)"]   = ((monthly["Electrode_MT"]*1000) / monthly["LM_EAF"].replace(0, np.nan)).round(3)
            monthly["Sp Cons (kg/KWh)"]  = ((monthly["Electrode_MT"]*1000) / monthly["Power_KWh"].replace(0, np.nan)).round(6)
            monthly.columns = ["Month","Days","Electrode (MT)","Electrode (PCs)",
                                "Power (KWh)","LM EAF (MT)","LM QP (MT)",
                                "Sp Cons (kg/MT)","Sp Cons (kg/KWh)"]

            fig_m1 = px.bar(monthly, x="Month", y="Electrode (MT)",
                             color="Electrode (MT)", color_continuous_scale="Blues",
                             title="Monthly Electrode Consumption (MT)")
            fig_m1.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white")

            fig_m2 = go.Figure()
            fig_m2.add_trace(go.Bar(x=monthly["Month"], y=monthly["LM EAF (MT)"],
                                     name="LM EAF", marker_color="#0077b6"))
            fig_m2.add_trace(go.Scatter(x=monthly["Month"], y=monthly["Sp Cons (kg/MT)"],
                                         mode="lines+markers", name="Sp Cons (kg/MT)",
                                         line=dict(color="#e53935", width=2), yaxis="y2"))
            fig_m2.update_layout(title="LM Produced vs Sp. Consumption", height=300,
                                  yaxis=dict(title="MT"),
                                  yaxis2=dict(title="kg/MT", overlaying="y", side="right"),
                                  plot_bgcolor="white", paper_bgcolor="white")

            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(fig_m1, use_container_width=True)
            with c2: st.plotly_chart(fig_m2, use_container_width=True)

            st.markdown('<div class="section-header">📋 Monthly Summary Table</div>', unsafe_allow_html=True)
            st.dataframe(monthly.round(4), width="stretch", hide_index=True)

            st.markdown("---")
            ex1, ex2, ex3 = st.columns(3)
            with ex1:
                st.download_button("📥 CSV", data=build_csv(monthly.round(4)),
                                   file_name=f"Monthly_Summary_{ts}.csv", mime="text/csv", width="stretch")
            with ex2:
                st.download_button("📥 Excel", data=build_excel({"Monthly Summary": monthly.round(4)}),
                                   file_name=f"Monthly_Summary_{ts}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   width="stretch")
            with ex3:
                try:
                    pdf = build_pdf("Monthly Summary Report", [
                        {"type":"fig","fig":fig_m1},
                        {"type":"fig","fig":fig_m2},
                        {"type":"heading","text":"Monthly Summary Table"},
                        {"type":"table","df":monthly.round(4)},
                    ])
                    st.download_button("📄 PDF", data=pdf,
                                       file_name=f"Monthly_Summary_{ts}.pdf",
                                       mime="application/pdf", width="stretch")
                except Exception as e:
                    st.warning(f"PDF needs `kaleido` + `reportlab`. Error: {e}")


# ============================================================
# MODULE 6 — DOWNLOAD / IMPORT
# ============================================================
def render_download():
    st.header("💾 Download Data")

    ea = st.session_state.ea_data.copy()
    ds = st.session_state.ds_data.copy()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    st.markdown("""
    <div class="download-card">
        <h3>⚡ Electrode Additions</h3>
        <p>All electrode addition records</p>
    </div>""", unsafe_allow_html=True)
    if len(ea) > 0:
        ea_disp = ea.copy(); ea_disp["Date"] = ea_disp["Date"].apply(fmt_date)
        with st.expander("👁️ Preview", expanded=False):
            st.dataframe(ea_disp.head(10), width="stretch", hide_index=True)
        st.download_button("📥 Download Electrode Additions (CSV)",
                            data=build_csv(ea_disp), file_name=f"ElectrodeAdditions_{ts}.csv",
                            mime="text/csv", width="stretch")
    else:
        st.info("No electrode addition data yet.")

    st.markdown("---")
    st.markdown("""
    <div class="download-card">
        <h3>📅 Daily Summary</h3>
        <p>All daily performance summary records</p>
    </div>""", unsafe_allow_html=True)
    if len(ds) > 0:
        ds_disp = ds.copy(); ds_disp["Date"] = ds_disp["Date"].apply(fmt_date)
        with st.expander("👁️ Preview", expanded=False):
            st.dataframe(ds_disp.head(10), width="stretch", hide_index=True)
        st.download_button("📥 Download Daily Summary (CSV)",
                            data=build_csv(ds_disp), file_name=f"DailySummary_{ts}.csv",
                            mime="text/csv", width="stretch")
    else:
        st.info("No daily summary data yet.")

    st.markdown("---")
    st.header("📤 Import Data")
    st.warning("⚠️ Importing will **replace** existing data for the selected sheet.")

    imp_type = st.radio("Import into:", ["Electrode Additions", "Daily Summary"],
                         label_visibility="collapsed", horizontal=True)
    uploaded = st.file_uploader("Upload CSV", type=["csv"], key="import_upload")
    if uploaded:
        try:
            imp_df = pd.read_csv(uploaded)
            expected = EA_COLS if imp_type == "Electrode Additions" else DS_COLS
            missing  = set(expected) - set(imp_df.columns)
            if missing:
                st.error(f"❌ Missing columns: {missing}")
            else:
                st.success("✅ File validated!")
                st.dataframe(imp_df.head(5), width="stretch", hide_index=True)
                st.info(f"**{len(imp_df)}** records found.")
                if st.button("🔄 Import & Replace", type="primary", width="stretch"):
                    imp_df["Date"] = pd.to_datetime(imp_df["Date"], errors="coerce")
                    if imp_type == "Electrode Additions":
                        st.session_state.ea_data = imp_df
                        save_electrode_additions(imp_df)
                    else:
                        st.session_state.ds_data = imp_df
                        save_daily_summary(imp_df)
                    st.success("✅ Data imported successfully!")
                    st.rerun()
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")


# ============================================================
# SIDEBAR + ROUTER
# ============================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:16px 0 10px 0;">
        <div style="font-size:36px;">⚡</div>
        <div style="font-size:1rem; font-weight:800; color:white; letter-spacing:.5px;">
            Electrode Tracker
        </div>
        <div style="font-size:11px; color:rgba(255,255,255,0.4); margin-top:2px;">
            EAF Operations
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    action = st.radio("Navigation", [
        "🏠 Dashboard",
        "⚡ Log Electrode Addition",
        "📅 Daily Summary",
        "📊 Analytics",
        "📋 Reports",
        "💾 Download / Import",
    ], label_visibility="collapsed")

    st.markdown("---")
    authenticator.logout("Log Out", "sidebar")
    st.markdown(f"**Logged in as:** {st.session_state['name']}")

    st.markdown("---")
    st.markdown("### 🔧 Debug")
    if st.button("🔄 Reload Data", key="reload_btn"):
        st.session_state.ea_data = load_electrode_additions()
        st.session_state.ds_data = load_daily_summary()
        st.success("Data reloaded from Google Sheets.")
        st.rerun()

# ── Route ──
if   action == "🏠 Dashboard":             render_dashboard()
elif action == "⚡ Log Electrode Addition": render_log_addition()
elif action == "📅 Daily Summary":          render_daily_summary()
elif action == "📊 Analytics":              render_analytics()
elif action == "📋 Reports":                render_reports()
elif action == "💾 Download / Import":      render_download()

# ── Footer ──
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#aaa;font-size:12px;padding:4px 0;'>"
    "⚡ Electrode Consumption Tracker &nbsp;|&nbsp; EAF Operations &nbsp;|&nbsp; "
    "Data saved to <code>Google Sheets</code></div>",
    unsafe_allow_html=True
)
