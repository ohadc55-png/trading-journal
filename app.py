import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# --- CONFIGURATION & PRO UI STYLING ---
# ==========================================
st.set_page_config(page_title="ProTrade Journal", layout="wide", page_icon="📈")

# עיצוב CSS מתקדם לממשק כהה ומקצועי
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
    
    .trade-container { background-color: #111827; border: 1px solid #374151; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
    
    /* עיצוב כרטיסי היסטוריה מפורטים */
    .history-card {
        background-color: #1F2937;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        border-right: 8px solid #374151;
    }
    .history-win { border-right: 8px solid #34D399; }
    .history-loss { border-right: 8px solid #F87171; }
    
    .detail-label { color: #9CA3AF; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 2px; }
    .detail-value { color: #E5E7EB; font-weight: 600; font-size: 1rem; }
    .divider { border-top: 1px solid #374151; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZE STATE ---
if 'trades' not in st.session_state:
    st.session_state.trades = []
if 'initial_capital' not in st.session_state:
    st.session_state.initial_capital = 10000.0

# --- CONSTANTS ---
FUTURE_MULTIPLIERS = { "ES (S&P 500)": 50, "MES (Micro S&P)": 5, "NQ (Nasdaq 100)": 20, "MNQ (Micro Nasdaq)": 2, "GC (Gold)": 100, "CL (Crude Oil)": 1000 }

# ==========================================
# --- MODAL: NEW TRADE ENTRY ---
# ==========================================
@st.dialog("🚀 New Trade Entry")
def open_trade_modal():
    asset_class = st.selectbox("Asset Class", ["Stock", "Future", "Option"])
    symbol = ""
    multiplier = 1.0
    if asset_class == "Stock": symbol = st.text_input("Ticker Symbol").upper()
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
    with c_price: entry_price = st.number_input("Entry Price ($)", min_value=0.00, format="%.2f")
    
    reason = st.text_area("Strategy / Notes")
    
    if st.button("Open Position", type="primary", use_container_width=True):
        new_trade = {
            "ID": len(st.session_state.trades) + 1,
            "Asset Class": asset_class,
            "Symbol": symbol,
            "Direction": direction,
            "Entry Date": entry_date.strftime("%Y-%m-%d"), 
            "Entry Price": entry_price,
            "Original Qty": qty,
            "Remaining Qty": qty,
            "Multiplier": multiplier,
            "Exits": [], 
            "Total Realized P&L": 0.0,
            "Status": "Open",
            "Reason": reason
        }
        st.session_state.trades.append(new_trade)
        st.rerun()

# ==========================================
# --- SIDEBAR & RESET ---
# ==========================================
with st.sidebar:
    st.title("⚙️ Controls")
    if st.button("➕ NEW TRADE", type="primary", use_container_width=True):
        open_trade_modal()
    st.markdown("---")
    st.session_state.initial_capital = st.number_input("Account Start ($)", value=st.session_state.initial_capital)
    if st.button("⚠️ CLEAR SESSION & DATA", use_container_width=True):
        st.session_state.trades = []
        st.rerun()

# חישובים כלליים לדשבורד (שימוש ב-get למניעת KeyError)
total_pnl = sum(t.get('Total Realized P&L', 0.0) for t in st.session_state.trades)
curr_equity = st.session_state.initial_capital + total_pnl
account_roi = (total_pnl / st.session_state.initial_capital * 100) if st.session_state.initial_capital > 0 else 0.0

# ==========================================
# --- DASHBOARD ---
# ==========================================
def kpi(title, value, is_money=True, color_logic=False, is_percent=False):
    color_class = ""
    if color_logic:
        if value > 0: color_class = "text-green"
        elif value < 0: color_class = "text-red"
    val_fmt = f"${value:,.2f}" if is_money else (f"{value:+.2f}%" if is_percent else str(value))
    return f'<div class="metric-card"><div class="metric-label">{title}</div><div class="metric-value {color_class}">{val_fmt}</div></div>'

st.markdown("## 📊 Portfolio Dashboard")
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(kpi("Current Equity", curr_equity), unsafe_allow_html=True)
with c2: st.markdown(kpi("Total Realized P&L", total_pnl, True, True), unsafe_allow_html=True)
with c3: st.markdown(kpi("Account ROI", account_roi, False, True, True), unsafe_allow_html=True)
with c4: st.markdown(kpi("Open Trades", len([t for t in st.session_state.trades if t.get('Status') == 'Open']), False), unsafe_allow_html=True)

# ==========================================
# --- MAIN TABS ---
# ==========================================
st.markdown("---")
tab_active, tab_history = st.tabs(["📂 Active Trades", "📜 Detailed History"])

# --- טאב עסקאות פעילות (Scaling Out) ---
with tab_active:
    open_trades = [t for t in st.session_state.trades if t.get('Status') == 'Open']
    if not open_trades:
        st.info("No active trades.")
    else:
        for i, trade in enumerate(st.session_state.trades):
            if trade.get('Status') == 'Open':
                st.markdown(f'<div class="trade-container"><b>{trade.get("Symbol")}</b> | {trade.get("Direction")} | Entry: ${trade.get("Entry Price")} | Remaining: {trade.get("Remaining Qty")}</div>', unsafe_allow_html=True)
                with st.expander(f"Manage / Scale Out {trade.get('Symbol')}"):
                    c_q, c_p, c_c = st.columns(3)
                    rem = trade.get('Remaining Qty', 0)
                    sq = c_q.number_input("Qty to Sell", 1, max(1, rem), key=f"q_{i}")
                    sp = c_p.number_input("Exit Price", 0.0, format="%.2f", key=f"p_{i}")
                    sc = c_c.number_input("Comm ($)", 0.0, key=f"c_{i}")
                    
                    if st.button("Close Partial / Full", key=f"b_{i}", use_container_width=True):
                        mult = trade.get('Multiplier', 1.0)
                        # חישוב רווח לחלק שנמכר
                        if trade.get('Direction') == "Long":
                            part_pnl = (sp - trade.get('Entry Price', 0)) * sq * mult - sc
                        else:
                            part_pnl = (trade.get('Entry Price', 0) - sp) * sq * mult - sc
                        
                        trade.setdefault('Exits', []).append({
                            "qty": sq, "price": sp, "pnl": part_pnl, "comm": sc, "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        trade['Remaining Qty'] -= sq
                        trade['Total Realized P&L'] = trade.get('Total Realized P&L', 0.0) + part_pnl
                        
                        if trade['Remaining Qty'] <= 0:
                            trade['Status'] = "Closed"
                        st.rerun()

# --- טאב היסטוריה מפורטת (דרישת המשתמש) ---
with tab_history:
    closed = [t for t in st.session_state.trades if t.get('Status') == 'Closed']
    if not closed:
        st.write("History is empty.")
    else:
        for t in closed:
            # אגרגציה וחישוב נתונים לסיכום הטרייד
            mult = t.get('Multiplier', 1.0)
            total_invested = t.get('Original Qty', 0) * t.get('Entry Price', 0) * mult
            
            exits = t.get('Exits', [])
            total_sold_value = sum(e['qty'] * e['price'] * mult for e in exits)
            total_sold_qty = sum(e['qty'] for e in exits)
            total_comm = sum(e.get('comm', 0) for e in exits)
            
            avg_exit_price = (total_sold_value / (total_sold_qty * mult)) if (total_sold_qty * mult) > 0 else 0
            last_exit_date = exits[-1]['date'] if exits else "N/A"
            
            final_pnl = t.get('Total Realized P&L', 0.0)
            final_roi = (final_pnl / total_invested * 100) if total_invested > 0 else 0
            
            # עיצוב צבעים לפי תוצאה
            card_class = "history-win" if final_pnl >= 0 else "history-loss"
            text_class = "text-green" if final_pnl >= 0 else "text-red"
            
            st.markdown(f"""
            <div class="history-card {card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 1.4rem; font-weight: bold;">{t.get('Symbol')} <small style="font-weight: normal; color: #9CA3AF;">({t.get('Asset Class')})</small></span>
                    <span class="{text_class}" style="font-size: 1.4rem; font-weight: bold;">
                        {"+" if final_pnl >= 0 else ""}{final_pnl:,.2f}$ ({final_roi:+.2f}%)
                    </span>
                </div>
                <div class="divider"></div>
                <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 15px;">
                    <div style="min-width: 150px;">
                        <div class="detail-label">Dates (Buy / Last Sell)</div>
                        <div class="detail-value">{t.get('Entry Date')} / {last_exit_date}</div>
                    </div>
                    <div style="min-width: 150px;">
                        <div class="detail-label">Buy / Avg Sell Price</div>
                        <div class="detail-value">${t.get('Entry Price', 0):.2f} / ${avg_exit_price:.2f}</div>
                    </div>
                    <div style="min-width: 150px;">
                        <div class="detail-label">Qty (Bought / Sold)</div>
                        <div class="detail-value">{t.get('Original Qty')} / {total_sold_qty}</div>
                    </div>
                    <div style="min-width: 150px;">
                        <div class="detail-label">Invested / Sold Value</div>
                        <div class="detail-value">${total_invested:,.2f} / ${total_sold_value:,.2f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)