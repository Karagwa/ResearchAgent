import streamlit as st
import time
from datetime import datetime
from agents.research_agent import research_agent
from utils.document_export import export_to_txt, export_to_docx, export_to_pdf
from utils.tracing import configure_tracing
import os
from dotenv import load_dotenv
import asyncio


load_dotenv()


st.set_page_config(
    page_title="DigDeep",
    page_icon="🔍",
    layout="wide"
    
)


try:
    langsmith_client = configure_tracing()
    tracing_enabled = True
except Exception as e:
    tracing_enabled = False
    st.warning(f"LangSmith tracing not configured: {e}")


if "research_history" not in st.session_state:
    st.session_state.research_history = []
if "current_research" not in st.session_state:
    st.session_state.current_research = None
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "progress" not in st.session_state:
    st.session_state.progress = 0
if "current_step" not in st.session_state:
    st.session_state.current_step = ""


st.title("🔍 DigDeep")
st.write("Research deeper, discover faster!")
st.markdown("""
Powered by advanced agentic AI technology, this app helps you uncover insights and gather information efficiently. All you have to do is...ask away!
""")


with st.sidebar:
    st.header("How to use")
    st.markdown("""
    1. Enter your research topic or question in the text area.
    2. Adjust the settings as needed, including the maximum number of research iterations.
    3. Click the "Start Research" button to begin the research process.
    4. View the progress and results in the main content area.
    """)
    st.markdown("---")
    st.header("Settings")
    max_iterations = st.slider("Max Research Iterations", 1, 5, 3,
                              help="How many search cycles to perform before generating report?")
    
    st.header("Research History")
    st.markdown("Click on a research entry to view details.")
    for i, research in enumerate(st.session_state.research_history):
        if st.button(f"{research['timestamp']}: {research['query'][:30]}...", key=f"history_{i}"):
            st.session_state.current_research = research


tab1, tab2 = st.tabs(["New Research", "History & Results"])

with tab1:
    research_query = st.text_area(
        "Enter your research topic or question:",
        height=100,
        placeholder="e.g., 'What are the latest advancements in quantum computing and their potential applications?'"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Start Research", type="primary", disabled=not st.session_state.is_running):
            if not research_query:
                st.error("Please enter a research question.")
            else:
                st.session_state.is_running = True
                st.session_state.progress = 0
                st.session_state.current_step = "Initializing research..."
                
               
                research_state = {
                    "research_query": research_query,
                    "max_iterations": max_iterations
                }
                
              
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                   
                    result = research_agent.invoke(research_state)
                    
                    
                    research_result = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "query": research_query,
                        "report": result["research_report"],
                        "time_taken": "N/A",  # We're not measuring time in this simplified version
                        "gathered_info": result.get("gathered_information", []),
                        "iterations": result.get("iterations", 0)
                    }
                    
                    st.session_state.research_history.append(research_result)
                    st.session_state.current_research = research_result
                    st.session_state.is_running = False
                    
                    st.success("Research completed successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Research failed: {str(e)}")
                    st.session_state.is_running = False
    
    with col2:
        if st.button("Clear History", disabled=len(st.session_state.research_history) == 0):
            st.session_state.research_history = []
            st.session_state.current_research = None
            st.rerun()


if st.session_state.current_research:
    research = st.session_state.current_research
    
    with tab2:
        st.header(f"Research: {research['query']}")
        st.caption(f"Completed on {research['timestamp']} ({research['iterations']} iterations)")
        
        if tracing_enabled:
            st.info("Tracing is enabled. View detailed traces in LangSmith.")
        
        
        st.subheader("Research Report")
        tab1, tab2 = st.tabs(["View Report", "Copy Report"])
        with tab1:

            st.write(research["report"])
        with tab2:
            st.code(research["report"], language=None)  
        
        st.subheader("Export Report")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            txt_data, txt_name = export_to_txt(research["report"])
            st.download_button(
                "Download as TXT",
                data=txt_data,
                file_name=txt_name,
                mime="text/plain"
            )
        
        with col2:
            doc_data, doc_name = export_to_docx(research["report"])
            st.download_button(
                "Download as DOCX",
                data=doc_data,
                file_name=doc_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        with col3:
            pdf_data, pdf_name = export_to_pdf(research["report"])
            st.download_button(
                "Download as PDF",
                data=pdf_data,
                file_name=pdf_name,
                mime="application/pdf"
            )
        
        
        with st.expander("View Research Details"):
            st.write(f"**Query:** {research['query']}")
            st.write(f"**Iterations:** {research['iterations']}")
            
            st.subheader("Gathered Information")
            for i, info in enumerate(research["gathered_info"]):
                st.write(f"**Query {i+1}:** {info['query']}")
                with st.expander(f"View results for Query {i+1}"):
                    st.text(info['results'])
                st.divider()


if not st.session_state.research_history:
    with tab2:
        st.info("No research history yet. Complete a research query to see results here.")


st.markdown("---")
st.caption("Built with :love by Karagwa Ann Treasure")


if st.session_state.is_running:
    st.toast("Research in progress... This may take a few minutes.", icon="🔍")