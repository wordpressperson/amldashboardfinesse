import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

# --- Configuration & Secrets ---
# You can set these in your environment or Streamlit secrets
API_IP = os.getenv("API_IP", "YOUR_BACKEND_IP")
JWT_TOKEN = os.getenv("JWT_TOKEN", "YOUR_JWT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_KEY")

# --- Page Config ---
st.set_page_config(
    page_title="AML Monitoring Dashboard", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for Finesse ---
st.markdown("""
    <style>
    /* Hide Streamlit Default UI */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Adjust main container padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
    }
    
    /* Style the metric cards */
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 5% 5% 5% 10%;
        border-radius: 10px;
        color: #FFFFFF;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Style the metric labels */
    div[data-testid="metric-container"] label {
        color: #A0AEC0 !important;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    
    /* Style dataframe headers */
    .stDataFrame {
        border-radius: 8px !important;
        border: 1px solid #333 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Mock Data Generation ---
np.random.seed(42)
hours = [f"{h}:00" for h in range(8, 16)]
transactions_valid = np.random.randint(5, 20, size=len(hours))
transactions_fraud = np.random.randint(1, 10, size=len(hours))

# --- Dashboard Layout ---
st.markdown("<h2 style='text-align: center; color: #E2E8F0; margin-bottom: 30px;'>AML Transaction Risks Monitoring</h2>", unsafe_allow_html=True)

# 1. Top KPI Row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Transactions", "36,421", "+1.2% today")
col2.metric("Unusual Transactions", "250", "-5 since yesterday")
col3.metric("Amount Transacted", "$36.18M", "High Volume")
col4.metric("Alerts in SLA", "89%", "Target: 100%")

st.markdown("<br>", unsafe_allow_html=True)

# 2. Charts Row
col_chart1, col_chart2 = st.columns([2, 1])

with col_chart1:
    st.markdown("<h4 style='color: #A0AEC0;'>Recent Activity Flow</h4>", unsafe_allow_html=True)
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=hours, y=transactions_valid, name='Valid', marker_color='#D4AF37')) 
    fig_bar.add_trace(go.Bar(x=hours, y=transactions_fraud, name='Flagged', marker_color='#E53E3E')) 
    
    fig_bar.update_layout(
        barmode='stack',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#A0AEC0'),
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

with col_chart2:
    st.markdown("<h4 style='color: #A0AEC0;'>Verification Status</h4>", unsafe_allow_html=True)
    labels = ['Verified Valid', 'Confirmed Fraud', 'Unassigned']
    values = [130, 80, 40]
    colors = ['#D4AF37', '#E53E3E', '#4A5568']
    
    fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.7, marker=dict(colors=colors))])
    fig_donut.update_layout(
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0),
        annotations=[dict(text='250<br>Alerts', x=0.5, y=0.5, font_size=20, showarrow=False, font_color='#E2E8F0')]
    )
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

# 3. Bottom Row: Ongoing Investigations Table
st.markdown("<h4 style='color: #A0AEC0; margin-top: 20px;'>High-Priority Alerts & Investigations</h4>", unsafe_allow_html=True)

df_investigations = pd.DataFrame({
    "Client": ["Johnson", "Martha", "Corp LLC", "Doe"],
    "Alert Reason": [">10 transactions same day", ">25 transactions same month", "Structuring detected", "High-risk jurisdiction"],
    "Amount": ["$550,000", "$2,550,000", "$85,000", "$120,000"],
    "Status": ["Investigation Opened", "In Peer Review", "Confirmed Unusual", "Pending"]
})

st.dataframe(
    df_investigations,
    use_container_width=True,
    hide_index=True,
)
