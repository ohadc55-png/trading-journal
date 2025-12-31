import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests

# ==========================================
# --- CONFIGURATION & STYLING ---
# ==========================================
st.set_page_config(page_title="ProTrade Journal Pro", layout="wide", page_icon="📈")

API_KEY = 'Y2S0SAL1NRF0Z40J' # המפתח שסיפקת

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
    
    .ticker-bar {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
    }
    
    .history-card {
        background-color: #1F2937;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        border-left: 8px solid #374151;
    }
    .history-win { border-left: 8px solid #34D399; }
    .history-loss { border-left: 8px solid #F87171; }
    .detail-label { color: #9CA3AF; font-size: 0.75rem; text-transform: uppercase; }
    .detail-value { color: #E5E7EB; font-weight: 600; font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# --- INITIALIZE STATE ---
# ==========================================
if 'trades' not in st.session_state: st.session_state.trades = []
if 'initial_capital' not in st.session_state: st.session_state.initial_capital = 10000.0
if 'benchmark_target' not in st.session_state: st.session_state.benchmark_target = 5000.0

FUTURE_MULTIPLIERS = { "ES (S&P 500)": 50, "MES (Micro S&P)": 5, "NQ (Nasdaq 100)": 20, "MNQ (Micro Nasdaq)": 2, "GC (Gold)": 100, "CL (Crude Oil)": 1000 }
MAJOR_INDICES = [ {"symbol": "SPY", "name": "S&P 500"}, {"symbol": "QQQ", "name": "Nasdaq"}, {"symbol": "GLD", "name": "Gold"} ]

# ==========================================
# --- API & UTILS ---
# ==========================================
@st.cache_data(ttl=60)
def fetch_stock_quote(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
        data = requests.get(url, timeout=10).json()
        if 'Global Quote' in data:
            q = data['Global Quote']
            return {'price': float(q.get('05. price', 0)), 'change_pct': float(q.get('10. change percent', '0').replace('%',''))}
    except: return None

def calculate_advanced_metrics(trades):
    closed = [t for t in trades if t.get('Status') == 'Closed']
    if not closed: return None
    winners = [t for t in closed if t.get('Total Realized P&L', 0) > 0]
    losers = [t for t in closed if t.get('Total Realized P&L', 0) < 0]
    win_rate = (len(winners) / len(closed) * 100) if closed else 0
    total_wins = sum(t.get('Total Realized P&L', 0) for t in winners)
    total_losses = abs(sum(t.get('Total Realized P&L', 0) for t in losers))
    profit_factor = total_wins / total_losses if total_losses > 0 else 99.0
    return {'win_rate': win_rate, 'profit_factor': profit_factor, 'total_trades': len(closed), 'avg_win': total_wins/len(winners) if winners else 0}

# ==========================================
# --- MODAL: NEW TRADE ---
# ==========================================
@st.dialog("🚀 New Trade Entry")
def open_trade_modal():
    asset_class = st.selectbox("Asset Class", ["Stock", "Future", "Option"])
    symbol = st.text_input("Symbol").upper()
    multiplier = 100.0 if asset_class == "Option" else (FUTURE_MULTIPLIERS.get(symbol, 1.0) if asset_class == "Future" else 1.0)
    
    c1, c2 = st.columns(2)
    direction = c1.radio("Direction", ["Long", "Short"], horizontal=True)
    qty = c2.number_input("Quantity", min_value=1, value=1)
    
    p1, p2 = st.columns(2)
    entry_date = p1.date_input("Entry Date")
    entry_price = p2.number_input("Entry Price ($)", min_value=0.01)
    
    strategy = st.selectbox("Strategy", ["Breakout", "Pullback", "Trend Following", "Pattern"])
    reason = st.text_area("Trade Plan")
    
    if st.button("✅ Open Position", type="primary", use_container_width=True):
        new_trade = {
            "ID": len(st.session_state.trades) + 1, "Asset Class": asset_class, "Symbol": symbol,
            "Direction": direction, "Entry Date": entry_date.strftime("%Y-%m-%d"), "Entry Price": entry_price,
            "Original Qty": qty, "Remaining Qty": qty, "Multiplier": multiplier, "Strategy": strategy,
            "Exits": [], "Total Realized P&L": 0.0, "Status": "Open", "Reason": reason
        }
        st.session_state.trades.append(new_trade)
        st.rerun()

# ==========================================
# --- MAIN UI ---
# ==========================================
st.title("📈 ProTrade Journal Pro")

# Ticker Bar
t_cols = st.columns(len(MAJOR_INDICES))
for i, idx in enumerate(MAJOR_INDICES):
    data = fetch_stock_quote(idx['symbol'])
    if data:
        color = "text-green" if data['change_pct'] >= 0 else "text-red"
        t_cols[i].markdown(f"**{idx['name']}**: ${data['price']:.2f} (<span class='{color}'>{data['change_pct']:.2f}%</span>)", unsafe_allow_html=True)

# KPIs
total_pnl = sum(t.get('Total Realized P&L', 0.0) for t in st.session_state.trades)
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f'<div class="metric-card"><div class="metric-label">Equity</div><div class="metric-value">${st.session_state.initial_capital + total_pnl:,.2f}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card"><div class="metric-label">Total P&L</div><div class="metric-value {"text-green" if total_pnl >=0 else "text-red"}">${total_pnl:,.2f}</div></div>', unsafe_allow_html=True)

# Performance Analytics
metrics = calculate_advanced_metrics(st.session_state.trades)
if metrics:
    st.markdown("---")
    st.markdown("## 📊 Analytics")
    a1, a2, a3 = st.columns(3)
    a1.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
    a2.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
    a3.metric("Avg Win", f"${metrics['avg_win']:.2f}")

# Active Trades & History Tabs
st.markdown("---")
tab_act, tab_hist = st.tabs(["📂 Active Positions", "📜 Detailed History"])

with tab_act:
    open_trades = [t for t in st.session_state.trades if t.get('Status') == 'Open']
    if not open_trades: st.info("No active trades.")
    for i, trade in enumerate(open_trades):
        with st.expander(f"🔵 {trade['Symbol']} - {trade['Direction']} ({trade['Remaining Qty']} left)"):
            col_q, col_p, col_c = st.columns(3)
            sq = col_q.number_input("Qty to Sell", 1, trade['Remaining Qty'], key=f"q_{i}")
            sp = col_p.number_input("Exit Price", 0.0, key=f"p_{i}")
            sc = col_c.number_input("Comm ($)", 0.0, key=f"c_{i}")
            
            if st.button(f"Close Partial {trade['Symbol']}", key=f"btn_{i}", type="primary"):
                m = trade.get('Multiplier', 1.0)
                pnl = ((sp - trade['Entry Price']) if trade['Direction'] == "Long" else (trade['Entry Price'] - sp)) * sq * m - sc
                trade.setdefault('Exits', []).append({"qty": sq, "price": sp, "pnl": pnl, "date": datetime.now().strftime("%Y-%m-%d")})
                trade['Remaining Qty'] -= sq
                trade['Total Realized P&L'] += pnl
                if trade['Remaining Qty'] <= 0: 
                    trade['Status'] = "Closed"
                    trade['Exit Date'] = datetime.now().strftime("%Y-%m-%d")
                st.rerun()

with tab_hist:
    closed = [t for t in st.session_state.trades if t.get('Status') == 'Closed']
    for t in closed:
        invested = t['Original Qty'] * t['Entry Price'] * t.get('Multiplier', 1.0)
        pnl = t.get('Total Realized P&L', 0.0)
        roi = (pnl / invested * 100) if invested > 0 else 0
        cls = "history-win" if pnl >= 0 else "history-loss"
        st.markdown(f"""
        <div class="history-card {cls}">
            <div style="display: flex; justify-content: space-between;">
                <b>{t['Symbol']}</b>
                <span class="{'text-green' if pnl >=0 else 'text-red'}">{pnl:+,.2f}$ ({roi:+.2f}%)</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                <div><div class="detail-label">Entry Price</div><div class="detail-value">${t['Entry Price']}</div></div>
                <div><div class="detail-label">Qty</div><div class="detail-value">{t['Original Qty']}</div></div>
                <div><div class="detail-label">Strategy</div><div class="detail-value">{t.get('Strategy')}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with st.sidebar:
    if st.button("➕ NEW TRADE", type="primary", use_container_width=True): open_trade_modal()
    if st.button("⚠️ CLEAR DATA", use_container_width=True):
        st.session_state.trades = []
        st.rerun()