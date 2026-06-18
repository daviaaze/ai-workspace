"""
AI Workspace Dashboard — Streamlit web interface.

Run:
  aiw dashboard
  or: streamlit run src/ai_workspace/dashboard/app.py

Access: http://localhost:8501
"""

import sys
from pathlib import Path

# Add ai-workspace to path if running directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ai_workspace.knowledge import KnowledgeStore

st.set_page_config(
    page_title="AI Workspace",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title(" AI Workspace")
st.sidebar.caption("Deep Search • Agent Swarm • Knowledge Base")

page = st.sidebar.radio(
    "Navigate",
    [" Overview", " Research", " Tasks", " Workflows", " Memory", " Analytics"],
)

refresh = st.sidebar.button(" Refresh", use_container_width=True)
st.sidebar.caption(f"Last refresh: {pd.Timestamp.now().strftime('%H:%M:%S')}")


@st.cache_data(ttl=30)
def load_metrics() -> dict:
    store = KnowledgeStore()
    store.initialize()
    c = store.conn.cursor()

    c.execute("SELECT COUNT(*) FROM research_entries")
    r_total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM research_entries WHERE created_at > NOW() - INTERVAL '24 hours'")
    r_24h = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks")
    t_total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
    t_done = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
    t_pending = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM agent_memory")
    m_total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM knowledge_entries")
    k_total = c.fetchone()[0]

    c.execute("SELECT ROUND(AVG(confidence)::numeric, 2) FROM research_entries WHERE confidence > 0")
    avg_conf = c.fetchone()[0] or 0

    c.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM research_entries
        WHERE created_at > NOW() - INTERVAL '30 days'
        GROUP BY date ORDER BY date
    """)
    daily_research = c.fetchall()

    c.execute("""
        SELECT status, COUNT(*) as count
        FROM tasks GROUP BY status
    """)
    task_status = c.fetchall()

    c.close()
    store.close()
    
    # Cache & cost stats
    try:
        from ai_workspace.core.cost import CostService
        cost = CostService()
        cache_stats = cost.cache.stats()
        today = cost.budget.today_spent()
        month = cost.budget.month_spent()
    except Exception:
        cache_stats = {"total_entries": 0, "total_hits": 0, "tokens_saved": 0, "cost_saved": 0.0}
        today = 0.0
        month = 0.0

    return {
        "research_total": r_total,
        "research_24h": r_24h,
        "tasks_total": t_total,
        "tasks_done": t_done,
        "tasks_pending": t_pending,
        "memories": m_total,
        "knowledge": k_total,
        "avg_confidence": avg_conf,
        "daily_research": daily_research,
        "task_status": task_status,
        # Cache
        "cache_entries": cache_stats["total_entries"],
        "cache_hits": cache_stats["total_hits"],
        "tokens_saved": cache_stats["tokens_saved"],
        "cost_saved": cache_stats["cost_saved"],
        "today_cost": today,
        "month_cost": month,
    }


@st.cache_data(ttl=30)
def load_research_history(limit: int = 50) -> list[dict]:
    store = KnowledgeStore()
    store.initialize()
    results = store.get_research_history(limit=limit)
    store.close()
    return results


@st.cache_data(ttl=30)
def load_tasks(limit: int = 50) -> list[dict]:
    store = KnowledgeStore()
    store.initialize()
    tasks = store.get_tasks(limit=limit)
    store.close()
    return tasks


@st.cache_data(ttl=30)
def load_workflow_runs(limit: int = 30) -> list[dict]:
    from ai_workspace.workflow import WorkflowRegistry
    runs = []
    for name in WorkflowRegistry.list():
        wf_cls = WorkflowRegistry.get(name)
        if wf_cls:
            runs.extend(wf_cls.get_runs(limit=10))
    runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return runs[:limit]



metrics = load_metrics()

if page == " Overview":
    st.title(" Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Research (24h)", metrics["research_24h"], delta=None)
    with col2:
        st.metric("Tasks Pending", metrics["tasks_pending"], delta=None)
    with col3:
        st.metric("Avg Confidence", f"{metrics['avg_confidence']:.0%}")
    with col4:
        st.metric("Agent Memories", metrics["memories"])
    
    # Cache row
    st.subheader(" Cache & Costs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(" Cache Entries", metrics["cache_entries"])
    with col2:
        st.metric(" Cache Hits", metrics["cache_hits"])
    with col3:
        st.metric(" Tokens Saved", f"{metrics['tokens_saved']:,}")
    with col4:
        st.metric(" Today's Cost", f"${metrics['today_cost']:.4f}")

    # Budget gauges
    col1, col2 = st.columns(2)
    with col1:
        daily_pct = min(100, (metrics["today_cost"] / 1.0) * 100)
        st.metric(" Daily Budget", f"{daily_pct:.1f}%", delta=f"${1.0 - metrics['today_cost']:.4f} remaining")
        st.progress(daily_pct / 100)
    with col2:
        month_pct = min(100, (metrics["month_cost"] / 10.0) * 100)
        st.metric(" Monthly Budget", f"{month_pct:.1f}%", delta=f"${10.0 - metrics['month_cost']:.4f} remaining")
        st.progress(month_pct / 100)

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Research Activity (30 days)")
        if metrics["daily_research"]:
            df = pd.DataFrame(metrics["daily_research"], columns=["date", "count"])
            fig = px.bar(df, x="date", y="count", title="Daily Research")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Task Distribution")
        if metrics["task_status"]:
            df = pd.DataFrame(metrics["task_status"], columns=["status", "count"])
            fig = px.pie(df, names="status", values="count", title="Tasks by Status")
            st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Recent Research")
    for r in load_research_history(limit=5):
        with st.expander(f"{r.get('query', '?')[:100]} ({r.get('confidence', 0):.0%})"):
            st.write(r.get("summary", "No summary"))
            st.caption(f"Created: {r.get('created_at', '')}")

elif page == " Research":
    st.title(" Research")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Research query", placeholder="Enter a topic to research...")
    with col2:
        depth = st.selectbox("Depth", [1, 2, 3], index=1)
    
    if st.button(" Deep Research", type="primary", disabled=not query):
        with st.spinner(f"Researching: {query}..."):
            from ai_workspace.search import DeepSearchEngine
            import asyncio
            
            engine = DeepSearchEngine(max_depth=depth)
            result = asyncio.run(engine.research(query))
            
            st.success(f"Complete! Confidence: {result.confidence:.0%}")
            
            if result.summary:
                st.markdown("### Summary")
                st.markdown(result.summary)
            
            if result.detailed_report:
                st.markdown("### Full Report")
                st.markdown(result.detailed_report)
            
            st.subheader("Sub-questions")
            for sq in result.sub_questions:
                with st.expander(f"Q: {sq.question[:100]} ({sq.confidence:.0%})"):
                    st.write(sq.answer)
    
    st.subheader("Research History")
    df = pd.DataFrame(load_research_history(limit=30))
    if not df.empty:
        st.dataframe(
            df[["id", "query", "confidence", "created_at"]],
            use_container_width=True,
            hide_index=True,
        )

elif page == " Tasks":
    st.title(" Tasks")
    
    with st.form("new_task"):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            new_title = st.text_input("Task title")
        with col2:
            new_priority = st.slider("Priority", 0, 10, 5)
        with col3:
            new_schedule = st.text_input("Schedule (cron)", placeholder="0 9 * * *")
        
        if st.form_submit_button("Add Task"):
            store = KnowledgeStore()
            store.initialize()
            store.add_task(new_title, priority=new_priority, schedule=new_schedule or None)
            store.close()
            st.success(f"Task added: {new_title}")
            st.cache_data.clear()
    
    tasks = load_tasks()
    if tasks:
        df = pd.DataFrame(tasks)
        status_colors = {
            "pending": "background-color: #fff3cd",
            "in_progress": "background-color: #cce5ff",
            "completed": "background-color: #d4edda",
            "failed": "background-color: #f8d7da",
        }
        
        def color_status(val):
            return status_colors.get(val, "")
        
        styled = df[["id", "status", "title", "priority", "schedule"]].style
        styled = styled.map(color_status, subset=["status"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

elif page == " Workflows":
    st.title(" Workflows")
    
    runs = load_workflow_runs()
    if runs:
        df = pd.DataFrame(runs)
        st.dataframe(
            df[["run_id", "workflow_name", "status", "duration_ms", "created_at"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No workflow runs yet. Try: aiw wf run deep_research --query 'test'")

elif page == " Memory":
    st.title(" Agent Memory")
    
    store = KnowledgeStore()
    store.initialize()
    
    agent_filter = st.selectbox("Agent", ["continuous-learner", "default"])
    memories = store.recall(agent_filter, "%", limit=50)
    store.close()
    
    for m in memories:
        with st.expander(f"{m.get('memory_type', '?')} — importance: {m.get('importance', 0):.0%}"):
            st.markdown(m.get("content", ""))
            st.caption(f"ID: {m['id']} | {m.get('created_at', '')}")

elif page == " Analytics":
    st.title(" Analytics")
    
    st.subheader("Knowledge Growth")
    
    store = KnowledgeStore()
    store.initialize()
    c = store.conn.cursor()
    
    c.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM knowledge_entries
        WHERE created_at > NOW() - INTERVAL '90 days'
        GROUP BY date ORDER BY date
    """)
    kb_growth = c.fetchall()
    
    c.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM agent_memory
        WHERE created_at > NOW() - INTERVAL '90 days'
        GROUP BY date ORDER BY date
    """)
    mem_growth = c.fetchall()
    
    c.close()
    store.close()
    
    if kb_growth:
        df_kb = pd.DataFrame(kb_growth, columns=["date", "count"])
        fig = px.area(df_kb, x="date", y="count", title="Knowledge Entries Over Time")
        st.plotly_chart(fig, use_container_width=True)
    
    if mem_growth:
        df_mem = pd.DataFrame(mem_growth, columns=["date", "count"])
        fig = px.line(df_mem, x="date", y="count", title="Agent Memory Growth")
        st.plotly_chart(fig, use_container_width=True)
    
    st.metric("Total Knowledge Entries", metrics["knowledge"])
    st.metric("Total Agent Memories", metrics["memories"])
    st.metric("Avg Research Confidence", f"{metrics['avg_confidence']:.0%}")



def run_dashboard():
    """Launch Streamlit dashboard."""
    import subprocess
    import os
    
    app_path = Path(__file__).resolve()
    os.execvp("streamlit", [
        "streamlit", "run", str(app_path),
        "--server.headless", "true",
        "--server.port", "8501",
    ])
