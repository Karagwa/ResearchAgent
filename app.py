import json
import uuid
import streamlit as st
from datetime import datetime
import os
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

# === Import your modules ===
from agents.research_agent import agent as research_agent
from utils.document_export import export_to_txt, export_to_docx, export_to_pdf
from utils.tracing import configure_tracing
from agents.state import ResearchAgentState
from agents.scoping_agent import agent as agent  # Your compiled StateGraph

load_dotenv()
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}
def format_research_report(report_data):
    """Convert the research report JSON to formatted Markdown"""
    if isinstance(report_data, str):
        try:
            report_data = json.loads(report_data)
        except:
            return report_data  # Return as-is if it's not valid JSON
    
    markdown = f"# {report_data.get('topic', 'Research Report')}\n\n"
    
    # Summary
    markdown += f"## Summary\n{report_data.get('summary', '')}\n\n"
    
    # Key Findings
    if 'key_findings' in report_data and report_data['key_findings']:
        markdown += "## Key Findings\n"
        for finding in report_data['key_findings']:
            markdown += f"- {finding}\n"
        markdown += "\n"
    
    # Sections
    if 'sections' in report_data and report_data['sections']:
        for section in report_data['sections']:
            markdown += f"## {section.get('title', 'Section')}\n"
            markdown += f"{section.get('content', '')}\n\n"
    
    # Conclusion
    if 'conclusion' in report_data and report_data['conclusion']:
        markdown += f"## Conclusion\n{report_data['conclusion']}\n\n"
    
    # References
    if 'references' in report_data and report_data['references']:
        markdown += "## References\n"
        for i, ref in enumerate(report_data['references'], 1):
            markdown += f"{i}. {ref}\n"
    
    return markdown
# === Page Config ===
st.set_page_config(
    page_title="DigDeep",
    page_icon="🔍",
    layout="wide"
)

# === Tracing Config ===
try:
    langsmith_client = configure_tracing()
    tracing_enabled = True
except Exception as e:
    tracing_enabled = False
    st.warning(f"LangSmith tracing not configured: {e}")

# === Session State Defaults ===
defaults = {
    "research_history": [],
    "current_research": None,
    "is_running": False,
    "user_input": "",
    "agent_state": None,
    "research_brief": "",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# === Title ===
st.title("🔍 DigDeep")
st.write("Research deeper, discover faster!")
st.markdown("""
Powered by advanced agentic AI technology, this app helps you uncover insights efficiently.
Enter your question and let the AI dig deeper!
""")

# === Sidebar ===
with st.sidebar:
    st.header("How to use")
    st.markdown("""
    1. Enter your research topic or question.  
    2. Click **Generate Brief** to see the agent's understanding.  
    3. Click **Start Research** to run the full workflow.  
    4. Download your report and view graphs.  
    """)
    st.markdown("---")
    st.header("Settings")
    max_iterations = st.slider(
        "Max Research Iterations", 1, 5, 2,
        help="How many search cycles to perform before generating report?",
        key="sidebar_max_iterations"
    )
    
    st.markdown("---")
    st.header("Research History")
    for i, research in enumerate(st.session_state.research_history):
        if st.button(f"{research['timestamp']}: {research['query'][:30]}...", key=f"history_{i}"):
            st.session_state.current_research = research
            st.session_state.user_input = research['query']
            st.rerun()

# === Tabs ===
tab1, tab2 = st.tabs(["New Research", "History & Results"])

# === TAB 1: New Research ===
with tab1:
    research_input = st.text_area(
        "Enter your research topic or question:",
        height=150,
        value=st.session_state.user_input,
        key="research_input"
    )
    initial_message = research_input.strip()
    st.session_state.user_input = initial_message
    state={
        "user_input": initial_message,
        "research_brief": "",  # Set to empty string for Pydantic validation
        "research_plan": None,
        "gathered_information": None,
        "graphs": [],
        "graph_paths": [],
        "evaluation": None,
        "research_report": None,
        "iterations": 0,
        "max_iterations": 2,
        "current_step": None,
        "messages": [AIMessage(content=initial_message)]
    }

    
    if st.button("Generate Brief and Research", disabled=not initial_message):
            try:
                
                state = agent.invoke(state, config=config)
                if state.get("messages") and "?" in getattr(state["messages"][-1], "content", ""):
                    st.warning("The agent needs clarification to generate the brief:")
                    clarification = st.text_input("Your reply:", key="clarify_brief")
                    if st.button("Send Clarification", key="send_brief"):
                        state["messages"].append(HumanMessage(content=clarification))
                        state = agent.invoke(state, config=config)
                if state.get("research_brief"):
                    st.session_state.research_brief = state["research_brief"]
                    st.success("Research brief generated!")
                    st.write(f"**Brief:** {st.session_state.research_brief}")
                if state.get("research_plan"):
                    st.write("**Research Plan:**")
                    st.write(state["research_plan"])
                if state.get("gathered_information"):
                    st.write("**Gathered Information:**")
                    st.write(state["gathered_information"])
                if state.get("research_report"):
                    st.write("**Research Report:**")
                    st.write(state["research_report"])
                    # Save to history
                    gathered_info = []
                    gathered_information = state.get("gathered_information")
                    if gathered_information is not None:
                        if hasattr(gathered_information, "items"):
                            gathered_info = gathered_information.items
                        elif isinstance(gathered_information, dict):
                            gathered_info = gathered_information.get("items", [])
                        elif isinstance(gathered_information, list):
                            gathered_info = gathered_information
                    research_record = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "query": initial_message,
                        "brief": state.get("research_brief", ""),
                        "report": state.get("research_report", ""),
                        "graph_paths": state.get("graph_paths", []),
                        "gathered_info": gathered_info,
                        "iterations": state.get("iterations", 0)
                    }
                    st.session_state.research_history.insert(0, research_record)
                    st.session_state.current_research = research_record
                    st.session_state.agent_state = state
                    st.success("Research completed and saved to history!")
            except Exception as e:
                st.error(f"Error {str(e)}")


    

# === TAB 2: History & Results ===
with tab2:
    if not st.session_state.research_history:
        st.info("No research history yet. Run a research query to see results here.")
    elif st.session_state.current_research:
        research = st.session_state.current_research
        st.header(f"Research: {research['query']}")
        st.caption(f"Completed on {research['timestamp']} ({research['iterations']} iterations)")
        
        if tracing_enabled:
            st.info("Tracing is enabled. View detailed traces in LangSmith.")
        
        st.subheader("Research Brief")
        st.write(research["brief"])
        
        st.subheader("Research Report")
        tab_report, tab_copy = st.tabs(["View Report", "Copy Report"])
        with tab_report:
            st.write(format_research_report(research["report"]))
        with tab_copy:
            st.code(format_research_report(research["report"]), language="markdown")
        
        st.subheader("Graph Visualization")
        if research.get("graph_paths"):
            for graph_path in research["graph_paths"]:
                if os.path.exists(graph_path):
                    st.image(graph_path, caption="Generated Graph", use_column_width=True)
                else:
                    st.info(f"Graph file not found: {graph_path}")
        else:
            st.info("No graph generated for this research.")
        formatted_research_report = format_research_report(research["report"])
        st.subheader("Export Report")
        col1, col2, col3 = st.columns(3)
        with col1:
            txt_data, txt_name = export_to_txt(formatted_research_report)
            st.download_button("Download as TXT", txt_data, txt_name, mime="text/plain")
        with col2:
            doc_data, doc_name = export_to_docx(formatted_research_report)
            st.download_button("Download as DOCX", doc_data, doc_name,
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        with col3:
            pdf_data, pdf_name = export_to_pdf(formatted_research_report)
            st.download_button("Download as PDF", pdf_data, pdf_name, mime="application/pdf")
        
        with st.expander("View Research Details"):
            st.write(f"**Query:** {research['query']}")
            st.write(f"**Iterations:** {research['iterations']}")
            st.subheader("Gathered Information")
            for i, info in enumerate(research.get("gathered_info", [])):
                if isinstance(info, dict):
                    st.write(f"**Query {i+1}:** {info.get('query', '')}")
                    with st.expander(f"View results for Query {i+1}"):
                        st.text(info.get('snippet', ''))
                else:
                    st.write(f"**Query {i+1}:** {info}")
                    
                st.divider()
    else:
        # If there's history but no current research selected
        st.info("Select a research from the sidebar to view details")

# === Footer ===
st.markdown("---")
st.caption("Built with ❤️ by Karagwa Ann Treasure")