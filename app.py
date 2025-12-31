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

# --- חיבור למסד הנתונים (ללא Cache - התיקון שלך!) ---
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        return None

supabase = init_connection()

# --- שחזור Session (קריטי ל-RLS) ---
if 'session' in st.session_state:
    try:
        supabase.auth.set_session(
            st.session_state.session.access_token,
            st.session_state.session.refresh_token
        )
    except Exception as e:
        # אם הטוקן פג תוקף - נבקש התחברות מחדש
        st.session_state.user = None
        st.session_state.session = None

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