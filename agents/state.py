from typing import TypedDict, List, Annotated
from langgraph.graph import add_messages

class AgentState(TypedDict):
    """State for the research agent"""
    messages: Annotated[List, add_messages]
    research_query: str
    research_plan: List[str]
    gathered_information: List[dict]
    research_report: str
    iterations: int
    max_iterations: int