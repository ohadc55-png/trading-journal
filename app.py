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

    /* CUSTOM STYLING FOR THE NEW TRADE BUTTON */
    /* This targets the primary button */
    div.stButton > button[kind="primary"] {
        background: #10B981;
        color: white;
        border-radius: 12px;
        font-size: 20px; /* Adjusted size for text */
        font-weight: 800; /* Bold text */
        height: 60px;
        width: 100%;
        border: none;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.4);
        transition: transform 0.1s;
    }
    div.stButton > button[kind="primary"]:active {
        transform: scale(0.95);
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
# --- HEADER & ACTION BUTTON (MOBILE OPTIMIZED) ---
# ==========================================

# Create two columns: Title on the left, Big "NEW TRADE" Button on the right
# Adjusted ratio to make sure the text fits nicely
col_header, col_btn = st.columns([4, 1], gap="medium")

with col_header:
    st.title("ProTrade Journal")

with col_btn:
    st.write("") # Spacer to align button
    # THIS IS THE BIG GREEN BUTTON WITH TEXT
    if st.button("NEW TRADE", type="primary", use_container_width=True):
        open_trade_modal()

# ==========================================
# --- SIDEBAR (ONLY WALLET SETTINGS) ---
# ==========================================
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    with st.expander("💰 Wallet Management", expanded=True):
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
df = pd.DataFrame(st.session_state.trades)
closed_df = df[df['Status'] == 'Closed'].copy() if not df.empty else pd.DataFrame()

realized_pl = closed_df['Net P&L ($)'].sum() if not closed_df.empty else 0.0
adj_capital = st.session_state.initial_capital + st.session_state.deposits - st.session_state.withdrawals
curr_equity = adj_capital + realized_pl
roi_pct = (realized_pl / adj_capital * 100) if adj_capital > 0 else 0.0

# --- KPI CARD FUNCTION ---
def kpi_card(title, value, is_money=True, color_logic=False, is_percent=False):
    if is_money:
        val_fmt = f"${value:,.2f}"
    elif is_percent:
        val_fmt = f"{value:.2f}%"
    else:
        val_fmt = f"{value}"
        
    color_class = ""
    if color_logic:
        if value > 0: color_class = "text-green"
        elif value < 0: color_class = "text-red"
        
    return f"""
    <div class="metric-card">
        <div class="metric-label">{title}</div>
        <div class="metric-value {color_class}">{val_fmt}</div>
    </div>
    """

# DASHBOARD METRICS
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(kpi_card("Equity", curr_equity), unsafe_allow_html=True)
with c2: st.markdown(kpi_card("Realized P&L", realized_pl, True, True), unsafe_allow_html=True)
with c3: st.markdown(kpi_card("ROI", roi_pct, False, True, True), unsafe_allow_html=True)
with c4: st.markdown(kpi_card("Trades", len(closed_df), False), unsafe_allow_html=True)
st.write("")

# EQUITY CHART
if not closed_df.empty:
    closed_df['Exit Date'] = pd.to_datetime(closed_df['Exit Date'])
    closed_df = closed_df.sort_values(by='Exit Date')
    closed_df['Cumulative P&L'] = closed_df['Net P&L ($)'].cumsum()
    closed_df['Equity Curve'] = adj_capital + closed_df['Cumulative P&L']
    
    chart_data = pd.DataFrame({
        'Date': [pd.to_datetime(st.session_state.trades[0]['Entry Date'])] if not closed_df.empty else [datetime.today()],
        'Equity': [adj_capital]
    })
    final_chart = pd.concat([chart_data, pd.DataFrame({'Date': closed_df['Exit Date'], 'Equity': closed_df['Equity Curve']})])
    
    fig = px.area(final_chart, x='Date', y='Equity', title="Account Growth", markers=True)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#9CA3AF"), height=300)
    fig.update_traces(line_color='#10B981', fillcolor="rgba(16, 185, 129, 0.1)")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# --- TABS: ACTIVE & HISTORY ---
# ==========================================
tab_active, tab_hist = st.tabs(["🟢 Active Trades", "📚 History Log"])

with tab_active:
    open_trades = [t for t in st.session_state.trades if t['Status'] == 'Open']
    if not open_trades:
        st.info("No active trades.")
    else:
        for row in open_trades:
            with st.container():
                st.markdown(f"""
                <div style="background-color: #1F2937; padding: 15px; border-radius: 8px; border-left: 4px solid {'#10B981' if row['Direction'] == 'Long' else '#F87171'}; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 1.2rem; font-weight: bold; color