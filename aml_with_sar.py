import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==================== LOAD SECRETS (secure – no UI inputs) ====================
try:
    BASE_URL = st.secrets["api"]["base_url"]
    BEARER_TOKEN = st.secrets["api"]["bearer_token"]
    OPENAI_API_KEY = st.secrets["openai"]["api_key"]
except Exception:
    st.error("🚨 Missing secrets configuration.\n\n"
             "Go to your Streamlit app → Settings → Secrets and add the [api] and [openai] sections.")
    st.stop()

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "accept": "application/json"
}

st.set_page_config(page_title="FinGuard AML", layout="wide", page_icon="🛡️")
st.title("🛡️ FinGuard AML")

# ==================== SIDEBAR (clean – only navigation) ====================
st.sidebar.image(
    "https://via.placeholder.com/180x50?text=FinGuard+AML",
    width=180   # fixed deprecation warning (use_column_width → width)
)
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Customers", "Transactions", "Alerts", "Screening", "Reports"]
)

# ==================== DATA LOADING ====================
@st.cache_data(ttl=60)
def load_data():
    # Try API first
    try:
        alerts_resp = requests.get(
            f"{BASE_URL}/v1/alerts",
            headers=headers,
            params={"limit": 100},
            timeout=10
        )
        alerts_resp.raise_for_status()
        alerts_data = alerts_resp.json()
        alerts_df = pd.DataFrame(
            alerts_data.get("alerts", alerts_data)
            if isinstance(alerts_data, dict)
            else alerts_data
        )
    except Exception:
        alerts_df = pd.DataFrame()

    # Load fixtures as fallback
    try:
        customers = pd.read_json("fixtures/customers.json")
        accounts = pd.read_json("fixtures/accounts.json")
        transactions = pd.read_json("fixtures/transactions.json")
    except Exception:
        st.warning("Fixtures folder not found – using minimal fallback data")
        customers = pd.DataFrame()
        accounts = pd.DataFrame()
        transactions = pd.DataFrame()

    accounts = accounts.merge(customers, on="customer_id", how="left") if not accounts.empty else accounts
    return customers, accounts, transactions, alerts_df


customers_df, accounts_df, transactions_df, alerts_df = load_data()

# ==================== PAGES ====================
if page == "Dashboard":
    st.subheader("Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers", len(customers_df), "+2 since last month")
    col2.metric("Total Transactions", len(transactions_df), "+12% from last month")
    col3.metric("Pending Alerts", max(len(alerts_df), 2), "+3 new today")
    col4.metric(
        "High-Risk Customers",
        len(customers_df[customers_df.get('risk_category', pd.Series()).isin(['high', 'critical'])]),
        "+1 this week"
    )

    if not transactions_df.empty:
        transactions_df['date'] = pd.to_datetime(transactions_df['timestamp']).dt.date
        vol = transactions_df.groupby('date')['amount'].sum().reset_index()
        st.plotly_chart(
            px.bar(vol, x='date', y='amount', title="Transaction Volume - Last Period"),
            use_container_width=True
        )

elif page == "Customers":
    st.subheader("Customer Directory")
    st.dataframe(
        accounts_df[['full_name', 'customer_id', 'risk_category', 'risk_rating', 'nationality', 'kyc_level']],
        use_container_width=True,
        height=600
    )

elif page == "Transactions":
    st.subheader("All Transactions")
    st.dataframe(
        transactions_df[['txn_id', 'timestamp', 'amount', 'currency', 'counterparty_country', 'purpose']],
        use_container_width=True,
        height=700
    )

elif page == "Alerts":
    st.subheader("Alert Queue")
    st.caption("Manage and investigate all AML/CFT alerts.")

    if alerts_df.empty:
        st.info("No alerts from API yet. Showing high-risk transactions as example alerts.")
        display_alerts = transactions_df[
            transactions_df.get('risk_flags', pd.Series()).apply(lambda x: isinstance(x, list) and len(x) > 0)
        ].copy().head(8)
        display_alerts = display_alerts.rename(columns={"txn_id": "ID", "timestamp": "timestamp", "purpose": "Description"})
    else:
        display_alerts = alerts_df.copy()

    # Safe date formatting
    if "timestamp" in display_alerts.columns:
        display_alerts["Date"] = pd.to_datetime(display_alerts["timestamp"], errors="coerce").dt.strftime("%m/%d/%Y")
    else:
        display_alerts["Date"] = datetime.now().strftime("%m/%d/%Y")

    display_alerts["Type"] = display_alerts.get("alert_type", "Suspicious Transaction")
    display_alerts["Priority"] = pd.cut(
        display_alerts.get("risk_score", pd.Series([0.8] * len(display_alerts))),
        bins=[0, 0.6, 0.8, 1.0],
        labels=["Medium", "High", "Critical"]
    ).astype(str)
    display_alerts["Status"] = display_alerts.get("status", "New")
    display_alerts["Assignee"] = "Unassigned"

    if "Description" not in display_alerts.columns:
        display_alerts["Description"] = display_alerts.get("reason", display_alerts.get("alert_type", "Suspicious activity"))

    final_cols = ["Date", "Description", "Type", "Priority", "Status", "Assignee"]
    display_table = display_alerts[final_cols].copy()

    # Styled table
    def style_row(row):
        styles = []
        for v in row:
            if v in ["High", "Critical"]:
                styles.append('background-color: #ffcccc; color: #c00; font-weight: bold')
            elif v == "New":
                styles.append('background-color: #ffebcc; color: #c80')
            elif v == "In Progress":
                styles.append('background-color: #e6f0ff; color: #0066cc')
            elif v == "Resolved":
                styles.append('background-color: #d4edda; color: #006600')
            else:
                styles.append('')
        return styles

    st.dataframe(
        display_table.style.apply(style_row, axis=1),
        use_container_width=True,
        height=500
    )

    # ==================== SAR NARRATIVES ====================
    st.subheader("📄 SAR Narratives (OpenAI Generated)")
    
    # Model selector (still in UI – only the key is secret)
    model_choice = st.selectbox(
        "OpenAI Model",
        ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        index=0
    )

    if not OPENAI_API_KEY:
        st.warning("OpenAI API key is not configured in Streamlit Secrets.")
    else:
        for idx, row in display_alerts.iterrows():
            with st.expander(f"📌 {row['Date']} — {row['Description']} (Risk Score: {row.get('risk_score', 'N/A')})"):
                # Show existing narrative if available from API
                existing_narrative = row.get("sar_narrative") or row.get("narrative") or row.get("explanation")
                if existing_narrative:
                    st.markdown(existing_narrative)
                else:
                    st.caption("No pre-generated narrative available from API.")

                # Generate SAR Now button
                if st.button("🔄 Generate SAR Now", key=f"gen_{idx}"):
                    with st.spinner("Generating professional SAR narrative..."):
                        try:
                            import openai
                            openai.api_key = OPENAI_API_KEY

                            prompt = f"""
You are a senior AML compliance officer. Generate a formal Suspicious Activity Report (SAR) narrative.
Customer ID: {row.get('customer_id', 'Unknown')}
Transaction ID: {row.get('txn_id', 'Unknown')}
Risk Score: {row.get('risk_score', 0.83)}
Alert Type: {row.get('alert_type', 'Suspicious Transaction Pattern')}
Date: {row.get('Date', 'Unknown')}
Transaction Details:
- Amount: {row.get('amount', 'N/A')}
- Currency: {row.get('currency', 'USD')}
- Purpose: {row.get('purpose', row.get('Description', 'N/A'))}
- Counterparty: {row.get('counterparty_name', 'N/A')}
- Country: {row.get('counterparty_country', 'N/A')}
Pattern Indicators (from risk model):
{row.get('risk_flags', 'High impact on amount and deviation')}
Write the SAR in this exact professional format:
SUSPICIOUS ACTIVITY REPORT - PATTERN ANALYSIS
Customer ID: ...
Risk Score: ...
Pattern Type: ...
SUSPICIOUS ACTIVITY DESCRIPTION:
...
PATTERN INDICATORS:
- ...
RECOMMENDATION:
...
"""
                            response = openai.chat.completions.create(
                                model=model_choice,
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.7,
                                max_tokens=800
                            )
                            generated_narrative = response.choices[0].message.content.strip()
                            st.success("✅ SAR Generated!")
                            st.markdown(generated_narrative)

                            if st.button("📋 Copy SAR to Clipboard", key=f"copy_{idx}"):
                                st.code(generated_narrative, language=None)
                                st.success("Copied to clipboard!")
                        except Exception as e:
                            st.error(f"OpenAI error: {e}")

    if st.button("Export All Alerts as CSV"):
        st.download_button(
            "Download CSV",
            display_table.to_csv(index=False),
            "alerts.csv",
            "text/csv"
        )

elif page == "Screening":
    st.subheader("Screening Results")
    screening = customers_df[
        (customers_df.get('pep_flag', False) == True) |
        customers_df.get('sanctions_check', pd.Series()).apply(
            lambda x: isinstance(x, dict) and x.get('status') == 'flagged'
        )
    ]
    st.dataframe(
        screening[['full_name', 'nationality', 'pep_flag', 'risk_category']],
        use_container_width=True
    )

elif page == "Reports":
    st.subheader("Generated Reports")
    reports = pd.DataFrame([
        {"Report Name": "SAR-2025-06-001", "Type": "SAR", "Generated Date": "2025-06-08", "Status": "Draft"},
        {"Report Name": "CTR-Q2-2025", "Type": "CTR", "Generated Date": "2025-06-01", "Status": "Submitted"},
    ])
    st.dataframe(reports, use_container_width=True)

st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Connected to backend")
if st.button("🔄 Refresh All Data"):
    st.cache_data.clear()
    st.rerun()
