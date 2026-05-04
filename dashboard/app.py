import json
import os
from datetime import datetime, timezone

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="OmniResolve — Case Dashboard",
    page_icon="⚖️",
    layout="wide",
)

st.sidebar.title("OmniResolve")
st.sidebar.caption("Dispute Intelligence System")
page = st.sidebar.radio("View", ["Active Cases", "Submit Case", "Analytics", "Systemic Alerts"])

def _api(method: str, path: str, **kwargs):
    try:
        resp = httpx.request(method, f"{API_BASE}{path}", timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None

if page == "Active Cases":
    st.title("Active Dispute Cases")

    log_path = "logs/audit.jsonl"
    records = []
    if os.path.exists(log_path):
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass

    resolution_events = [r for r in records if r.get("event") == "resolution"]
    escalation_events = [r for r in records if r.get("event") == "escalation"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Resolved", len(resolution_events))
    col2.metric("Escalated", len(escalation_events))
    col3.metric("Avg Confidence", f"{sum(r.get('confidence', 0) for r in resolution_events) / max(len(resolution_events), 1):.2f}")
    col4.metric("Auto-resolved", len([r for r in resolution_events if r.get("confidence", 0) >= 0.65]))

    if resolution_events:
        df = pd.DataFrame(resolution_events)
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.sort_values("ts", ascending=False)

        st.subheader("Recent Resolutions")
        display_cols = ["ts", "case_id", "customer_id", "dispute_category", "recommendation", "confidence"]
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols].head(50), use_container_width=True)

        st.subheader("Case Detail")
        selected = st.selectbox("Select case", df["case_id"].unique())
        if selected:
            row = df[df["case_id"] == selected].iloc[0]
            st.json(row.to_dict())

    if escalation_events:
        st.subheader("Escalation Queue — Pending Human Review")
        esc_df = pd.DataFrame(escalation_events)
        st.dataframe(esc_df, use_container_width=True)

        with st.expander("Submit Human Decision"):
            case_id_input = st.text_input("Case ID")
            resolution_choice = st.selectbox("Decision", ["refund", "replace", "reject", "escalate"])
            notes_input = st.text_area("Notes")
            if st.button("Submit Decision"):
                result = _api("POST", f"/cases/{case_id_input}/human-decision", json={
                    "resolution": resolution_choice,
                    "notes": notes_input,
                })
                if result:
                    st.success(f"Decision submitted: {result}")

    else:
        st.info("No resolution events found. Run the pipeline and cases will appear here.")

elif page == "Submit Case":
    st.title("Submit New Dispute Case")

    with st.form("new_case"):
        customer_id = st.text_input("Customer ID (or email)")
        order_id = st.text_input("Order ID")
        channel = st.selectbox("Channel", ["web", "chat", "email", "phone"])
        message = st.text_area("Dispute Description", height=150)
        evidence_files = st.file_uploader(
            "Upload Evidence (photos, receipts)", accept_multiple_files=True
        )
        submitted = st.form_submit_button("Submit Case")

    if submitted:
        if not message:
            st.warning("Please provide a dispute description.")
        else:
            with st.spinner("Running dispute pipeline..."):
                result = _api("POST", "/cases/", json={
                    "customer_id": customer_id,
                    "order_id": order_id,
                    "channel": channel,
                    "message": message,
                })

            if result:
                case_id = result.get("case_id", "")
                st.success(f"Case created: **{case_id}**")

                for f in (evidence_files or []):
                    files = {"file": (f.name, f.read(), f.type)}
                    ev_result = _api("POST", f"/cases/{case_id}/evidence",
                                     **{"files": files})

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Recommendation", result.get("resolution", "—"))
                    st.metric("Confidence", f"{result.get('confidence', 0):.2f}")
                    st.metric("Requires Human Review", str(result.get("requires_human", False)))
                with col2:
                    citations = result.get("legal_citations", [])
                    st.subheader("Legal Citations")
                    for c in citations:
                        st.write(f"- {c}")

                brief = result.get("brief", "")
                if brief:
                    st.subheader("Resolution Brief")
                    st.text_area("Brief", brief, height=300, disabled=True)

elif page == "Analytics":
    st.title("Dispute Analytics")

    log_path = "logs/audit.jsonl"
    records = []
    if os.path.exists(log_path):
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass

    resolution_events = [r for r in records if r.get("event") == "resolution"]

    if not resolution_events:
        st.info("No data yet.")
    else:
        df = pd.DataFrame(resolution_events)
        df["ts"] = pd.to_datetime(df.get("ts", pd.Timestamp.now()))

        col1, col2 = st.columns(2)
        with col1:
            if "dispute_category" in df.columns:
                fig = px.pie(df, names="dispute_category", title="Disputes by Category")
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            if "recommendation" in df.columns:
                fig = px.bar(df["recommendation"].value_counts().reset_index(),
                             x="recommendation", y="count", title="Resolutions by Type")
                st.plotly_chart(fig, use_container_width=True)

        if "confidence" in df.columns:
            fig = px.histogram(df, x="confidence", nbins=20, title="Confidence Score Distribution")
            st.plotly_chart(fig, use_container_width=True)

        if "ts" in df.columns and "dispute_category" in df.columns:
            df_daily = df.set_index("ts").resample("D")["case_id"].count().reset_index()
            df_daily.columns = ["date", "cases"]
            fig = px.line(df_daily, x="date", y="cases", title="Daily Case Volume")
            st.plotly_chart(fig, use_container_width=True)

elif page == "Systemic Alerts":
    st.title("Systemic Risk Alerts")
    st.caption("Cross-case patterns surfaced by Neo4j — products with high dispute rates, sellers with fraud signals")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("High-Defect Products")
        from graphrag.neo4j_client import run_query
        import asyncio

        async def get_defect_products():
            return await run_query("""
                MATCH (p:Product)<-[:CONTAINS]-(:Order)<-[:CONCERNS]-(d:Dispute)
                WITH p, count(d) AS dispute_count
                WHERE dispute_count >= 3
                RETURN p.sku AS sku, p.name AS name, p.category AS category,
                       p.defect_rate AS defect_rate, dispute_count
                ORDER BY dispute_count DESC LIMIT 20
            """)

        try:
            products = asyncio.run(get_defect_products())
            if products:
                st.dataframe(pd.DataFrame(products), use_container_width=True)
            else:
                st.info("No high-defect products found.")
        except Exception as e:
            st.warning(f"Connect Neo4j to see live data: {e}")

    with col2:
        st.subheader("Seller Fraud Heatmap")

        async def get_sellers():
            return await run_query("""
                MATCH (s:Seller)
                WHERE s.fraud_signals > 0 OR s.dispute_rate > 0.05
                RETURN s.id AS seller_id, s.name AS name,
                       s.dispute_rate AS dispute_rate,
                       s.refund_rate AS refund_rate,
                       s.fraud_signals AS fraud_signals
                ORDER BY s.fraud_signals DESC, s.dispute_rate DESC LIMIT 20
            """)

        try:
            sellers = asyncio.run(get_sellers())
            if sellers:
                df_s = pd.DataFrame(sellers)
                fig = px.scatter(
                    df_s, x="dispute_rate", y="refund_rate",
                    size="fraud_signals", color="fraud_signals",
                    hover_data=["seller_id", "name"],
                    title="Seller Risk: Dispute Rate vs Refund Rate",
                    color_continuous_scale="Reds",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No at-risk sellers found.")
        except Exception as e:
            st.warning(f"Connect Neo4j to see live data: {e}")
