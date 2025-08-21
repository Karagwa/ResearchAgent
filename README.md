# ResearchAgent Project Details

## Overview
ResearchAgent is an autonomous research assistant built with Streamlit, LangGraph, and Google Gemini. It automates the process of planning, gathering, evaluating, and reporting on research topics using web search and generative AI. The app is designed for in-depth, citation-rich research reports with export and tracing capabilities.

## Features
- **Automated Research Workflow:**
  - Plans research queries based on user input
  - Gathers information from the web using Tavily API
  - Evaluates sufficiency of gathered information
  - Generates a comprehensive, well-structured report with citations
- **Export Options:** Download reports as TXT, DOCX, or PDF
- **Markdown Report Preview:** View and copy formatted markdown reports
- **LangSmith Tracing:** Optional tracing for debugging and analysis
- **Research History:** View and revisit previous research sessions

## Technology Stack
- **Frontend:** Streamlit
- **AI/LLM:** Google Gemini (via LangChain)
- **Web Search:** Tavily API
- **Workflow Orchestration:** LangGraph
- **Tracing:** LangSmith
- **Export:** Python-docx, FPDF, and standard file I/O

## File Structure
- `app.py` — Main Streamlit app and UI logic
- `agents/`
  - `research_agent.py` — Research agent workflow and logic
  - `tools.py` — Web search tool integration
  - `state.py` — Agent state definitions
- `utils/`
  - `document_export.py` — Export functions for TXT, DOCX, PDF
  - `tracing.py` — LangSmith tracing configuration
- `.env` — API keys and environment variables
- `requirements.txt` — Python dependencies

## Setup & Usage
1. Clone the repository and install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Add your API keys to a `.env` file (see `.env.example` if available).
3. Run the app:
   ```sh
   streamlit run app.py
   ```
4. Enter a research topic, adjust settings, and start research.

## Environment Variables
- `GOOGLE_API_KEY` — Google Gemini API key
- `TAVILY_API_KEY` — Tavily web search API key
- `LANGSMITH_*` — (Optional) LangSmith tracing keys
- `OPENAI_API_KEY` — (Optional) For OpenAI integration

## References
- [LangGraph 101: Build a Deep Research Agent](https://towardsdatascience.com/langgraph-101-lets-build-a-deep-research-agent/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [LangChain Documentation](https://python.langchain.com/)
- [Tavily API](https://docs.tavily.com/)

---
Built by Karagwa. Powered by LangGraph, Google Gemini, Tavily, and Streamlit.
