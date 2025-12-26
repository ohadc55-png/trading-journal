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
            "Symbol": symbol,
            "Direction": direction,
            "Entry Date": entry_date.strftime("%Y-%m-%d"),
            "Entry Price": entry_price,
            "Original Qty": qty,
            "Remaining Qty": qty,
            "Multiplier": multiplier,
            "Exits": [],  # List of partial sales
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

# Calculation Logic
total_realized_pl = sum(t['Total Realized P&L'] for t in st.session_state.trades)
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
    return f"""
    <div class="metric-card">
        <div class="metric-label">{title}</div>
        <div class="metric-value {color_class}">{val_fmt}</div>
    </div>
    """

st.markdown("## 📊 Portfolio Dashboard")
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(kpi_card("Current Equity", curr_equity), unsafe_allow_html=True)
with c2: st.markdown(kpi_card("Total Realized P&L", total_realized_pl, True, True), unsafe_allow_html=True)
with c3: st.markdown(kpi_card("Account ROI", roi_pct, False, True, True), unsafe_allow_html=True)
with c4: 
    open_count = len([t for t in st.session_state.trades if t['Status'] == 'Open'])
    st.markdown(kpi_card("Open Trades", open_count, False), unsafe_allow_html=True)

# ==========================================
# --- TRADES MANAGEMENT ---
# ==========================================
st.markdown("---")
tab1, tab2 = st.tabs(["📂 Active Trades", "📜 History"])

with tab1:
    open_trades = [t for t in st.session_state.trades if t['Status'] == 'Open']
    if not open_trades:
        st.info("No active trades. Click 'New Trade' to start.")
    
    for i, trade in enumerate(st.session_state.trades):
        if trade['Status'] == 'Open':
            with st.container():
                # Trade Header
                st.markdown(f"""
                <div class="trade-container">
                    <h4 style='margin:0;'>{trade['Symbol']} ({trade['Direction']})</h4>
                    <small>Entry: ${trade['Entry Price']} | Rem. Qty: {trade['Remaining Qty']} / {trade['Original Qty']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                exp = st.expander(f"Manage Trade - {trade['Symbol']}")
                with exp:
                    col_ex1, col_ex2, col_ex3 = st.columns(3)
                    sell_qty = col_ex1.number_input("Qty to Sell", min_value=1, max_value=trade['Remaining Qty'], key=f"q_{i}")
                    sell_price = col_ex2.number_input("Exit Price", min_value=0.0, key=f"p_{i}")
                    sell_comm = col_ex3.number_input("Commission ($)", min_value=0.0, key=f"c_{i}")
                    
                    if st.button("Execute Partial Sale", key=f"btn_{i}", use_container_width=True):
                        # Calculate P&L for this slice
                        multiplier = trade['Multiplier']
                        if trade['Direction'] == "Long":
                            part_pnl = (sell_price - trade['Entry Price']) * sell_qty * multiplier
                        else:
                            part_pnl = (trade['Entry Price'] - sell_price) * sell_qty * multiplier
                        
                        net_part_pnl = part_pnl - sell_comm
                        
                        # Update Trade Data
                        trade['Exits'].append({
                            "qty": sell_qty, "price": sell_price, "pnl": net_part_pnl, "date": datetime.now().strftime("%Y-%m-%d")
                        })
                        trade['Remaining Qty'] -= sell_qty
                        trade['Total Realized P&L'] += net_part_pnl
                        
                        if trade['Remaining Qty'] == 0:
                            trade['Status'] = "Closed"
                        
                        st.success(f"Sold {sell_qty} units. P&L: ${net_part_pnl:,.2f}")
                        st.rerun()

                # Display Cumulative P&L for this trade
                if trade['Exits']:
                    sold_qty = sum(e['qty'] for e in trade['Exits'])
                    entry_value = sold_qty * trade['Entry Price'] * trade['Multiplier']
                    trade_pnl_pct = (trade['Total Realized P&L'] / entry_value * 100) if entry_value > 0 else 0.0
                    
                    color = "#34D399" if trade['Total Realized P&L'] >= 0 else "#F87171"
                    st.markdown(f"""
                        <div style="padding-left: 20px; border-left: 3px solid {color}; margin-bottom: 20px;">
                            <span style="color: {color}; font-weight: bold;">
                                Realized so far: ${trade['Total Realized P&L']:,.2f} ({trade_pnl_pct:+.2f}%)
                            </span>
                        </div>
                    """, unsafe_allow_html=True)

with tab2:
    closed_trades = [t for t in st.session_state.trades if t['Status'] == 'Closed']
    if closed_trades:
        history_df = pd.DataFrame(closed_trades)
        st.dataframe(history_df[['Symbol', 'Direction', 'Entry Price', 'Original Qty', 'Total Realized P&L']], use_container_width=True)
    else:
        st.write("History is empty.")

