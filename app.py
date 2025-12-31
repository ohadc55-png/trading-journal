import streamlit as st
import pandas as pd
from datetime import datetime
import requests
from supabase import create_client, Client

# ==========================================
# --- CONFIGURATION & SETUP ---
# ==========================================
st.set_page_config(page_title="ProTrade Cloud", layout="wide", page_icon="☁️")

MARKET_API_KEY = 'Y2S0SAL1NRF0Z40J'

FUTURE_MULTIPLIERS = {
    "ES (S&P 500)": 50, "MES (Micro S&P)": 5,
    "NQ (Nasdaq 100)": 20, "MNQ (Micro Nasdaq)": 2,
    "RTY (Russell 2000)": 50, "M2K (Micro Russell)": 5,
    "GC (Gold)": 100, "MGC (Micro Gold)": 10,
    "CL (Crude Oil)": 1000, "SI (Silver)": 5000
}

# --- חיבור למסד הנתונים (ללא Cache - התיקון הקריטי) ---
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        return None

supabase = init_connection()

# --- שחזור Session (מונע את חסימת ה-RLS) ---
if 'session' in st.session_state:
    try:
        supabase.auth.set_session(
            st.session_state.session.access_token,
            st.session_state.session.refresh_token
        )
    except Exception:
        st.session_state.user = None
        st.session_state.session = None

# CSS - תיקנתי את סגירת הגרשיים כדי למנוע את השגיאה
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
        background: #111827;
        border-bottom: 1px solid #374151;
        padding: 10px 20px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-around;
    }
    .history-card { background-color: #1F2937; border-radius: 10px; padding: 20px; margin-bottom: 15px; border-right: 8px solid #374151; }
    .history-win { border-right: 8px solid #34D399; }
    .history-loss { border-right: 8px solid #F87171; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# --- AUTHENTICATION ---
# ==========================================
if 'user' not in st.session_state: st.session_state.user = None

def login_page():
    st.title("🔐 ProTrade Cloud Login")
    t1, t2 = st.tabs(["Log In", "Sign Up"])
    with t1:
        email = st.text_input("Email", key="l_email")
        password = st.text_input("Password", type="password", key="l_pass")
        if st.button("Log In", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.session_state.session = res.session
                st.rerun()
            except Exception as e: st.error(f"Login failed: {e}")
    with t2:
        nem = st.text_input("Email", key="s_email")
        npass = st.text_input("Password", type="password", key="s_pass")
        if st.button("Sign Up"):
            try:
                supabase.auth.sign_up({"email": nem, "password": npass})
                st.success("User created! Check email or log in.")
            except Exception as e: st.error(f"Sign up failed: {e}")

if not st.session_state.user:
    login_page()
    st.stop()

# ==========================================
# --- API & MARKET DATA ---
# ==========================================
@st.cache_data(ttl=60)
def fetch_market_price(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={MARKET_API_KEY}"
        res = requests.get(url, timeout=5).json()
        q = res.get('Global Quote', {})
        return {
            'price': float(q.get('05. price', 0)),
            'change_pct': float(q.get('10. change percent', '0').replace('%', ''))
        }
    except: return None

def display_ticker():
    st.markdown("### 🌍 Live Market")
    indices = [("SPY", "S&P 500"), ("QQQ", "Nasdaq"), ("GLD", "Gold")]
    cols = st.columns(len(indices))
    for i, (sym, name) in enumerate(indices):
        data = fetch_market_price(sym)
        if data:
            c = "text-green" if data['change_pct'] >= 0 else "text-red"
            cols[i].markdown(f"**{name}**<br><span style='font-size:1.2rem;'>${data['price']:.2f}</span> <small class='{c}'>{data['change_pct']:+.2f}%</small>", unsafe_allow_html=True)

# ==========================================
# --- DB HELPERS ---
# ==========================================
user_id = st.session_state.user.id

def fetch_trades():
    return supabase.table('trades').select('*').order('created_at', desc=True).execute().data

def fetch_exits(trade_id):
    return supabase.table('exits').select('*').eq('trade_id', trade_id).execute().data

# ==========================================
# --- MAIN APP ---
# ==========================================
display_ticker()
st.sidebar.title(f"👤 {st.session_state.user.email}")
if st.sidebar.button("Log Out"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.session = None
    st.rerun()

# --- MODAL: NEW TRADE ---
@st.dialog("🚀 New Trade Entry")
def open_trade_modal():
    asset = st.selectbox("Asset Class", ["Stock", "Future", "Option"])
    
    symbol_final = ""
    multiplier = 1.0
    
    if asset == "Stock":
        symbol_final = st.text_input("Ticker Symbol").upper()
    
    elif asset == "Future":
        fut_key = st.selectbox("Contract", list(FUTURE_MULTIPLIERS.keys()))
        symbol_final = fut_key.split(" ")[0]
        multiplier = FUTURE_MULTIPLIERS[fut_key]
        
    elif asset == "Option":
        c1, c2 = st.columns(2)
        und = c1.text_input("Underlying").upper()
        o_type = c2.selectbox("Type", ["Call", "Put"])
        c3, c4 = st.columns(2)
        strike = c3.text_input("Strike")
        exp = c4.date_input("Expiry")
        symbol_final = f"{und} {o_type} {strike} {exp.strftime('%d%b%y')}"
        multiplier = 100.0

    st.divider()
    
    c1, c2 = st.columns(2)
    direction = c1.radio("Direction", ["Long", "Short"], horizontal=True)
    qty = c2.number_input("Quantity", min_value=1, value=1)
    
    p1, p2 = st.columns(2)
    entry_date = p1.date_input("Entry Date")
    entry_price = p2.number_input("Entry Price ($)", min_value=0.01, format="%.2f")
    
    strategy = st.selectbox("Strategy", ["Breakout", "Pullback", "Trend", "Reversal"])
    
    if st.button("Open Position", type="primary", use_container_width=True):
        new_trade = {
            "user_id": user_id,
            "asset_class": asset,
            "symbol": symbol_final,
            "direction": direction,
            "entry_date": entry_date.strftime("%Y-%m-%d"),
            "entry_price": entry_price,
            "original_qty": qty,
            "remaining_qty": qty,
            "multiplier": multiplier,
            "status": "Open",
            "strategy": strategy
        }
        
        try:
            # כאן היה הבאג הקודם - תוקן ע"י הסרת ה-Cache למעלה
            supabase.table('trades').insert(new_trade).execute()
            st.success("Trade Saved to Cloud!")
            st.rerun()
        except Exception as e:
            st.error(f"Error saving trade: {e}")

if st.sidebar.button("➕ NEW TRADE", type="primary"):
    open_trade_modal()

# --- DASHBOARD ---
st.title("📈 ProTrade Journal Cloud")

my_trades = fetch_trades()
open_trades = [t for t in my_trades if t['status'] == 'Open']

total_realized_pnl = 0 
# לוגיקה עתידית: סיכום PnL ממומש

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="metric-card"><div class="metric-label">Open Trades</div><div class="metric-value">{len(open_trades)}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card"><div class="metric-label">Est. Realized P&L</div><div class="metric-value text-green">${total_realized_pnl}</div></div>', unsafe_allow_html=True)

# --- TABS ---
t_active, t_hist = st.tabs(["📂 Active Trades", "📜 History"])

with t_active:
    if not open_trades: st.info("No active trades.")
    for t in open_trades:
        with st.expander(f"🔵 {t['symbol']} | {t['direction']} | Rem: {t['remaining_qty']}"):
            cq, cp = st.columns(2)
            sq = cq.number_input("Qty to Sell", 1, t['remaining_qty'], key=f"q_{t['id']}")
            sp = cp.number_input("Exit Price", 0.0, key=f"p_{t['id']}")
            
            if st.button("Execute Sale", key=f"btn_{t['id']}"):
                m = float(t['multiplier'])
                entry = float(t['entry_price'])
                diff = (sp - entry) if t['direction'] == "Long" else (entry - sp)
                pnl = diff * sq * m
                
                try:
                    supabase.table('exits').insert({
                        "trade_id": t['id'], "exit_qty": sq, "exit_price": sp, "pnl": pnl
                    }).execute()
                    
                    new_rem = t['remaining_qty'] - sq
                    upd = {"remaining_qty": new_rem}
                    if new_rem <= 0: upd["status"] = "Closed"
                    
                    supabase.table('trades').update(upd).eq('id', t['id']).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error closing trade: {e}")

with t_hist:
    closed = [t for t in my_trades if t['status'] == 'Closed']
    if not closed: st.write("History is empty.")
    for t in closed:
        exits = fetch_exits(t['id'])
        final_pnl = sum(e['pnl'] for e in exits)
        cls = "history-win" if final_pnl >= 0 else "history-loss"
        clr = "text-green" if final_pnl >= 0 else "text-red"
        
        st.markdown(f"""
        <div class="history-card {cls}">
            <div style="display: flex; justify-content: space-between;">
                <b>{t['symbol']}</b>
                <span class="{clr}">{final_pnl:+,.2f}$</span>
            </div>
            <small>Strategy: {t.get('strategy', 'N/A')}</small>
        </div>
        """, unsafe_allow_html=True)