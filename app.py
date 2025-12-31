import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests

# ==========================================
# --- CONFIGURATION & PRO STYLING ---
# ==========================================
st.set_page_config(page_title="ProTrade Journal Pro", layout="wide", page_icon="📈")

API_KEY = 'Y2S0SAL1NRF0Z40J' # המפתח שלך

st.markdown("""
<style>
    .stApp { background-color: #0E1117; font-family: 'Roboto', sans-serif; }
    
    /* קומפוננטות UI */
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
    
    /* שורת מדדים עליונה */
    .ticker-bar {
        background: #111827;
        border-bottom: 1px solid #374151;
        padding: 10px 20px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-around;
    }
    
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
if 'trades' not in st.session_state: st.session_state.trades = []
if 'initial_capital' not in st.session_state: st.session_state.initial_capital = 10000.0

FUTURE_MULTIPLIERS = { 
    "ES": 50, "MES": 5, "NQ": 20, "MNQ": 2, "GC": 100, "CL": 1000 
}

# ==========================================
# --- API HELPERS (QA: Caching applied) ---
# ==========================================
@st.cache_data(ttl=300)
def fetch_market_data(symbol, is_crypto=False):
    try:
        if is_crypto:
            url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={symbol}&to_currency=USD&apikey={API_KEY}"
            res = requests.get(url, timeout=5).json()
            rate = res.get('Realtime Currency Exchange Rate', {})
            return {'price': float(rate.get('5. Exchange Rate', 0)), 'change': 0.0}
        else:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
            res = requests.get(url, timeout=5).json()
            quote = res.get('Global Quote', {})
            return {
                'price': float(quote.get('05. price', 0)),
                'change_pct': float(quote.get('10. change percent', '0').replace('%', ''))
            }
    except: return None

# ==========================================
# --- TOP TICKER BAR ---
# ==========================================
def display_ticker():
    indices = [("SPY", "S&P 500"), ("QQQ", "Nasdaq"), ("GLD", "Gold")]
    cols = st.columns(len(indices) + 1)
    
    for i, (sym, name) in enumerate(indices):
        data = fetch_market_data(sym)
        if data:
            color = "text-green" if data['change_pct'] >= 0 else "text-red"
            cols[i].markdown(f"**{name}**<br><span style='font-size:1.2rem;'>${data['price']:.2f}</span> <small class='{color}'>{data['change_pct']:+.2f}%</small>", unsafe_allow_html=True)
    
    btc = fetch_market_data("BTC", True)
    if btc:
        cols[-1].markdown(f"**Bitcoin**<br><span style='font-size:1.2rem;'>${btc['price']:,.0f}</span>", unsafe_allow_html=True)

# ==========================================
# --- MODAL: NEW TRADE ---
# ==========================================
@st.dialog("🚀 New Trade Entry")
def open_trade_modal():
    asset = st.selectbox("Asset Class", ["Stock", "Future", "Option"])
    symbol = st.text_input("Symbol (e.g., NVDA, ES, AAPL)").upper()
    
    multiplier = 1.0
    if asset == "Future": multiplier = FUTURE_MULTIPLIERS.get(symbol, 1.0)
    elif asset == "Option": multiplier = 100.0
    
    c1, c2 = st.columns(2)
    direction = c1.radio("Direction", ["Long", "Short"], horizontal=True)
    qty = c2.number_input("Quantity", min_value=1, value=1)
    
    p1, p2 = st.columns(2)
    entry_date = p1.date_input("Entry Date")
    entry_price = p2.number_input("Entry Price ($)", min_value=0.01, format="%.2f")
    
    strategy = st.selectbox("Strategy", ["Breakout", "Pullback", "Trend", "Level"])
    reason = st.text_area("Trade Reasoning")
    
    if st.button("✅ Open Position", type="primary", use_container_width=True):
        st.session_state.trades.append({
            "ID": len(st.session_state.trades) + 1, "Asset Class": asset, "Symbol": symbol,
            "Direction": direction, "Entry Date": entry_date.strftime("%Y-%m-%d"), 
            "Entry Price": entry_price, "Original Qty": qty, "Remaining Qty": qty, 
            "Multiplier": multiplier, "Exits": [], "Total Realized P&L": 0.0,
            "Status": "Open", "Strategy": strategy, "Reason": reason
        })
        st.rerun()

# ==========================================
# --- MAIN LAYOUT ---
# ==========================================
display_ticker()
st.title("📈 ProTrade Journal Pro")

# --- KPI Dashboard ---
total_pnl = sum(t.get('Total Realized P&L', 0.0) for t in st.session_state.trades)
equity = st.session_state.initial_capital + total_pnl
roi = (total_pnl / st.session_state.initial_capital * 100) if st.session_state.initial_capital > 0 else 0

c1, c2, c3, c4 = st.columns(4)
def kpi(title, val, is_money=True, color=False, is_pct=False):
    cls = ("text-green" if val > 0 else "text-red") if color else ""
    fmt = f"${val:,.2f}" if is_money else (f"{val:+.2f}%" if is_pct else str(val))
    st.markdown(f'<div class="metric-card"><div class="metric-label">{title}</div><div class="metric-value {cls}">{fmt}</div></div>', unsafe_allow_html=True)

with c1: kpi("Current Equity", equity)
with c2: kpi("Total Realized P&L", total_pnl, True, True)
with c3: kpi("Account ROI", roi, False, True, True)
with c4: kpi("Open Positions", len([t for t in st.session_state.trades if t.get('Status') == 'Open']), False)

# --- TABS ---
st.markdown("---")
t_active, t_history = st.tabs(["📂 Active Positions", "📜 Detailed History"])

# --- TAB 1: ACTIVE ---
with t_active:
    active_list = [t for t in st.session_state.trades if t.get('Status') == 'Open']
    if not active_list: st.info("No active trades.")
    for i, trade in enumerate(active_list):
        with st.expander(f"🔵 {trade['Symbol']} | {trade['Direction']} | Remaining: {trade['Remaining Qty']}"):
            col_q, col_p, col_c = st.columns(3)
            sq = col_q.number_input("Qty to Sell", 1, trade['Remaining Qty'], key=f"q_{trade['ID']}")
            sp = col_p.number_input("Exit Price", 0.0, format="%.2f", key=f"p_{trade['ID']}")
            sc = col_c.number_input("Comm ($)", 0.0, key=f"c_{trade['ID']}")
            
            if st.button(f"Execute Sale", key=f"btn_{trade['ID']}", type="primary"):
                m = trade.get('Multiplier', 1.0)
                # QA: Correct P&L Calculation for Long/Short
                diff = (sp - trade['Entry Price']) if trade['Direction'] == "Long" else (trade['Entry Price'] - sp)
                pnl = (diff * sq * m) - sc
                
                trade.setdefault('Exits', []).append({"qty": sq, "price": sp, "pnl": pnl, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
                trade['Remaining Qty'] -= sq
                trade['Total Realized P&L'] += pnl
                if trade['Remaining Qty'] <= 0: 
                    trade['Status'] = "Closed"
                    trade['Exit Date'] = datetime.now().strftime("%Y-%m-%d")
                st.rerun()

# --- TAB 2: HISTORY (QA: Comprehensive Data) ---
with t_history:
    closed_list = [t for t in st.session_state.trades if t.get('Status') == 'Closed']
    if not closed_list: st.write("History is empty.")
    for t in closed_list:
        invested = t['Original Qty'] * t['Entry Price'] * t.get('Multiplier', 1.0)
        pnl = t.get('Total Realized P&L', 0.0)
        roi_t = (pnl / invested * 100) if invested > 0 else 0
        
        # אגרגציה למכירות
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
                <div><div class="detail-label">Invested / Sold Value</div><div class="detail-value