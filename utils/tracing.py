import os
from langsmith import Client

def configure_tracing():
    """Configure LangSmith tracing for the application"""
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "Research Agent"
    
    
    client = Client()
    return client

def get_trace_url(run_id):
    """Generate a trace URL for a given run ID"""
    return f"https://smith.langchain.com/public/{os.environ.get('LANGCHAIN_PROJECT', 'default')}/r/{run_id}?poll=true"