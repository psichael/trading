import os
import time
import shutil
import pandas as pd
import numpy as np
import pytz
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="Forge Command Center", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 10px; }
        .buy-alert { color: #2ca02c; font-weight: bold; }
        .sell-alert { color: #d62728; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FILE LOCATOR ---
current_dir = os.path.dirname(os.path.abspath(__file__)) 
potential_paths = [
    os.path.join(current_dir, 'data_code', 'history', 'telemetry.csv'),
    os.path.join(current_dir, 'history', 'telemetry.csv'),
    os.path.join(os.path.dirname(current_dir), 'history', 'telemetry.csv'),
    os.path.join(os.path.dirname(current_dir), 'live', 'data_code', 'history', 'telemetry.csv')
]
telemetry_file = next((p for p in potential_paths if os.path.exists(p)), None)

# --- PERSISTENT STATE ---
if 'alert_log' not in st.session_state:
    st.session_state.alert_log = []
if 'last_signals' not in st.session_state:
    st.session_state.last_signals = {}

def load_data_safely():
    if not telemetry_file: return pd.DataFrame(), "Path not found"
    try:
        temp_file = telemetry_file + ".tmp"
        shutil.copy2(telemetry_file, temp_file)
        df = pd.read_csv(temp_file)
        if os.path.exists(temp_file): os.remove(temp_file)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        return df, "Success"
    except Exception as e: return pd.DataFrame(), str(e)

@st.fragment(run_every=30)
def render_content():
    df, status = load_data_safely()
    if df.empty:
        st.error(f"❌ Dashboard is Blind: {status}")
        return

    tickers = sorted(df['ticker'].unique())
    latest_all = df.sort_values('timestamp').groupby('ticker').last()
    
    # 🎨 Color Palette
    asset_colors = px.colors.qualitative.Bold
    color_map = {ticker: asset_colors[i % len(asset_colors)] for i, ticker in enumerate(tickers)}

    # --- LOGIC: DETECT SIGNAL FLIPS & BUILD TABLE ---
    trading_data = []
    total_unrealized_pct = 0
    active_count = 0

    for ticker in tickers:
        t_hist = df[df['ticker'] == ticker].sort_values('timestamp')
        latest = t_hist.iloc[-1]
        current_signal = latest['signal']
        
        # Check for State Change (Alert Log)
        if ticker in st.session_state.last_signals:
            prev_signal = st.session_state.last_signals[ticker]
            if prev_signal == 'WAIT' and current_signal == 'LONG':
                st.session_state.alert_log.insert(0, {"Time": latest['timestamp'].strftime('%H:%M:%S'), "Asset": ticker, "Action": "🚀 BUY / ENTRY", "Price": f"${latest['price']:.4f}"})
            elif prev_signal == 'LONG' and current_signal == 'WAIT':
                st.session_state.alert_log.insert(0, {"Time": latest['timestamp'].strftime('%H:%M:%S'), "Asset": ticker, "Action": "📉 SELL / EXIT", "Price": f"${latest['price']:.4f}"})
        
        st.session_state.last_signals[ticker] = current_signal

        # Table Logic
        buy_price = 0
        pnl_pct = 0.0
        status_text = "⏳ WATCHING"
        
        if current_signal == 'LONG':
            status_text = "✅ TRADING"
            active_count += 1
            
            non_longs = t_hist[t_hist['signal'] != 'LONG']
            if not non_longs.empty:
                last_non_long_time = non_longs.iloc[-1]['timestamp']
                current_streak = t_hist[t_hist['timestamp'] > last_non_long_time]
            else:
                current_streak = t_hist
                
            if not current_streak.empty:
                buy_price = current_streak.iloc[0]['price']
                pnl_pct = ((latest['price'] - buy_price) / buy_price) * 100
                total_unrealized_pct += pnl_pct

        trading_data.append({
            "Ticker": ticker, "Status": status_text, "Price": f"${latest['price']:.4f}",
            "Entry": f"${buy_price:.4f}" if buy_price > 0 else "-",
            "PnL %": f"{pnl_pct:+.2f}%" if current_signal == 'LONG' else "0.00%",
            "RDS": f"{latest.get('m5_rds', 0):.4f}", "Flux": f"{latest['h1_flux']:.2f}"
        })

    # ==========================================
    # ROW 1: ACCELERATOR & PNL
    # ==========================================
    col_viz, col_pnl = st.columns([2, 1])
    with col_viz:
        st.write("### ⚛️ Particle Accelerator")
        fig_radar = go.Figure()
        for ticker in tickers:
            t_data = df[df['ticker'] == ticker].tail(25)
            if t_data.empty: continue
            r_coords = t_data['h1_flux'].values
            base_angle = (tickers.index(ticker) * (360 / len(tickers)))
            theta_coords = (base_angle + (t_data['m5_state'].cumsum() / 12)) % 360
            
            l_node = t_data.iloc[-1]
            h_color = '#00FF00' if l_node['signal'] == 'LONG' else ('#FFA500' if l_node.get('m5_rds', 5.0) < 1.04 else color_map[ticker])
            fig_radar.add_trace(go.Scatterpolar(r=r_coords, theta=theta_coords, mode='lines+markers', name=ticker,
                                                line=dict(color=color_map[ticker], width=2),
                                                marker=dict(size=[0]*(len(t_data)-1) + [25], color=h_color, line=dict(color='white', width=2))))
        fig_radar.update_layout(template="plotly_white", height=550, polar=dict(radialaxis=dict(range=[0, 110])), margin=dict(t=20, b=20))
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_pnl:
        st.write("### 📈 Performance")
        st.metric("Active Trades", active_count)
        st.metric("Est. PnL Sum", f"{total_unrealized_pct:+.2f}%")
        opportunity_heat = df[df['ticker'].isin(latest_all[latest_all['signal'] == 'LONG'].index)].groupby('timestamp')['h1_flux'].mean()
        if not opportunity_heat.empty: st.line_chart(opportunity_heat, height=200)

    # ==========================================
    # ROW 2: LIVE ROSTER
    # ==========================================
    st.divider()
    st.write("### 📊 Active Roster")
    st.dataframe(pd.DataFrame(trading_data).sort_values("Status", ascending=False), hide_index=True, use_container_width=True)

    # ==========================================
    # ROW 3: DRILL-DOWN & ALERTS
    # ==========================================
    st.divider()
    c_drill, c_alerts = st.columns([2, 1])
    
    with c_drill:
        active_ticker = st.radio("Inspect Particle:", tickers, horizontal=True)
        t_df = df[df['ticker'] == active_ticker].tail(8640)
        
        # Remove overnight flatlines for equities to show true trading action
        if 'usd' not in active_ticker.lower() and not t_df.empty:
            try:
                local_tz = datetime.now().astimezone().tzinfo
                est_times = t_df['timestamp'].dt.tz_localize(local_tz).dt.tz_convert('US/Eastern')
                mask = (est_times.dt.weekday <= 4) & \
                       ((est_times.dt.hour > 9) | ((est_times.dt.hour == 9) & (est_times.dt.minute >= 30))) & \
                       (est_times.dt.hour < 16)
                t_df = t_df[mask]
            except Exception:
                pass
                
        fig_detail = make_subplots(specs=[[{"secondary_y": True}]])
        fig_detail.add_trace(go.Scatter(x=t_df['timestamp'], y=t_df['price'], name="Price", line=dict(color=color_map[active_ticker], width=4)), secondary_y=False)
        fig_detail.add_trace(go.Scatter(x=t_df['timestamp'], y=t_df['m5_state'], name="M5 Kinetic", fill='tozeroy', line=dict(width=0, color='rgba(0,0,0,0.1)')), secondary_y=True)
        fig_detail.add_trace(go.Scatter(x=t_df['timestamp'], y=t_df['m5_rds'], name="RDS", line=dict(color='red', width=1.5)), secondary_y=True)
        fig_detail.add_hline(y=1.04, line_dash="dash", line_color="red", secondary_y=True)
        fig_detail.update_layout(template="plotly_white", height=350, margin=dict(t=0, b=0))
        st.plotly_chart(fig_detail, use_container_width=True)

    with c_alerts:
        st.write("### 🔔 Alert Log")
        if not st.session_state.alert_log:
            st.info("Waiting for first live state flip...")
        else:
            alert_df = pd.DataFrame(st.session_state.alert_log).head(10)
            st.table(alert_df)

st.title("LiveGatedForge: Command Center")
render_content()
