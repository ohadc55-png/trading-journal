import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="Pro Trading Journal", layout="wide", page_icon="📈")

# --- INITIALIZE SESSION STATE ---
if 'trades' not in st.session_state:
    st.session_state.trades = []

if 'capital' not in st.session_state:
    st.session_state.capital = 10000.0  # Default starting capital

if 'balance_history' not in st.session_state:
    st.session_state.balance_history = []

# --- MULTIPLIER DICTIONARY FOR FUTURES ---
FUTURE_MULTIPLIERS = {
    "ES (E-mini S&P 500)": 50,
    "MES (Micro S&P 500)": 5,
    "NQ (E-mini NASDAQ 100)": 20,
    "MNQ (Micro NASDAQ 100)": 2,
    "RTY (E-mini Russell 2000)": 50,
    "M2K (Micro Russell 2000)": 5,
    "GC (Gold)": 100,
    "MGC (Micro Gold)": 10,
    "SI (Silver)": 1000, # $1,000 per 1.0 move (standard contract is 5000oz)
    "SIL (Micro Silver)": 100,
    "CL (Crude Oil)": 1000
}

# --- SIDEBAR: CAPITAL MANAGEMENT ---
st.sidebar.header("💰 Capital Management")
initial_cap_input = st.sidebar.number_input("Initial Capital ($)", value=st.session_state.capital, step=1000.0)

# Update capital if changed manually
if initial_cap_input != st.session_state.capital:
    st.session_state.capital = initial_cap_input

st.sidebar.markdown("---")
st.sidebar.subheader("Cash Flow")
deposit = st.sidebar.number_input("Deposit Funds (+)", min_value=0.0, step=100.0)
withdraw = st.sidebar.number_input("Withdraw Funds (-)", min_value=0.0, step=100.0)

if st.sidebar.button("Apply Cash Flow"):
    if deposit > 0:
        st.session_state.capital += deposit
        st.sidebar.success(f"Deposited ${deposit:,.2f}")
    if withdraw > 0:
        st.session_state.capital -= withdraw
        st.sidebar.success(f"Withdrew ${withdraw:,.2f}")

# Calculate Statistics
df = pd.DataFrame(st.session_state.trades)
total_realized_pl = df['Net P&L ($)'].sum() if not df.empty else 0.0
current_equity = st.session_state.capital + total_realized_pl

st.sidebar.markdown("---")
st.sidebar.metric(label="Current Equity", value=f"${current_equity:,.2f}")
st.sidebar.metric(label="Total Realized P&L", value=f"${total_realized_pl:,.2f}", 
                  delta_color="normal" if total_realized_pl == 0 else "inverse")


# --- MAIN APP UI ---
st.title("📈 Professional Trading Journal")

tab1, tab2 = st.tabs(["📝 New Entry & Active Trades", "📊 History & Analytics"])

# ==========================================
# TAB 1: NEW ENTRY & ACTIVE TRADES
# ==========================================
with tab1:
    st.subheader("New Trade Entry")
    
    # 1. Asset Class Selection
    asset_class = st.radio("Select Asset Class:", ["Stock", "Future", "Option"], horizontal=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # SYMBOL INPUT LOGIC
        if asset_class == "Stock":
            symbol = st.text_input("Ticker Symbol (e.g., AAPL)").upper()
            multiplier = 1.0
            qty_label = "Shares"
            details = "Stock"
            
        elif asset_class == "Future":
            future_name = st.selectbox("Select Contract", list(FUTURE_MULTIPLIERS.keys()))
            symbol = future_name.split(" ")[0] # Extract symbol like 'ES'
            multiplier = FUTURE_MULTIPLIERS[future_name]
            qty_label = "Contracts"
            details = f"Future ({multiplier}$/pt)"
            
        else: # Option
            underlying = st.text_input("Underlying Symbol (e.g., SPY)").upper()
            opt_type = st.selectbox("Type", ["Call", "Put"])
            strike = st.number_input("Strike Price", step=1.0)
            exp_date = st.date_input("Expiration Date")
            symbol = f"{underlying} {exp_date.strftime('%d%b%y')} {strike}{opt_type[0]}"
            multiplier = 100.0
            qty_label = "Contracts"
            details = f"{opt_type} {strike} Exp: {exp_date}"
            
            # Optional: Underlying Target
            underlying_target = st.number_input("Underlying Asset Target Price (Optional)", min_value=0.0, step=0.1)

    with col2:
        direction = st.radio("Direction", ["Long", "Short"], horizontal=True)
        quantity = st.number_input(f"Quantity ({qty_label})", min_value=1, step=1)
        entry_date = st.date_input("Entry Date", datetime.today())
        
    with col3:
        if asset_class == "Option":
            entry_price = st.number_input("Premium Price (per contract)", min_value=0.0, step=0.05, format="%.2f")
        else:
            entry_price = st.number_input("Entry Price", min_value=0.0, step=0.25, format="%.2f")
            
        stop_loss = st.number_input("Initial Stop Loss", min_value=0.0, step=0.25)
        target_price = st.number_input("Target Price", min_value=0.0, step=0.25)

    reason = st.text_area("Trade Thesis / Strategy")
    
    if st.button("Open Trade"):
        new_trade = {
            "ID": len(st.session_state.trades) + 1,
            "Asset Class": asset_class,
            "Symbol": symbol,
            "Details": details,
            "Direction": direction,
            "Entry Date": entry_date.strftime("%Y-%m-%d"),
            "Entry Price": entry_price,
            "Quantity": quantity,
            "Multiplier": multiplier,
            "Stop Loss": stop_loss,
            "Target": target_price,
            "Reason": reason,
            "Status": "Open",
            "Exit Date": None,
            "Exit Price": 0.0,
            "Commissions": 0.0,
            "Net P&L ($)": 0.0,
            "Net P&L (%)": 0.0,
            "Management Notes": ""
        }
        st.session_state.trades.append(new_trade)
        st.success(f"Trade Opened: {direction} {symbol}")
        st.rerun()

    st.markdown("---")
    
    # --- ACTIVE TRADES DISPLAY (Dynamic) ---
    st.subheader("🔥 Active Positions")
    
    # Filter Open Trades
    active_trades = [t for t in st.session_state.trades if t['Status'] == 'Open']
    
    if not active_trades:
        st.info("No active trades currently.")
    else:
        # Convert to DataFrame for easier handling
        df_active = pd.DataFrame(active_trades)
        
        # Check distinct asset classes
        active_classes = df_active['Asset Class'].unique()
        
        # Helper function to display trade closure form
        def display_close_form(trade_row):
            with st.expander(f"Close Trade: {trade_row['Symbol']} (ID: {trade_row['ID']})"):
                col_exit1, col_exit2 = st.columns(2)
                with col_exit1:
                    exit_price = st.number_input(f"Exit Price", key=f"ep_{trade_row['ID']}", step=0.1)
                    exit_date = st.date_input(f"Exit Date", datetime.today(), key=f"ed_{trade_row['ID']}")
                with col_exit2:
                    commissions = st.number_input("Total Commissions ($)", min_value=0.0, step=1.0, key=f"cm_{trade_row['ID']}")
                    mgt_notes = st.text_area("Management / Exit Notes", key=f"mn_{trade_row['ID']}")
                
                if st.button(f"Confirm Close {trade_row['Symbol']}", key=f"btn_{trade_row['ID']}"):
                    # CALCULATE P&L
                    mult = trade_row['Multiplier']
                    qty = trade_row['Quantity']
                    entry = trade_row['Entry Price']
                    
                    if trade_row['Direction'] == 'Long':
                        gross_pnl = (exit_price - entry) * qty * mult
                    else: # Short
                        gross_pnl = (entry - exit_price) * qty * mult
                        
                    net_pnl = gross_pnl - commissions
                    
                    # Calculate % P&L (Based on margin/cost)
                    cost_basis = entry * qty * mult
                    pnl_percent = (net_pnl / cost_basis) * 100 if cost_basis != 0 else 0
                    
                    # Update Record in Session State
                    for t in st.session_state.trades:
                        if t['ID'] == trade_row['ID']:
                            t['Status'] = 'Closed'
                            t['Exit Price'] = exit_price
                            t['Exit Date'] = exit_date.strftime("%Y-%m-%d")
                            t['Commissions'] = commissions
                            t['Net P&L ($)'] = net_pnl
                            t['Net P&L (%)'] = pnl_percent
                            t['Management Notes'] = mgt_notes
                            break
                    
                    st.success(f"Trade Closed. P&L: ${net_pnl:,.2f}")
                    st.rerun()

        # LOGIC: If multiple classes, split them. If single, show one table.
        if len(active_classes) > 1:
            for ac in active_classes:
                st.markdown(f"### Active {ac}s")
                subset = df_active[df_active['Asset Class'] == ac]
                
                # Show table for quick view
                st.dataframe(subset[['ID', 'Symbol', 'Direction', 'Entry Price', 'Quantity', 'Entry Date']])
                
                # Show close forms
                for index, row in subset.iterrows():
                    display_close_form(row)
        else:
            # Single class only
            st.dataframe(df_active[['ID', 'Asset Class', 'Symbol', 'Direction', 'Entry Price', 'Quantity', 'Entry Date']])
            for index, row in df_active.iterrows():
                display_close_form(row)

# ==========================================
# TAB 2: HISTORY & ANALYTICS
# ==========================================
with tab2:
    st.header("Trade History & Performance")
    
    closed_trades = [t for t in st.session_state.trades if t['Status'] == 'Closed']
    
    if not closed_trades:
        st.warning("No closed trades yet.")
    else:
        df_closed = pd.DataFrame(closed_trades)
        
        # Sort by Exit Date (Newest first)
        df_closed = df_closed.sort_values(by="Exit Date", ascending=False)
        
        # --- SUB-TABS FOR SECTORS ---
        subtab_all, subtab_stock, subtab_future, subtab_option = st.tabs(
            ["Overview (All)", "Stocks", "Futures", "Options"]
        )
        
        def render_performance(dataframe, title):
            if dataframe.empty:
                st.info(f"No closed trades for {title}")
                return
            
            # KPI CARDS
            total_pnl = dataframe['Net P&L ($)'].sum()
            win_count = len(dataframe[dataframe['Net P&L ($)'] > 0])
            total_count = len(dataframe)
            win_rate = (win_count / total_count) * 100
            
            avg_win = dataframe[dataframe['Net P&L ($)'] > 0]['Net P&L ($)'].mean()
            avg_loss = dataframe[dataframe['Net P&L ($)'] <= 0]['Net P&L ($)'].mean()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Net P&L", f"${total_pnl:,.2f}", delta_color="normal")
            c2.metric("Win Rate", f"{win_rate:.1f}%")
            c3.metric("Avg Win", f"${avg_win:,.2f}" if not pd.isna(avg_win) else "-")
            c4.metric("Avg Loss", f"${avg_loss:,.2f}" if not pd.isna(avg_loss) else "-")
            
            # STYLE TABLE (Green/Red P&L)
            st.dataframe(
                dataframe[[
                    'Symbol', 'Direction', 'Entry Date', 'Exit Date', 
                    'Entry Price', 'Exit Price', 'Net P&L ($)', 'Net P&L (%)'
                ]].style.applymap(
                    lambda x: 'color: green' if x > 0 else 'color: red', 
                    subset=['Net P&L ($)', 'Net P&L (%)']
                ),
                use_container_width=True
            )

        with subtab_all:
            render_performance(df_closed, "All Trades")
            
        with subtab_stock:
            render_performance(df_closed[df_closed['Asset Class'] == 'Stock'], "Stocks")
            
        with subtab_future:
            render_performance(df_closed[df_closed['Asset Class'] == 'Future'], "Futures")
            
        with subtab_option:
            render_performance(df_closed[df_closed['Asset Class'] == 'Option'], "Options")