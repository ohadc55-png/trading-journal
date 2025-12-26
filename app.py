import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# --- CONFIGURATION & PRO UI STYLING ---
# ==========================================
st.set_page_config(page_title="ProTrade Journal", layout="wide", page_icon="🚀")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; font-family: 'Roboto', sans-serif; }
    .metric-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 10px;
    }
    .metric-label { color: #9CA3AF; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; }
    .metric-value { color: #F3F4F6; font-size: 1.8rem; font-weight: 700; }
    .text-green { color: #34D399 !important; }
    .text-red { color: #F87171 !important; }
    
    .trade-container {
        background-color: #111827;
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .history-card {
        background-color: #1F2937;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        border-right: 6px solid #374151;
    }
    .history-win { border-right: 6px solid #34D399; }
    .history-loss { border-right: 6px solid #F87171; }
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

# --- CONSTANTS ---
FUTURE_MULTIPLIERS = {
    "ES (S&P 500)": 50, "MES (Micro S&P)": 5,
    "NQ (Nasdaq 100)": 20, "MNQ (Micro Nasdaq)": 2,
    "GC (Gold)": 100, "CL (Crude Oil)": 1000
}

# ==========================================
# --- MODAL: NEW TRADE ENTRY ---
# ==========================================
@st.dialog("🚀 New Trade Entry")
def open_trade_modal():
    asset_class = st.selectbox("Asset Class", ["Stock", "Future", "Option"])
    symbol = ""
    multiplier = 1.0
    
    if asset_class == "Stock":
        symbol = st.text_input("Ticker Symbol").upper()
    elif asset_class == "Future":
        fut = st.selectbox("Contract", list(FUTURE_MULTIPLIERS.keys()))
        symbol = fut.split(" ")[0]
        multiplier = FUTURE_MULTIPLIERS[fut]
    else: # Option
        und = st.text_input("Underlying").upper()
        o_type = st.selectbox("Type", ["Call", "Put"])
        strike = st.text_input("Strike")
        symbol = f"{und} {o_type} {strike}"
        multiplier = 100.0

    col_main1, col_main2 = st.columns(2)
    with col_main1: direction = st.radio("Direction", ["Long", "Short"], horizontal=True)
    with col_main2: qty = st.number_input("Size / Quantity", min_value=1, value=1)
    
    c_date, c_price = st.columns(2)
    with c_date: entry_date = st.date_input("Entry Date", datetime.today())
    with c_price: entry_price = st.number_input("Entry Price ($)", min_value=0.01, format="%.2f")
    
    reason = st.text_area("Strategy / Notes")
    
    if st.button("Open Position", type="primary", use_container_width=True):
        new_trade = {
            "ID": len(st.session_state.trades) + 1,
            "Asset Class": asset_class,
            "Symbol": symbol,
            "Direction": direction,
            "Entry Date": entry_date.strftime("%Y-%m-%d"),
            "Entry Price": entry_price,
            "Original Qty": qty,
            "Remaining Qty": qty,
            "Multiplier": multiplier,
            "Exits": [],
            "Total Realized P&L": 0.0,
            "Status": "Open",
            "Reason": reason
        }
        st.session_state.trades.append(new_trade)
        st.rerun()

# ==========================================
# --- SIDEBAR & CALCULATIONS ---
# ==========================================
with st.sidebar:
    st.title("⚙️ Controls")
    if st.button("➕ NEW TRADE", type="primary", use_container_width=True):
        open_trade_modal()
    st.markdown("---")
    st.session_state.initial_capital = st.number_input("Account Start ($)", value=st.session_state.initial_capital)
    if st.button("⚠️ CLEAR ALL DATA"):
        st.session_state.trades = []
        st.rerun()

total_realized_pl = sum(t.get('Total Realized P&L', 0.0) for t in st.session_state.trades)
adj_capital = st.session_state.initial_capital + st.session_state.deposits - st.session_state.withdrawals
curr_equity = adj_capital + total_realized_pl
roi_pct = (total_realized_pl / adj_capital * 100) if adj_capital > 0 else 0.0

# ==========================================
# --- DASHBOARD ---
# ==========================================
def kpi_card(title, value, is_money=True, color_logic=False, is_percent=False):
    color_class = ""
    if color_logic:
        if value > 0: color_class = "text-green"
        elif value < 0: color_class = "text-red"
    val_fmt = f"${value:,.2f}" if is_money else (f"{value:+.2f}%" if is_percent else str(value))
    return f'<div class="metric-card"><div class="metric-label">{title}</div><div class="metric-value {color_class}">{val_fmt}</div></div>'

st.markdown("## 📊 Portfolio Dashboard")
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(kpi_card("Current Equity", curr_equity), unsafe_allow_html=True)
with c2: st.markdown(kpi_card("Total Realized P&L", total_realized_pl, True, True), unsafe_allow_html=True)
with c3: st.markdown(kpi_card("Account ROI", roi_pct, False, True, True), unsafe_allow_html=True)
with c4: 
    open_count = len([t for t in st.session_state.trades if t.get('Status') == 'Open'])
    st.markdown(kpi_card("Open Trades", open_count, False), unsafe_allow_html=True)

# ==========================================
# --- MAIN TABS ---
# ==========================================
st.markdown("---")
tab_active, tab_history = st.tabs(["📂 Active Trades", "📜 History"])

# --- ACTIVE TRADES ---
with tab_active:
    open_trades = [t for t in st.session_state.trades if t.get('Status') == 'Open']
    if not open_trades:
        st.info("No active trades.")
    else:
        for i, trade in enumerate(st.session_state.trades):
            if trade.get('Status') == 'Open':
                st.markdown(f'<div class="trade-container"><b>{trade.get("Symbol")}</b> ({trade.get("Direction")}) | Entry: ${trade.get("Entry Price")}</div>', unsafe_allow_html=True)
                with st.expander(f"Manage {trade.get('Symbol')}"):
                    c_q, c_p, c_c = st.columns(3)
                    rem = trade.get('Remaining Qty', 0)
                    sq = c_q.number_input("Qty to Sell", 1, max(1, rem), key=f"q_{i}")
                    sp = c_p.number_input("Exit Price", 0.0, key=f"p_{i}")
                    sc = c_c.number_input("Comm ($)", 0.0, key=f"c_{i}")
                    if st.button("Close Partial", key=f"b_{i}"):
                        mult = trade.get('Multiplier', 1.0)
                        pnl = ((sp - trade['Entry Price']) if trade['Direction'] == "Long" else (trade['Entry Price'] - sp)) * sq * mult - sc
                        trade.setdefault('Exits', []).append({"qty": sq, "price": sp, "pnl": pnl, "date": datetime.now().strftime("%Y-%m-%d")})
                        trade['Remaining Qty'] -= sq
                        trade['Total Realized P&L'] = trade.get('Total Realized P&L', 0.0) + pnl
                        if trade['Remaining Qty'] <= 0: trade['Status'] = "Closed"
                        st.rerun()

# --- HISTORY ---
with tab_history:
    closed_trades = [t for t in st.session_state.trades if t.get('Status') == 'Closed']
    if not closed_trades:
        st.write("History is empty.")
    else:
        # חלוקה לפי סוגי נכסים
        h_stocks, h_futures, h_options = st.tabs(["📈 Stocks", "⛓️ Futures", "🎭 Options"])
        
        asset_map = {"Stock": h_stocks, "Future": h_futures, "Option": h_options}
        
        for a_type, tab_obj in asset_map.items():
            with tab_obj:
                type_trades = [t for t in closed_trades if t.get('Asset Class') == a_type]
                if not type_trades:
                    st.write(f"No {a_type} history yet.")
                else:
                    for t in type_trades:
                        pnl = t.get('Total Realized P&L', 0.0)
                        # חישוב אחוז רווח סופי
                        entry_val = t.get('Original Qty', 1) * t.get('Entry Price', 1) * t.get('Multiplier', 1)
                        pct = (pnl / entry_val * 100) if entry_val > 0 else 0.0
                        
                        status_class = "history-win" if pnl >= 0 else "history-loss"
                        color_text = "text-green" if pnl >= 0 else "text-red"
                        
                        st.markdown(f"""
                        <div class="history-card {status_class}">
                            <div style="display: flex; justify-content: space-between;">
                                <div>
                                    <b style="font-size: 1.1rem;">{t.get('Symbol')}</b> ({t.get('Direction')})<br>
                                    <small style="color: #9CA3AF;">Entry: ${t.get('Entry Price')} | Qty: {t.get('Original Qty')}</small>
                                </div>
                                <div style="text-align: right;">
                                    <span class="{color_text}" style="font-weight: bold; font-size: 1.1rem;">
                                        {"+" if pnl >= 0 else ""}{pnl:,.2f}$
                                    </span><br>
                                    <small class="{color_text}">{pct:+.2f}%</small>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
