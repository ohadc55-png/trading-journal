import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import requests

# ==========================================
# --- CONFIGURATION & SETUP ---
# ==========================================
st.set_page_config(page_title="ProTrade Journal Cloud", layout="wide", page_icon="☁️")

# חיבור למסד הנתונים באמצעות ה-Secrets שהגדרת
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# CSS עיצוב
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
    .metric-value { color: #F3F4F6; font-size: 1.8rem; font-weight: 700; }
    .metric-label { color: #9CA3AF; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; }
    .text-green { color: #34D399 !important; }
    .text-red { color: #F87171 !important; }
    .history-card { background-color: #1F2937; border-radius: 10px; padding: 20px; margin-bottom: 15px; border-right: 8px solid #374151; }
    .history-win { border-right: 8px solid #34D399; }
    .history-loss { border-right: 8px solid #F87171; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# --- AUTHENTICATION (מערכת כניסה) ---
# ==========================================
if 'user' not in st.session_state:
    st.session_state.user = None

def login_page():
    st.title("🔐 ProTrade Login")
    
    tab1, tab2 = st.tabs(["Log In", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In", type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                
    with tab2:
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Sign Up"):
            try:
                res = supabase.auth.sign_up({"email": new_email, "password": new_password})
                st.success("Account created! Please check your email to verify (or log in if auto-confirmed).")
            except Exception as e:
                st.error(f"Error: {e}")

# אם המשתמש לא מחובר - תעצור כאן ותציג מסך כניסה
if not st.session_state.user:
    login_page()
    st.stop()

# ==========================================
# --- DATA MANAGEMENT (DB Functions) ---
# ==========================================
user_id = st.session_state.user.id

def fetch_trades():
    # שליפת טריידים מהמסד (RLS דואג שנראה רק את שלנו)
    response = supabase.table('trades').select('*').order('created_at', desc=True).execute()
    return response.data

def fetch_exits(trade_id):
    response = supabase.table('exits').select('*').eq('trade_id', trade_id).execute()
    return response.data

# ==========================================
# --- MAIN APP LOGIC ---
# ==========================================
st.sidebar.title(f"👤 {st.session_state.user.email}")
if st.sidebar.button("Log Out"):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# Modal: New Trade
@st.dialog("🚀 New Trade Entry")
def open_trade_modal():
    asset = st.selectbox("Asset Class", ["Stock", "Future", "Option"])
    symbol = st.text_input("Symbol").upper()
    multiplier = 100.0 if asset == "Option" else 1.0
    
    c1, c2 = st.columns(2)
    direction = c1.radio("Direction", ["Long", "Short"], horizontal=True)
    qty = c2.number_input("Quantity", min_value=1, value=1)
    
    p1, p2 = st.columns(2)
    entry_date = p1.date_input("Entry Date")
    entry_price = p2.number_input("Entry Price ($)", min_value=0.01)
    
    strategy = st.selectbox("Strategy", ["Breakout", "Pullback", "Trend", "Level"])
    
    if st.button("Open Position", type="primary"):
        new_trade = {
            "user_id": user_id,
            "asset_class": asset,
            "symbol": symbol,
            "direction": direction,
            "entry_date": entry_date.strftime("%Y-%m-%d"),
            "entry_price": entry_price,
            "original_qty": qty,
            "remaining_qty": qty,
            "multiplier": multiplier,
            "status": "Open",
            "strategy": strategy
        }
        # שמירה ב-Supabase
        supabase.table('trades').insert(new_trade).execute()
        st.rerun()

# ==========================================
# --- DASHBOARD ---
# ==========================================
st.title("📈 ProTrade Cloud")

# שליפת נתונים בזמן אמת מהמסד
my_trades = fetch_trades()
open_trades = [t for t in my_trades if t['status'] == 'Open']

# חישוב P&L כולל (דורש לוגיקה מסוימת כי הנתונים מגיעים כרשימה)
# הערה: כרגע נציג P&L ממומש בסיסי אם יש עמודת P&L בטבלה, או נחשב דינמית בעתיד
# לצורך פשטות: נניח שיש לנו שדה מחושב או שנחשב מקומית
total_pnl = 0 
# כאן נוכל להוסיף לוגיקה מורכבת יותר של שליפת ה-Exits וסיכום הרווח

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="metric-card"><div class="metric-label">Open Trades</div><div class="metric-value">{len(open_trades)}</div></div>', unsafe_allow_html=True)

# כפתור הוספה
if st.sidebar.button("➕ NEW TRADE", type="primary"):
    open_trade_modal()

# ==========================================
# --- TABS ---
# ==========================================
tab_act, tab_hist = st.tabs(["📂 Active Trades", "📜 History"])

with tab_act:
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
                
                # 1. הוספת רשומה לטבלת exits
                supabase.table('exits').insert({
                    "trade_id": t['id'],
                    "exit_qty": sq,
                    "exit_price": sp,
                    "pnl": pnl
                }).execute()
                
                # 2. עדכון טבלת trades
                new_rem = t['remaining_qty'] - sq
                update_data = {"remaining_qty": new_rem}
                if new_rem <= 0:
                    update_data["status"] = "Closed"
                
                supabase.table('trades').update(update_data).eq('id', t['id']).execute()
                st.rerun()

with tab_hist:
    closed = [t for t in my_trades if t['status'] == 'Closed']
    if not closed: st.write("History is empty.")
    for t in closed:
        # כאן צריך לשלוף את ה-Exits כדי לחשב P&L סופי
        exits = fetch_exits(t['id'])
        total_trade_pnl = sum(e['pnl'] for e in exits)
        
        cls = "history-win" if total_trade_pnl >= 0 else "history-loss"
        clr = "text-green" if total_trade_pnl >= 0 else "text-red"
        
        st.markdown(f"""
        <div class="history-card {cls}">
            <div style="display: flex; justify-content: space-between;">
                <b>{t['symbol']}</b>
                <span class="{clr}">Total P&L: ${total_trade_pnl:,.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)