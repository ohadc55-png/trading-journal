import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==========================================
# --- CONFIGURATION & PRO UI STYLING ---
# ==========================================
st.set_page_config(page_title="ProTrade Journal", layout="wide", page_icon="🚀")

# CUSTOM CSS
st.markdown("""
<style>
    /* GLOBAL FONTS & COLORS */
    .stApp {
        background-color: #0E1117;
        font-family: 'Roboto', 'Helvetica Neue', sans-serif;
    }
    
    /* METRIC CARDS */
    .metric-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-label {
        color: #9CA3AF;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .metric-value {
        color: #F3F4F6;
        font-size: 2rem;
        font-weight: 700;
    }
    
    /* COLORS */
    .text-green { color: #34D399 !important; }
    .text-red { color: #F87171 !important; }
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; border: none; color: #6B7280; }
    .stTabs [aria-selected="true"] { color: #10B981 !important; border-bottom: 2px solid #10B981; }
    
    /* DATAFRAME HEADER */
    th { background-color: #111827 !important; color: #9CA3AF !important; }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZE STATE ---
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'initial_capital' not in st.session_state:
    st.session_state.initial_capital = 10000.0
if 'deposits' not in st.session_state:
    st.session_state.deposits = 0.0
if 'withdrawals' not in st.session_state:
    st.session_state.withdrawals = 0.0

# --- MULTIPLIERS ---
FUTURE_MULTIPLIERS = {
    "ES (S&P 500)": 50, "MES (Micro S&P)": 5,
    "NQ (Nasdaq 100)": 20, "MNQ (Micro Nasdaq)": 2,
    "RTY (Russell 2000)": 50, "M2K (Micro Russell)": 5,
    "GC (Gold)": 100, "MGC (Micro Gold)": 10,
    "CL (Crude Oil)": 1000, "SI (Silver)": 1000, "SIL (Micro Silver)": 100
}

# ==========================================
# --- MODAL: NEW TRADE ENTRY ---
# ==========================================
@st.dialog("🚀 New Trade Entry")
def open_trade_modal():
    asset_class = st.selectbox("Asset Class", ["Stock", "Future", "Option"])
    
    symbol = ""
    multiplier = 1.0
    details = ""
    
    if asset_class == "Stock":
        symbol = st.text_input("Ticker Symbol").upper()
        details = "Stock"
    elif asset_class == "Future":
        fut = st.selectbox("Contract", list(FUTURE_MULTIPLIERS.keys()))
        symbol = fut.split(" ")[0]
        multiplier = FUTURE_MULTIPLIERS[fut]
        details = "Future"
    else: # Option
        c1, c2 = st.columns(2)
        with c1: und = st.text_input("Underlying").upper()
        with c2: o_type = st.selectbox("Type", ["Call", "Put"])
        c3, c4 = st.columns(2)
        with c3: strike = st.text_input("Strike")
        with c4: exp = st.date_input("Expiry")
        symbol = f"{und} {o_type} {strike}"
        multiplier = 100.0
        details = f"{o_type} {strike} {exp}"

    st.write("")
    col_main1, col_main2 = st.columns(2)
    with col_main1: direction = st.radio("Direction", ["Long", "Short"], horizontal=True)
    with col_main2: qty = st.number_input("Size / Quantity", min_value=1, value=1)
    
    # Entry Date & Price
    c_date, c_price = st.columns(2)
    with c_date: entry_date = st.date_input("Entry Date", datetime.today())
    with c_price: entry_price = st.number_input("Entry Price ($)", min_value=0.0, format="%.2f")
    
    with st.expander("Risk Management (Optional)"):
        c_risk1, c_risk2 = st.columns(2)
        with c_risk1: stop_loss = st.number_input("Stop Loss", min_value=0.0, format="%.2f")
        with c_risk2: target = st.number_input("Target", min_value=0.0, format="%.2f")
    
    reason = st.text_area("Strategy", placeholder="Reason for trade...")
    
    if st.button("Submit Trade", type="primary", use_container_width=True):
        new_trade = {
            "ID": len(st.session_state.trades) + 1, "Asset Class": asset_class, "Symbol": symbol,
            "Details": details, "Direction": direction, 
            "Entry Date": entry_date.strftime("%Y-%m-%d"), 
            "Entry Price": entry_price, "Quantity": qty, "Multiplier": multiplier,
            "Stop Loss": stop_loss, "Target": target, "Reason": reason,
            "Status": "Open", "Exit Date": None, "Exit Price": 0.0,
            "Commissions": 0.0, "Net P&L ($)": 0.0, "Net P&L (%)": 0.0
        }
        st.session_state.trades.append(new_trade)
        st.success("Trade Executed!")
        st.rerun()

# ==========================================
# --- SIDEBAR ---
# ==========================================
with st.sidebar:
    st.markdown("## ⚙️ Controls")
    if st.button("➕ NEW TRADE", type="primary", use_container_width=True):
        open_trade_modal()
    st.markdown("---")
    with st.expander("💰 Wallet"):
        st.session_state.initial_capital = st.number_input("Initial Balance", value=st.session_state.initial_capital)
        d = st.number_input("Deposit", min_value=0.0, step=100.0)
        w = st.number_input("Withdraw", min_value=0.0, step=100.0)
        if st.button("Update"):
            st.session_state.deposits += d
            st.session_state.withdrawals += w
            st.rerun()

# ==========================================
# --- MAIN LOGIC ---
# ==========================================
# #region agent log
import json
import os
log_path = os.path.join(os.path.dirname(__file__), ".cursor", "debug.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
def log_debug(location, message, data, hypothesis_id, run_id="run1"):
    try:
        import time
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"location": location, "message": message, "data": data, "hypothesisId": hypothesis_id, "runId": run_id, "sessionId": "debug-session", "timestamp": int(time.time() * 1000)}) + "\n")
    except Exception as e:
        pass
# #endregion

df = pd.DataFrame(st.session_state.trades)
log_debug("app.py:164", "DataFrame created", {"df_empty": df.empty, "df_columns": list(df.columns) if not df.empty else [], "trades_count": len(st.session_state.trades)}, "D")

try:
    closed_df = df[df['Status'] == 'Closed'].copy() if not df.empty and 'Status' in df.columns else pd.DataFrame()
    log_debug("app.py:167", "Closed DataFrame filtered", {"closed_df_empty": closed_df.empty, "has_status_col": 'Status' in df.columns if not df.empty else False}, "B")
except Exception as e:
    log_debug("app.py:167", "Closed DataFrame filter error", {"error": str(e), "error_type": str(type(e))}, "B")
    closed_df = pd.DataFrame()

try:
    if not closed_df.empty and 'Net P&L ($)' in closed_df.columns:
        realized_pl = closed_df['Net P&L ($)'].sum()
        if pd.isna(realized_pl):
            realized_pl = 0.0
    else:
        realized_pl = 0.0
    log_debug("app.py:170", "Realized P&L calculated", {"realized_pl": realized_pl, "realized_pl_type": str(type(realized_pl)), "is_nan": bool(pd.isna(realized_pl))}, "C")
except Exception as e:
    log_debug("app.py:170", "Realized P&L calculation error", {"error": str(e), "error_type": str(type(e))}, "C")
    realized_pl = 0.0

adj_capital = st.session_state.initial_capital + st.session_state.deposits - st.session_state.withdrawals
curr_equity = adj_capital + realized_pl
log_debug("app.py:158-159", "Capital calculations", {"adj_capital": adj_capital, "curr_equity": curr_equity, "curr_equity_type": str(type(curr_equity))}, "A")

try:
    roi_pct = (realized_pl / adj_capital * 100) if adj_capital > 0 else 0.0
    if pd.isna(roi_pct):
        roi_pct = 0.0
    log_debug("app.py:177", "ROI calculated", {"roi_pct": roi_pct, "roi_pct_type": str(type(roi_pct)), "is_nan": bool(pd.isna(roi_pct))}, "C")
except Exception as e:
    log_debug("app.py:177", "ROI calculation error", {"error": str(e), "error_type": str(type(e))}, "C")
    roi_pct = 0.0

# --- FIXED KPI CARD FUNCTION (BUG FIX) ---
def kpi_card(title, value, is_money=True, color_logic=False, is_percent=False):
    # #region agent log
    is_nan_val = False
    try:
        if isinstance(value, (int, float)):
            is_nan_val = bool(pd.isna(value))
    except:
        pass
    log_debug("app.py:181", "kpi_card called", {"title": title, "value": value, "value_type": str(type(value)), "is_money": is_money, "color_logic": color_logic, "is_percent": is_percent, "is_nan": is_nan_val}, "A")
    # #endregion
    
    # Formatting
    # #region agent log
    log_debug("app.py:165", "Before formatting", {"value": value, "is_money": is_money, "is_percent": is_percent}, "A")
    # #endregion
    
    try:
        if is_money:
            val_fmt = f"${value:,.2f}"
        elif is_percent:
            val_fmt = f"{value:.2f}%"
        else:
            val_fmt = f"{value}"
    except Exception as e:
        # #region agent log
        log_debug("app.py:166-170", "Formatting error", {"error": str(e), "error_type": str(type(e)), "value": value, "value_type": str(type(value))}, "A")
        # #endregion
        val_fmt = str(value)
        
    # #region agent log
    log_debug("app.py:171", "After formatting", {"val_fmt": val_fmt}, "A")
    # #endregion
    
    # Color Logic (safe for numbers)
    color_class = ""
    if color_logic:
        # #region agent log
        log_debug("app.py:175", "Before color logic", {"value": value, "value_type": str(type(value))}, "E")
        # #endregion
        try:
            if value > 0: color_class = "text-green"
            elif value < 0: color_class = "text-red"
        except Exception as e:
            # #region agent log
            log_debug("app.py:176-177", "Color logic error", {"error": str(e), "error_type": str(type(e)), "value": value}, "E")
            # #endregion
        # #region agent log
        log_debug("app.py:178", "After color logic", {"color_class": color_class}, "E")
        # #endregion
        
    return f"""
    <div class="metric-card">
        <div class="metric-label">{title}</div>
        <div class="metric-value {color_class}">{val_fmt}</div>
    </div>
    """

st.markdown("### 📊 Dashboard")
c1, c2, c3, c4 = st.columns(4)

# #region agent log
log_debug("app.py:186", "Before dashboard rendering", {"curr_equity": curr_equity, "realized_pl": realized_pl, "roi_pct": roi_pct}, "A")
# #endregion

try:
    with c1: st.markdown(kpi_card("Equity", curr_equity), unsafe_allow_html=True)
except Exception as e:
    # #region agent log
    log_debug("app.py:187", "Equity card error", {"error": str(e), "error_type": str(type(e)), "curr_equity": curr_equity}, "A")
    # #endregion
    with c1: st.error(f"Error displaying Equity: {e}")

try:
    with c2: st.markdown(kpi_card("Realized P&L", realized_pl, True, True), unsafe_allow_html=True)
except Exception as e:
    # #region agent log
    log_debug("app.py:188", "Realized P&L card error", {"error": str(e), "error_type": str(type(e)), "realized_pl": realized_pl}, "A")
    # #endregion
    with c2: st.error(f"Error displaying Realized P&L: {e}")

try:
    with c3: st.markdown(kpi_card("ROI", roi_pct, False, True, True), unsafe_allow_html=True) # Fixed call
except Exception as e:
    # #region agent log
    log_debug("app.py:189", "ROI card error", {"error": str(e), "error_type": str(type(e)), "roi_pct": roi_pct}, "A")
    # #endregion
    with c3: st.error(f"Error displaying ROI: {e}")

try:
    if not df.empty and 'Status' in df.columns:
        open_trades_count = len(df[df['Status'] == 'Open'])
    else:
        open_trades_count = 0
    # #region agent log
    log_debug("app.py:264", "Open trades count", {"open_trades_count": open_trades_count, "has_status_col": 'Status' in df.columns if not df.empty else False}, "B")
    # #endregion
    with c4: st.markdown(kpi_card("Open Trades", open_trades_count), unsafe_allow_html=True)
except Exception as e:
    # #region agent log
    log_debug("app.py:264", "Open Trades card error", {"error": str(e), "error_type": str(type(e))}, "B")
    # #endregion
    with c4: st.error(f"Error displaying Open Trades: {e}")
