import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# --- CONFIGURATION & CUSTOM CSS (UX/UI) ---
# ==========================================
st.set_page_config(page_title="Pro Trader Dashboard", layout="wide", page_icon="📈", initial_sidebar_state="collapsed")

# INJECT CUSTOM CSS FOR PROFESSIONAL FINANCIAL LOOK
st.markdown("""
<style>
    /* Force Dark Theme feel and professional font styles */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Style headers */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 600;
        color: #E0E0E0;
    }

    /* Custom Styling for Metric Cards to look like the reference image */
    div[data-testid="stMetric"] {
        background-color: #262730; /* Slightly lighter dark card background */
        border: 1px solid #363945;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        text-align: center;
    }
    
    /* Style the metric labels and values */
    div[data-testid="stMetricLabel"] {
        font-size: 1rem;
        color: #A0A0A0;
        font-weight: 500;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #FFFFFF;
    }

    /* Style Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1E1E24;
        border-radius: 5px 5px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        border: 1px solid #363945;
        color: #A0A0A0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #262730 !important;
        color: #FFFFFF !important;
        border-bottom: 2px solid #00C897 !important; /* Green accent for active tab */
    }

    /* Expander Styling (for New Trade button) */
    .streamlit-expanderHeader {
        background-color: #262730;
        border: 1px solid #363945;
        border-radius: 5px;
        color: #FFFFFF;
        font-weight: 600;
    }
    
    /* DataFrame Styling */
    [data-testid="stDataFrame"] {
        border: 1px solid #363945;
        border-radius: 5px;
    }

</style>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'initial_capital' not in st.session_state:
    st.session_state.initial_capital = 10000.0
if 'deposits' not in st.session_state:
    st.session_state.deposits = 0.0
if 'withdrawals' not in st.session_state:
    st.session_state.withdrawals = 0.0

# --- MULTIPLIER DICTIONARY ---
FUTURE_MULTIPLIERS = {
    "ES (E-mini S&P 500)": 50, "MES (Micro S&P 500)": 5,
    "NQ (E-mini NASDAQ 100)": 20, "MNQ (Micro NASDAQ 100)": 2,
    "RTY (E-mini Russell 2000)": 50, "M2K (Micro Russell 2000)": 5,
    "GC (Gold)": 100, "MGC (Micro Gold)": 10,
    "SI (Silver)": 1000, "SIL (Micro Silver)": 100, "CL (Crude Oil)": 1000
}

# ==========================================
# --- SIDEBAR (Hidden by default, used for settings) ---
# ==========================================
with st.sidebar:
    st.header("⚙️ Settings & Funds")
    st.session_state.initial_capital = st.number_input("Initial Capital Setup ($)", value=st.session_state.initial_capital, step=1000.0)
    st.markdown("---")
    st.subheader("Manage Cash Flow")
    new_deposit = st.number_input("Deposit (+)", min_value=0.0, step=100.0)
    if st.button("Confirm Deposit"):
        st.session_state.deposits += new_deposit
        st.success(f"Deposited ${new_deposit:,.2f}")

    new_withdrawal = st.number_input("Withdraw (-)", min_value=0.0, step=100.0)
    if st.button("Confirm Withdrawal"):
        st.session_state.withdrawals += new_withdrawal
        st.success(f"Withdrew ${new_withdrawal:,.2f}")

# ==========================================
# --- CALCULATIONS ---
# ==========================================
df = pd.DataFrame(st.session_state.trades)
total_realized_pl = df[df['Status'] == 'Closed']['Net P&L ($)'].sum() if not df.empty else 0.0

# Adjusted Capital = Initial + Deposits - Withdrawals
adjusted_capital = st.session_state.initial_capital + st.session_state.deposits - st.session_state.withdrawals

# Current Equity = Adjusted Capital + Realized P&L
current_equity = adjusted_capital + total_realized_pl

# Total Return % based on Adjusted Capital
total_return_pct = (total_realized_pl / adjusted_capital * 100) if adjusted_capital > 0 else 0.0

# ==========================================
# --- MAIN DASHBOARD UI ---
# ==========================================
st.title("Multi-Asset Trading Journal")

# 1. THE "NEW TRADE" BUTTON (TOP EXPANDER)
with st.expander("➕ New Trade Entry", expanded=False):
    st.markdown("### Enter Trade Details")
    # --- ASSET CLASS SELECTION ---
    asset_class = st.radio("Select Asset Class:", ["Stock", "Future", "Option"], horizontal=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if asset_class == "Stock":
            symbol = st.text_input("Ticker Symbol (e.g., AAPL)").upper()
            multiplier = 1.0
            qty_label = "Shares"
            details = "Stock"
        elif asset_class == "Future":
            future_name = st.selectbox("Select Contract", list(FUTURE_MULTIPLIERS.keys()))
            symbol = future_name.split(" ")[0]
            multiplier = FUTURE_MULTIPLIERS[future_name]
            qty_label = "Contracts"
            details = f"Future ({multiplier}$/pt)"
        else: # Option
            underlying = st.text_input("Underlying (e.g., SPY)").upper()
            opt_type = st.selectbox("Type", ["Call", "Put"])
            strike = st.number_input("Strike", step=1.0)
            exp_date = st.date_input("Expiry")
            symbol = f"{underlying} {exp_date.strftime('%d%b%y')} {strike}{opt_type[0]}"
            multiplier = 100.0
            qty_label = "Contracts"
            details = f"{opt_type} {strike} Exp: {exp_date}"
            underlying_target = st.number_input("Underlying Target (Opt.)", min_value=0.0, step=0.1)

    with col2:
        direction = st.radio("Direction", ["Long", "Short"], horizontal=True)
        quantity = st.number_input(f"Quantity ({qty_label})", min_value=1, step=1)
        entry_date = st.date_input("Entry Date", datetime.today())
        
    with col3:
        if asset_class == "Option":
            entry_price = st.number_input("Premium (per contract)", min_value=0.0, step=0.05, format="%.2f")
        else:
            entry_price = st.number_input("Entry Price", min_value=0.0, step=0.25, format="%.2f")
        stop_loss = st.number_input("Initial Stop Loss", min_value=0.0, step=0.25)
        target_price = st.number_input("Target Price", min_value=0.0, step=0.25)

    reason = st.text_area("Trade Strategy / Thesis")
    
    if st.button("Submit Trade", type="primary"):
        new_trade = {
            "ID": len(st.session_state.trades) + 1, "Asset Class": asset_class, "Symbol": symbol,
            "Details": details, "Direction": direction, "Entry Date": entry_date.strftime("%Y-%m-%d"),
            "Entry Price": entry_price, "Quantity": quantity, "Multiplier": multiplier,
            "Stop Loss": stop_loss, "Target": target_price, "Reason": reason,
            "Status": "Open", "Exit Date": None, "Exit Price": 0.0,
            "Commissions": 0.0, "Net P&L ($)": 0.0, "Net P&L (%)": 0.0, "Management Notes": ""
        }
        st.session_state.trades.append(new_trade)
        st.success("Trade Submitted Successfully!")
        st.rerun()

st.markdown("---")

# 2. THE ACCOUNT DASHBOARD CARDS
st.subheader("Account Summary")
met_c1, met_c2, met_c3, met_c4 = st.columns(4)
with met_c1:
    st.metric("Adjusted Capital (Start + Dep - W/D)", f"${adjusted_capital:,.2f}")
with met_c2:
    st.metric("Current Equity", f"${current_equity:,.2f}")
with met_c3:
    st.metric("Total Realized P&L", f"${total_realized_pl:,.2f}", delta=f"{total_realized_pl:,.2f}", delta_color="normal")
with met_c4:
    st.metric("Total Return %", f"{total_return_pct:.2f}%", delta=f"{total_return_pct:.2f}%", delta_color="normal")

st.markdown("---")

# ==========================================
# --- MAIN TABS LAYOUT ---
# ==========================================
tab_active, tab_history = st.tabs(["🔥 Active Positions", "📊 Trade History & Analytics"])

# -------------------------------------------
# TAB 1: ACTIVE POSITIONS
# -------------------------------------------
with tab_active:
    active_trades = [t for t in st.session_state.trades if t['Status'] == 'Open']
    if not active_trades:
        st.info("No active positions. Click 'New Trade Entry' above to start.")
    else:
        df_active = pd.DataFrame(active_trades)
        active_classes = df_active['Asset Class'].unique()
        
        # Function for close trade form
        def display_close_form(trade_row):
            with st.expander(f"🔴 Close: {trade_row['Symbol']} ({trade_row['Direction']})"):
                c_ex1, c_ex2 = st.columns(2)
                with c_ex1:
                    exit_price = st.number_input(f"Exit Price", key=f"ep_{trade_row['ID']}", step=0.1)
                    exit_date = st.date_input(f"Exit Date", datetime.today(), key=f"ed_{trade_row['ID']}")
                with c_ex2:
                    commissions = st.number_input("Total Commissions ($)", min_value=0.0, step=1.0, key=f"cm_{trade_row['ID']}")
                    mgt_notes = st.text_area("Exit / Management Notes", key=f"mn_{trade_row['ID']}")
                
                if st.button(f"Confirm Close Transaction", key=f"btn_{trade_row['ID']}", type="secondary"):
                    mult = trade_row['Multiplier']
                    qty = trade_row['Quantity']
                    entry = trade_row['Entry Price']
                    if trade_row['Direction'] == 'Long':
                        gross_pnl = (exit_price - entry) * qty * mult
                    else:
                        gross_pnl = (entry - exit_price) * qty * mult
                    net_pnl = gross_pnl - commissions
                    cost_basis = entry * qty * mult
                    pnl_percent = (net_pnl / cost_basis) * 100 if cost_basis != 0 else 0
                    
                    for t in st.session_state.trades:
                        if t['ID'] == trade_row['ID']:
                            t.update({'Status': 'Closed', 'Exit Price': exit_price, 'Exit Date': exit_date.strftime("%Y-%m-%d"), 'Commissions': commissions, 'Net P&L ($)': net_pnl, 'Net P&L (%)': pnl_percent, 'Management Notes': mgt_notes})
                            break
                    st.success(f"Closed. P&L: ${net_pnl:,.2f}")
                    st.rerun()

        # Dynamic Display Logic
        if len(active_classes) > 1:
            for ac in active_classes:
                st.subheader(f"Active {ac}s")
                subset = df_active[df_active['Asset Class'] == ac]
                st.dataframe(subset[['Symbol', 'Direction', 'Entry Price', 'Quantity', 'Entry Date', 'Stop Loss', 'Target']], use_container_width=True, hide_index=True)
                for index, row in subset.iterrows():
                    display_close_form(row)
        else:
            st.dataframe(df_active[['Asset Class', 'Symbol', 'Direction', 'Entry Price', 'Quantity', 'Entry Date', 'Stop Loss', 'Target']], use_container_width=True, hide_index=True)
            for index, row in df_active.iterrows():
                display_close_form(row)

# -------------------------------------------
# TAB 2: HISTORY & ANALYTICS
# -------------------------------------------
with tab_history:
    closed_trades = [t for t in st.session_state.trades if t['Status'] == 'Closed']
    if not closed_trades:
        st.warning("No closed trades yet.")
    else:
        df_closed = pd.DataFrame(closed_trades).sort_values(by="Exit Date", ascending=False)
        subtab_all, subtab_stock, subtab_future, subtab_option = st.tabs(["Overview (All)", "Stocks", "Futures", "Options"])
        
        def render_performance(dataframe, title):
            if dataframe.empty:
                st.info(f"No data for {title}")
                return
            total_pnl = dataframe['Net P&L ($)'].sum()
            win_count = len(dataframe[dataframe['Net P&L ($)'] > 0])
            win_rate = (win_count / len(dataframe)) * 100
            
            st.markdown(f"#### {title} Performance")
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Net P&L", f"${total_pnl:,.2f}", delta_color="normal")
            kpi2.metric("Win Rate", f"{win_rate:.1f}%")
            kpi3.metric("Total Trades", len(dataframe))
            
            st.dataframe(dataframe[['Symbol', 'Details', 'Direction', 'Entry Date', 'Exit Date', 'Entry Price', 'Exit Price', 'Net P&L ($)', 'Net P&L (%)']].style.applymap(lambda x: 'color: #00C897' if x > 0 else 'color: #FF5252', subset=['Net P&L ($)', 'Net P&L (%)']).format({'Net P&L ($)': "${:,.2f}", 'Net P&L (%)': "{:.2f}%", 'Entry Price': "{:.2f}", 'Exit Price': "{:.2f}"}), use_container_width=True, hide_index=True)

        with subtab_all: render_performance(df_closed, "All Asset Classes")
        with subtab_stock: render_performance(df_closed[df_closed['Asset Class'] == 'Stock'], "Stocks")
        with subtab_future: render_performance(df_closed[df_closed['Asset Class'] == 'Future'], "Futures")
        with subtab_option: render_performance(df_closed[df_closed['Asset Class'] == 'Option'], "Options")