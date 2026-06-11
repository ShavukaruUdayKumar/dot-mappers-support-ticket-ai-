"""Streamlit UI for Support Ticket AI System."""
import streamlit as st
import pandas as pd
import json
from datetime import datetime

# ── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title="Support Ticket AI",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Load services once ────────────────────────────────────
@st.cache_resource
def load_services():
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.data.loader import data_loader
    from app.services.query_service import QueryService
    from app.services.anomaly_service import AnomalyService

    data_loader.load_data("data/support_tickets.csv")
    return data_loader, QueryService(), AnomalyService()


try:
    data_loader, query_service, anomaly_service = load_services()
    df = data_loader.get_data()
    services_ok = True
except Exception as e:
    st.error(f"Failed to load services: {e}")
    services_ok = False
    st.stop()

# ── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/technical-support.png", width=64)
    st.title("Support Ticket AI")
    st.caption("Powered by Groq · llama-3.3-70b")

    st.divider()

    st.markdown("**Dataset Overview**")
    col1, col2 = st.columns(2)
    col1.metric("Total", len(df))
    col2.metric("Open", len(df[df['status'] == 'Open']))
    col1.metric("Resolved", len(df[df['status'] == 'Resolved']))
    col2.metric("Escalated", len(df[df['status'] == 'Escalated']))

    st.divider()

    st.markdown("**Sample Questions**")
    sample_questions = [
        "How many critical tickets are open?",
        "Which agent resolved the most tickets?",
        "What is the average rating for Technical tickets?",
        "How many billing tickets are escalated?",
        "Which agent has the lowest average rating?",
        "Show all Critical tickets",
    ]
    for q in sample_questions:
        if st.button(q, use_container_width=True, key=q):
            st.session_state["prefill_question"] = q

    st.divider()
    st.caption("Built for DOTMappers AI Engineer Assessment")

# ── Main tabs ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Ask a Question",
    "⚠️ Anomaly Detection",
    "📊 Dataset Stats",
    "🗂️ Raw Data"
])

# ══════════════════════════════════════════════════════════
# TAB 1 — Natural Language Query
# ══════════════════════════════════════════════════════════
with tab1:
    st.header("Ask a Question in Plain English")
    st.caption("The LLM converts your question → JSON intent → Pandas executes → LLM narrates the answer")

    # Prefill from sidebar button
    default_q = st.session_state.get("prefill_question", "")

    question = st.text_input(
        "Your question:",
        value=default_q,
        placeholder="e.g. How many critical tickets are open?",
        key="question_input"
    )

    ask_col, clear_col = st.columns([1, 5])
    ask = ask_col.button("Ask", type="primary", use_container_width=True)
    if clear_col.button("Clear", use_container_width=False):
        st.session_state["prefill_question"] = ""
        st.rerun()

    if ask and question.strip():
        with st.spinner("Thinking..."):
            try:
                result = query_service.execute_query(question)

                # Answer box
                st.success(f"**Answer:** {result.natural_answer}")

                # Two columns — data + metadata
                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("**Raw Result**")
                    if isinstance(result.data, list):
                        st.dataframe(pd.DataFrame(result.data), use_container_width=True)
                    else:
                        st.metric("Value", result.data)

                with c2:
                    st.markdown("**Query Metadata**")
                    meta = result.metadata
                    st.metric("Execution Time", f"{meta.execution_time_ms:.0f} ms")
                    st.metric("LLM Calls", meta.llm_calls)
                    st.metric("Rows Returned", meta.rows_returned)

                # Show the JSON intent
                with st.expander("🔎 View Query Intent (what LLM generated)"):
                    if meta.query_intent:
                        st.json(meta.query_intent.model_dump())

            except Exception as e:
                st.error(f"Error: {str(e)}")

    elif ask and not question.strip():
        st.warning("Please enter a question.")

# ══════════════════════════════════════════════════════════
# TAB 2 — Anomaly Detection
# ══════════════════════════════════════════════════════════
with tab2:
    st.header("Hybrid Anomaly Detection")
    st.caption("Rule-based (business logic) + Statistical (Z-score) combined")

    if st.button("Run Anomaly Detection", type="primary"):
        with st.spinner("Scanning for anomalies..."):
            try:
                report = anomaly_service.detect_all_anomalies()

                # Summary metrics
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Total Anomalies", report.total_anomalies)
                c2.metric("🔴 Critical", len(report.critical_anomalies))
                c3.metric("🟠 High", len(report.high_anomalies))
                c4.metric("🟡 Medium", len(report.medium_anomalies))
                c5.metric("🟢 Low", len(report.low_anomalies))

                st.divider()

                # Breakdown by type
                if report.anomalies_by_type:
                    st.markdown("**Anomalies by Type**")
                    type_df = pd.DataFrame(
                        list(report.anomalies_by_type.items()),
                        columns=["Type", "Count"]
                    ).sort_values("Count", ascending=False)
                    st.bar_chart(type_df.set_index("Type"))

                # Critical anomalies table
                def render_anomaly_table(anomalies, label, color):
                    if anomalies:
                        st.markdown(f"**{color} {label} Anomalies ({len(anomalies)})**")
                        rows = []
                        for a in anomalies:
                            rows.append({
                                "Ticket ID": a.ticket_id,
                                "Type": a.anomaly_type,
                                "Reason": a.reason,
                                "Agent": a.metadata.get("agent_id", "-"),
                                "Category": a.metadata.get("category", "-"),
                            })
                        st.dataframe(pd.DataFrame(rows), use_container_width=True)

                render_anomaly_table(report.critical_anomalies, "Critical", "🔴")
                render_anomaly_table(report.high_anomalies, "High", "🟠")
                render_anomaly_table(report.medium_anomalies, "Medium", "🟡")
                render_anomaly_table(report.low_anomalies, "Low", "🟢")

            except Exception as e:
                st.error(f"Anomaly detection failed: {str(e)}")
    else:
        st.info("Click **Run Anomaly Detection** to scan the dataset.")

# ══════════════════════════════════════════════════════════
# TAB 3 — Dataset Stats
# ══════════════════════════════════════════════════════════
with tab3:
    st.header("Dataset Statistics")

    # Top metrics
    resolved = df[df['status'] == 'Resolved']
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tickets", len(df))
    c2.metric("Avg Resolution (hrs)", f"{resolved['resolution_time_hrs'].mean():.1f}")
    c3.metric("Avg Response (hrs)", f"{df['response_time_hrs'].mean():.1f}")
    c4.metric("Avg Rating", f"{df['customer_rating'].mean():.2f} / 5")

    st.divider()

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**By Status**")
        status_df = df['status'].value_counts().reset_index()
        status_df.columns = ['Status', 'Count']
        st.bar_chart(status_df.set_index('Status'))

    with c2:
        st.markdown("**By Priority**")
        priority_df = df['priority'].value_counts().reset_index()
        priority_df.columns = ['Priority', 'Count']
        st.bar_chart(priority_df.set_index('Priority'))

    with c3:
        st.markdown("**By Category**")
        category_df = df['category'].value_counts().reset_index()
        category_df.columns = ['Category', 'Count']
        st.bar_chart(category_df.set_index('Category'))

    st.divider()

    # Top agents
    st.markdown("**Top 5 Agents by Resolved Tickets**")
    top_agents = (
        resolved.groupby('agent_id')
        .size()
        .reset_index(name='Resolved Count')
        .sort_values('Resolved Count', ascending=False)
        .head(5)
        .rename(columns={'agent_id': 'Agent'})
    )
    st.bar_chart(top_agents.set_index('Agent'))

# ══════════════════════════════════════════════════════════
# TAB 4 — Raw Data
# ══════════════════════════════════════════════════════════
with tab4:
    st.header("Raw Ticket Data")

    # Filters
    fc1, fc2, fc3 = st.columns(3)
    status_filter = fc1.multiselect(
        "Status", options=df['status'].unique().tolist(),
        default=df['status'].unique().tolist()
    )
    priority_filter = fc2.multiselect(
        "Priority", options=df['priority'].unique().tolist(),
        default=df['priority'].unique().tolist()
    )
    category_filter = fc3.multiselect(
        "Category", options=df['category'].unique().tolist(),
        default=df['category'].unique().tolist()
    )

    filtered = df[
        df['status'].isin(status_filter) &
        df['priority'].isin(priority_filter) &
        df['category'].isin(category_filter)
    ]

    st.caption(f"Showing {len(filtered)} of {len(df)} tickets")
    st.dataframe(filtered, use_container_width=True, height=500)
