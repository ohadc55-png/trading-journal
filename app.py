import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# --- CONFIGURATION & CUSTOM CSS ---
# ==========================================
st.set_page_config(page_title="Pro Trader Journal", layout="wide", page_icon="📈")

# CSS: FORCING LIGHT TEXT ON DARK BACKGROUND
st.markdown("""
<style>
    /* 1. FORCE ALL TEXT TO BE LIGHT */
    .stApp, p, h1, h2, h3, h4, h5, h6, span, div, label {
        color: #E0E0E0 !important; /* Bright light gray/white */
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* 2. FORCE INPUT FIELDS TO BE READABLE */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox div, .stTextArea textarea {
        color: #FFFFFF !important; /* White text inside inputs */
        background-color: #262730 !important; /* Dark background for inputs */
        border: 1px solid #4a4a4a;
    }
    
    /* 3. FIX LABEL COLORS (The titles above inputs) */
    .stMarkdown label, div[data-testid="stInputLabel"] {
        color: #00e5ff !important; /* Cyan color for input labels to make them pop */
        font-weight: bold;
    }

    /* 4. DASHBOARD CARDS STYLING */
    .metric-container {
        background-color: #1c1c21;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
    }
    .metric-value {
        color: #ffffff !important;
        font-size: 1.8rem;
        font-weight: 700;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
    }
    .metric-label {
        color: #a0a0a0 !important;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* 5. BUTTON STYLING */
    div.stButton > button {
        background-color: #00C897;
        color: white !important;
        border: none;
        font-weight: bold;
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
# --- MODAL: NEW TRADE ENTRY (POP-UP) ---
# ==========================================
@st.dialog("➕ Enter New Trade Details")
def open_trade_modal():
    # This entire function runs inside a pop-up window
    
    asset_class = st.selectbox("Select Asset Class", ["Stock", "Future", "Option"])
    
    symbol = ""
    multiplier = 1.0
    details = ""
    
    # Logic for Inputs based on Class
    if asset_class == "Stock":
        symbol = st.text_input("Ticker Symbol").upper()
        details = "Stock"
    elif asset_class == "Future":
        fut = st.selectbox("Contract", list(FUTURE_MULTIPLIERS.keys()))
        symbol = fut.split(" ")[0]
        multiplier = FUTURE_MULTIPLIERS[fut]
        details = "Future"
    else: # Option
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            und = st.text_input("Underlying Asset").upper()
            o_type = st.selectbox("Type", ["Call", "Put"])
        with col_opt2:
            strike = st.text_input("Strike Price")
            exp = st.date_input("Expiration")
        
        symbol = f"{und} {o_type} {strike}"
        multiplier = 100.0
        details = f"{o_type} {strike} {exp}"

    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        direction = st.radio("Direction", ["Long", "Short"], horizontal=True)
    with c2:
        qty = st.number_input("Quantity / Size", min_value=1, value=1)
        
    entry_price = st.number_input("Entry Price", min_value=0.0, format="%.2f")
    
    c3, c4 = st.columns(2)
    with c3:
        stop_loss = st.number_input("Stop Loss", min_value=0.0, format="%.2f")
    with c4:
        target = st.number_input("Target Price", min_value=0.0, format="%.2f")
        
    reason = st.text_area("Strategy / Thesis (Optional)")
    
    if st.button("Submit Trade", use_container_width=True):
        new_trade = {
            "ID": len(st.session_state.trades) + 1, "Asset Class": asset_class, "Symbol": symbol,
            "Details": details, "Direction": direction, "Entry Date": datetime.today().strftime("%Y-%m-%d"),
            "Entry Price": entry_price, "Quantity": qty, "Multiplier": multiplier,
            "Stop Loss": stop_loss, "Target": target, "Reason": reason,
            "Status": "Open", "Exit Date": None, "Exit Price": 0.0,
            "Commissions": 0.0, "Net P&L ($)": 0.0, "Net P&L (%)": 0.0, "Management Notes": ""
        }
        st.session_state.trades.append(new_trade)
        st.success("Trade Added!")
        st.rerun()

# ==========================================
# --- SIDEBAR: SETTINGS & BUTTONS ---
# ==========================================
with st.sidebar:
    st.title("⚡ Actions")
    
    # THE BIG BUTTON THAT OPENS THE POP-UP
    if st.button("➕ NEW TRADE", type="primary", use_container_width=True):
        open_trade_modal()
        
    st.markdown("---")
    with st.expander("💰 Capital Settings", expanded=False):
        st.session_state.initial_capital = st.number_input("Start Capital", value=st.session_state.initial_capital)
        dep = st.number_input("Deposit (+)", min_value=0.0, step=100.0)
        wd = st.number_input("Withdraw (-)", min_value=0.0, step=100.0)
        if st.button("Update Funds"):
            st.session_state.deposits += dep
            st.session_state.withdrawals += wd
            st.rerun()

# ==========================================
# --- MAIN DASHBOARD ---
# ==========================================

# CALCULATIONS
df = pd.DataFrame(st.session_state.trades)
realized_pl = df[df['Status'] == 'Closed']['Net P&L ($)'].sum() if not df.empty else 0.0
adj_capital = st.session_state.initial_capital + st.session_state.deposits - st.session_state.withdrawals
curr_equity = adj_capital + realized_pl
return_pct = (realized_pl / adj_capital * 100) if adj_capital > 0 else 0.0

# HELPER FOR CARDS
def card_html(label, value, color_override=None):
    val_str = f"${value:,.2f}" if isinstance(value, float) else value
    if "Return" in label: val_str = f"{value:.2f}%"
    
    color_style = ""
    if color_override == "green": color_style = "color: #00e676 !important;"
    elif color_override == "red": color_style = "color: #ff1744 !important;"
    
    return f"""
    <div class="metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="{color_style}">{val_str}</div>
    </div>
    """

st.markdown("## 📊 Account Overview")

# RENDER CARDS
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(card_html("Adjusted Capital", adj_capital), unsafe_allow_html=True)
with c2: st.markdown(card_html("Current Equity", curr_equity, "white"), unsafe_allow_html=True)
with c3: 
    color = "green" if realized_pl >= 0 else "red"
    st.markdown(card_html("Realized P&L", realized_pl, color), unsafe_allow_html=True)
with c4: 
    color = "green" if return_pct >= 0 else "red"
    st.markdown(card_html("Total Return", return_pct, color), unsafe_allow_html=True)

st.write("") 

# ==========================================
# --- TABS: ACTIVE & HISTORY ---
# ==========================================
tab_active, tab_hist = st.tabs(["🟢 Active Positions", "📚 Trade History"])

with tab_active:
    open_trades = [t for t in st.session_state.trades if t['Status'] == 'Open']
    if not open_trades:
        st.info("No active trades.")
    else:
        df_open = pd.DataFrame(open_trades)
        for i, row in df_open.iterrows():
            # Use Expander for each row to keep it clean
            with st.expander(f"{row['Symbol']} | {row['Direction']} | Size: {row['Quantity']} | Entry: {row['Entry Price']}", expanded=True):
                c_exit1, c_exit2, c_exit3 = st.columns([1, 1, 2])
                with c_exit1:
                    exit_price = st.number_input("Exit Price", key=f"ep_{row['ID']}")
                with c_exit2:
                    comm = st.number_input("Comm ($)", key=f"cm_{row['ID']}")
                with c_exit3:
                    st.write("") 
                    st.write("") 
                    if st.button("🔴 CLOSE TRADE", key=f"cls_{row['ID']}"):
                        # Calculation Logic
                        mult = row['Multiplier']
                        if row['Direction'] == 'Long':
                            gross = (exit_price - row['Entry Price']) * row['Quantity'] * mult
                        else:
                            gross = (row['Entry Price'] - exit_price) * row['Quantity'] * mult
                        net = gross - comm
                        cost = row['Entry Price'] * row['Quantity'] * mult
                        pct = (net / cost) * 100 if cost != 0 else 0
                        
                        # Update State
                        for t in st.session_state.trades:
                            if t['ID'] == row['ID']:
                                t.update({'Status': 'Closed', 'Exit Price': exit_price, 'Exit Date': datetime.today().strftime("%Y-%m-%d"), 'Commissions': comm, 'Net P&L ($)': net, 'Net P&L (%)': pct})
                        st.rerun()

with tab_hist:
    closed_trades = [t for t in st.session_state.trades if t['Status'] == 'Closed']
    if not closed_trades:
        st.write("No closed trades available.")
    else:
        df_closed = pd.DataFrame(closed_trades).sort_values(by="Exit Date", ascending=False)
        
        # Display Table with Colors
        st.dataframe(
            df_closed[['Symbol', 'Direction', 'Entry Price', 'Exit Price', 'Net P&L ($)', 'Net P&L (%)']].style.applymap(
                lambda x: 'color: #00e676' if x > 0 else 'color: #ff1744', subset=['Net P&L ($)', 'Net P&L (%)']
            ).format({'Net P&L ($)': "${:,.2f}", 'Net P&L (%)': "{:.2f}%"}),
            use_container_width=True
        )