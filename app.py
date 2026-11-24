import time
import traceback
from datetime import datetime

import streamlit as st

from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Multi-Agent Research System",
    page_icon="🔎",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "state" not in st.session_state:
    st.session_state.state = None      # latest pipeline result
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "history" not in st.session_state:
    st.session_state.history = []      # list of past runs


# ---------------------------------------------------------------------------
# Pipeline (same logic as pipeline.py, but reports progress to the UI)
# ---------------------------------------------------------------------------
def run_pipeline_ui(topic: str) -> dict:
    state = {}
    timings = {}

    with st.status("Running research pipeline...", expanded=True) as status:
        # Step 1: search agent
        st.write("🔎 **Step 1/4** - Search agent is looking for information...")
        t0 = time.time()
        search_agent = build_search_agent()
        search_result = search_agent.invoke({
            "messages": [("user", f"find recent, reliable and detailed information about {topic}")]
        })
        state["search_results"] = search_result["messages"][-1].content
        timings["Search"] = time.time() - t0
        st.write(f"✅ Search finished in {timings['Search']:.1f}s")

        # Step 2: reader agent
        st.write("📖 **Step 2/4** - Reader agent is scraping the top resource...")
        t0 = time.time()
        reader_agent = build_reader_agent()
        reader_result = reader_agent.invoke({
            "messages": [("user",
                f"Based on the following search results about '{topic}', "
                f"pick the most relevant URL and scrape it for deeper content.\n\n"
                f"Search Results:\n{state['search_results'][:800]}"
            )]
        })
        state["scraped_content"] = reader_result["messages"][-1].content
        timings["Reader"] = time.time() - t0
        st.write(f"✅ Scraping finished in {timings['Reader']:.1f}s")

        # Step 3: writer chain
        st.write("✍️ **Step 3/4** - Writer is drafting the report...")
        t0 = time.time()
        research_combined = (
            f"SEARCH RESULTS : \n {state['search_results']} \n\n"
            f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
        )
        state["report"] = writer_chain.invoke({
            "topic": topic,
            "research": research_combined,
        })
        timings["Writer"] = time.time() - t0
        st.write(f"✅ Report drafted in {timings['Writer']:.1f}s")

        # Step 4: critic chain
        st.write("🧐 **Step 4/4** - Critic is reviewing the report...")
        t0 = time.time()
        state["feedback"] = critic_chain.invoke({"report": state["report"]})
        timings["Critic"] = time.time() - t0
        st.write(f"✅ Review finished in {timings['Critic']:.1f}s")

        status.update(
            label=f"Research complete in {sum(timings.values()):.1f}s",
            state="complete",
            expanded=False,
        )

    state["timings"] = timings
    return state


def as_text(value) -> str:
    """Chain outputs may be str or message objects; normalise to str."""
    return value if isinstance(value, str) else getattr(value, "content", str(value))


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🔎 Research Agent")
    st.caption("Search → Read → Write → Critique")

    st.markdown("### How it works")
    st.markdown(
        "1. **Search agent** finds recent sources\n"
        "2. **Reader agent** scrapes the best one\n"
        "3. **Writer** drafts a report\n"
        "4. **Critic** reviews the draft"
    )

    st.divider()
    st.markdown("### Past runs")
    if st.session_state.history:
        for i, run in enumerate(reversed(st.session_state.history)):
            label = f"{run['topic'][:30]} ({run['time']})"
            if st.button(label, key=f"hist_{i}", use_container_width=True):
                st.session_state.state = run["state"]
                st.session_state.topic = run["topic"]
                st.rerun()
        if st.button("Clear history", use_container_width=True):
            st.session_state.history = []
            st.session_state.state = None
            st.rerun()
    else:
        st.caption("No runs yet.")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("Multi-Agent Research System")
st.write("Enter a topic and let the agents research it and produce a reviewed report.")

with st.form("research_form"):
    topic_input = st.text_input(
        "Research topic",
        value=st.session_state.topic,
        placeholder="e.g. Impact of quantum computing on cryptography",
    )
    submitted = st.form_submit_button("🚀 Start research", type="primary")

if submitted:
    topic = topic_input.strip()
    if not topic:
        st.warning("Please enter a topic first.")
    else:
        st.session_state.topic = topic
        try:
            result = run_pipeline_ui(topic)
            st.session_state.state = result
            st.session_state.history.append({
                "topic": topic,
                "time": datetime.now().strftime("%H:%M"),
                "state": result,
            })
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            with st.expander("Error details"):
                st.code(traceback.format_exc())

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
state = st.session_state.state
if state:
    st.divider()
    st.subheader(f"Results: {st.session_state.topic}")

    timings = state.get("timings", {})
    if timings:
        cols = st.columns(len(timings) + 1)
        for col, (name, secs) in zip(cols, timings.items()):
            col.metric(name, f"{secs:.1f}s")
        cols[-1].metric("Total", f"{sum(timings.values()):.1f}s")

    tab_report, tab_feedback, tab_search, tab_scraped = st.tabs(
        ["📄 Final report", "🧐 Critic feedback", "🔎 Search results", "📖 Scraped content"]
    )

    report_text = as_text(state["report"])
    feedback_text = as_text(state["feedback"])

    with tab_report:
        st.markdown(report_text)
        st.download_button(
            "⬇️ Download report (.md)",
            data=report_text,
            file_name="research_report.md",
            mime="text/markdown",
        )

    with tab_feedback:
        st.markdown(feedback_text)

    with tab_search:
        st.markdown(as_text(state["search_results"]))

    with tab_scraped:
        st.markdown(as_text(state["scraped_content"]))