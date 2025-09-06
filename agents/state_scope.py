
"""State Definitions and Pydantic Schemas for Research Scoping.

This defines the state objects and structured schemas used for
the research agent scoping workflow, including researcher state management and output schemas.
"""

import operator
from typing import Any
from typing import Dict
from typing_extensions import Optional, Annotated, List, Sequence

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from agents.state import GatheredInformation, ResearchPlan, ResearchReport, EvaluationResult, Graph, ResearchAgentInput

# ===== STATE DEFINITIONS =====

class AgentInputState(MessagesState):
    """Input state for the full agent - only contains messages from user input."""
    messages: List[BaseMessage]  # Override to allow both HumanMessage and AIMessage



# ===== STRUCTURED OUTPUT SCHEMAS =====

class ClarifyWithUser(BaseModel):
    """Schema for user clarification decision and questions."""

    need_clarification: bool = Field(
        description="Whether the user needs to be asked a clarifying question.",
    )
    has_location: bool = Field(
        description="True if a clear geographical location (city, state, country) has been provided.",
    )
    needs_visualization: bool = Field(
        description="True if the user has requested a data visualization (e.g., 'show me a graph', 'visualize the data').",
    )
    graph_type: Optional[str] = Field(
        default=None,
        description="The type of graph requested by the user (e.g., bar, line, pie). None if not requested or unspecified.",
    )
    x_axis: Optional[str] = Field(
        default=None,
        description="The variable or category to plot on the X-axis if visualization is requested.",
    )
    y_axis: Optional[str] = Field(
        default=None,
        description="The variable or metric to plot on the Y-axis if visualization is requested.",
    )
    question: str = Field(
        description="A question to ask the user to clarify the report scope. Empty string if no clarification needed.",
    )
    verification: str = Field(
        description="Message confirming readiness to start research after sufficient details are available.",
    )

class ResearchQuestion(BaseModel):
    """Schema for structured research brief generation."""

    research_brief: str = Field(
        description="A detailed research brief that will be used to guide the research.",
    )
    graph_type: Optional[str] = Field(
        default=None,
        description="Type of graph specified in the research brief (bar, line, pie, etc.).",
    )
    x_axis: Optional[str] = Field(
        default=None,
        description="X-axis variable for visualization, if applicable.",
    )
    y_axis: Optional[str] = Field(
        default=None,
        description="Y-axis variable for visualization, if applicable.",
    )
    graph_data: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Structured JSON array of data points for plotting. Example: [{name: 'Entity A', metric: 10}, {name: 'Entity B', metric: 20}]",
    )

    
class FinalReport(BaseModel):
    """Schema for structured final report generation."""

    final_report: str = Field(
        description="A comprehensive final report based on the research conducted.",
    )
    graph: Optional[str] = Field(
        description="A graph or visualization if requested by the user.",
    )
    image: Optional[str] = Field(
        description="An image if relevant to the report.",
    )
    