import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests

# ==========================================
# --- CONFIGURATION & STYLING ---
# ==========================================
st.set_page_config(page_title="ProTrade Journal Pro", layout="wide", page_icon="📈")

API_KEY = 'Y2S0SAL1NRF0Z40J'

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
    
    .history-card {
        background-color: #1F2937;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        border-right: 8px solid #374151;
    }
    .history-win { border-right: 8px solid #34D399; }
    .history-loss { border-right: 8px solid #F87171; }
    .detail-label { color: #9CA3AF; font-size: 0.75rem; text-transform: uppercase; }
    .detail-value { color: #E5E7EB; font-weight: 600; font-size: 1rem; }
    .divider { border-top: 1px solid #374151; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# --- INITIALIZE SESSION STATE ---
# ==========================================
# אתחול בטוח של הנתונים כדי למנוע קריסות
if 'trades' not in st.session_state: 
    st.session_state.trades = []
if 'initial_capital' not in st.session_state: 
    st.session_state.initial_capital = 10000.0

# ==========================================
# --- API FUNCTIONS ---
# ==========================================
@st.cache_data(ttl=60) # עדכון כל דקה
def fetch_ticker_data(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
        res = requests.get(url, timeout=5).json()
        q = res.get('Global Quote', {})
        return {
            'price': float(q.get('05. price', 0)),
            'change_pct': float(q.get('10. change percent', '0').replace('%',''))
        }
    except: return None

# ==========================================
# --- TOP TICKER BAR ---
# ==========================================
st.markdown("### 🌍 Market Ticker")
indices = [("SPY", "S&P 500"), ("QQQ", "Nasdaq"), ("GLD", "Gold")]
t_cols = st.columns(len(indices))

for i, (sym, name) in enumerate(indices):
    data = fetch_ticker_data(sym)
    if data:
        color = "text-green" if data['change_pct'] >= 0 else "text-red"
        t_cols[i].markdown(f"**{name}**<br><span style='font-size:1.2rem;'>${data['price']:.2f}</span> <small class='{color}'>{data['change_pct']:+.2f}%</small>", unsafe_allow_html=True)

# ==========================================
# --- SIDEBAR CONTROLS ---
# ==========================================
with st.sidebar:
    st.title("⚙️ Controls")
    if st.button("➕ NEW TRADE", type="primary", use_container_width=True):
        st.session_state.show_modal = True # פתרון לדיאלוג
    
    st.markdown("---")
    st.session_state.initial_capital = st.number_input("Starting Capital ($)", value=st.session_state.initial_capital)
    
    if st.button("⚠️ CLEAR SESSION & DATA", use_container_width=True):
        st.session_state.trades = []
        st.rerun()

# ==========================================
# --- DASHBOARD KPIs ---
# ==========================================
total_pnl = sum(t.get('Total Realized P&L', 0.0) for t in st.session_state.trades)
equity = st.session_state.initial_capital + total_pnl
roi = (total_pnl / st.session_state.initial_capital * 100) if st.session_state.initial_capital > 0 else 0

st.markdown("## 📊 Dashboard")
c1, c2, c3, c4 = st.columns(4)

def kpi_card(title, value, is_money=True, color_logic=False, is_percent=False):
    color_class = ("text-green" if value > 0 else "text-red") if color_logic else ""
    val_fmt = f"${value:,.2f}" if is_money else (f"{value:+.2f}%" if is_percent else str(value))
    return f'<div class="metric-card"><div class="metric-label">{title}</div><div class="metric-value {color_class}">{val_fmt}</div></div>'

with c1: st.markdown(kpi_card("Current Equity", equity), unsafe_allow_html=True)
with c2: st.markdown(kpi_card("Total Realized P&L", total_pnl, True, True), unsafe_allow_html=True)
with c3: st.markdown(kpi_card("Account ROI", roi, False, True, True), unsafe_allow_html=True)
with c4: st.markdown(kpi_card("Open Trades", len([t for t in st.session_state.trades if t.get('Status') == 'Open']), False), unsafe_allow_html=True)

# ==========================================
# --- MODAL: NEW TRADE (Using dialog) ---
# ==========================================
@st.dialog("🚀 New Trade Entry")
def open_trade_modal():
    asset = st.selectbox("Asset Class", ["Stock", "Future", "Option"])
    symbol = st.text_input("Symbol").upper()
    multiplier = 100.0 if asset == "Option" else 1.0
    
    col_q, col_d = st.columns(2)
    qty = col_q.number_input("Quantity", min_value=1, value=1)
    direction = col_d.radio("Direction", ["Long", "Short"], horizontal=True)
    
    col_da, col_pr = st.columns(2)
    entry_date = col_da.date_input("Entry Date")
    entry_price = col_pr.number_input("Entry Price ($)", min_value=0.01)
    
    if st.button("Open Position", type="primary", use_container_width=True):
        st.session_state.trades.append({
            "ID": len(st.session_state.trades) + 1, "Asset Class": asset, "Symbol": symbol,
            "Direction": direction, "Entry Date": entry_date.strftime("%Y-%m-%d"), 
            "Entry Price": entry_price, "Original Qty": qty, "Remaining Qty": qty, 
            "Multiplier": multiplier, "Exits": [], "Total Realized P&L": 0.0,
            "Status": "Open"
        })
        st.rerun()

if st.get('show_modal', False):
    open_trade_modal()
    st.session_state.show_modal = False

# ==========================================
# --- TABS: ACTIVE & HISTORY ---
# ==========================================
st.markdown("---")
tab_active, tab_history = st.tabs(["📂 Active Trades", "📜 Detailed History"])

with tab_active:
    active = [t for t in st.session_state.trades if t.get('Status') == 'Open']
    if not active: st.info("No active trades.")
    for i, trade in enumerate(active):
        with st.expander(f"🔵 {trade['Symbol']} - {trade['Direction']} | Remaining: {trade['Remaining Qty']}"):
            cq, cp, cc = st.columns(3)
            sq = cq.number_input("Qty to Sell", 1, trade['Remaining Qty'], key=f"sq_{trade['ID']}")
            sp = cp.number_input("Exit Price", 0.0, key=f"sp_{trade['ID']}")
            sc = cc.number_input("Comm ($)", 0.0, key=f"sc_{trade['ID']}")
            
            if st.button("Execute Partial Sale", key=f"btn_{trade['ID']}", type="primary"):
                m = trade.get('Multiplier', 1.0)
                diff = (sp - trade['Entry Price']) if trade['Direction'] == "Long" else (trade['Entry Price'] - sp)
                pnl = (diff * sq * m) - sc
                
                trade.setdefault('Exits', []).append({"qty": sq, "price": sp, "pnl": pnl, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
                trade['Remaining Qty'] -= sq
                trade['Total Realized P&L'] += pnl
                if trade['Remaining Qty'] <= 0: 
                    trade['Status'] = "Closed"
                    trade['Exit Date'] = datetime.now().strftime("%Y-%m-%d")
                st.rerun()

with tab_history:
    closed = [t for t in st.session_state.trades if t.get('Status') == 'Closed']
    if not closed: st.write("History is empty.")
    for t in closed:
        invested = t['Original Qty'] * t['Entry Price'] * t.get('Multiplier', 1.0)
        pnl = t.get('Total Realized P&L', 0.0)
        roi_t = (pnl / invested * 100) if invested > 0 else 0
        
        sold_val = sum(e['qty'] * e['price'] * t.get('Multiplier', 1.0) for e in t.get('Exits', []))
        avg_exit = (sold_val / (t['Original Qty'] * t.get('Multiplier', 1.0))) if t['Original Qty'] > 0 else 0
        
        cls = "history-win" if pnl >= 0 else "history-loss"
        txt = "text-green" if pnl >= 0 else "text-red"
        
        st.markdown(f"""
        <div class="history-card {cls}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 1.3rem; font-weight: bold;">{t['Symbol']} <small>({t['Asset Class']})</small></span>
                <span class="{txt}" style="font-size: 1.3rem; font-weight: bold;">{pnl:+,.2f}$ ({roi_t:+.2f}%)</span>
            </div>
            <div class="divider"></div>
            <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div><div class="detail-label">Entry / Exit Date</div><div class="detail-value">{t['Entry Date']} / {t.get('Exit Date', 'N/A')}</div></div>
                <div><div class="detail-label">Entry / Avg Exit Price</div><div class="detail-value">${t['Entry Price']:.2f} / ${avg_exit:.2f}</div></div>
                <div><div class="detail-label">Invested / Sold Value</div><div class="detail-value">${invested:,.2f} / ${sold_val:,.2f}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)