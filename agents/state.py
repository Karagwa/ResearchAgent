import operator
from pydantic import BaseModel, Field
from typing import Annotated, List, Optional, Dict, Sequence, TypedDict, Union
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langgraph.graph.message import add_messages

class ResearchAgentInput(BaseModel):
    research_brief: str  # The structured research brief from scoping agent


    


class ResearchStep(BaseModel):
    step_number: int = Field(..., description="The order of the step in the plan")
    action: str = Field(..., description="The high-level action (e.g., search, summarize, analyze)")
    description: str = Field(..., description="Detailed explanation of what will be done in this step")

class ResearchPlan(BaseModel):
    topic: str = Field(..., description="The research topic")
    steps: List[ResearchStep] = Field(..., description="The structured step-by-step plan")
    
class InformationItem(BaseModel):
    query: str = Field(..., description="The query or sub-question used")
    source: str = Field(..., description="The source name or URL")
    snippet: str = Field(..., description="Relevant snippet or extracted text")
    metadata: Optional[Dict] = Field(default=None, description="Any additional metadata from the source")

class GatheredInformation(BaseModel):
    topic: str = Field(..., description="The research topic")
    items: List[InformationItem] = Field(..., description="List of gathered information items")

class GraphDataPoint(BaseModel):
    x: str = Field(..., description="X-axis value")
    y: float = Field(..., description="Y-axis value")

class Graph(BaseModel):
    title: str = Field(..., description="Graph title")
    chart_type: str = Field(..., description="Type of chart (bar, line, pie, etc.)")
    x_label: str = Field(..., description="Label for the X-axis")
    y_label: str = Field(..., description="Label for the Y-axis")
    data: List[GraphDataPoint] = Field(..., description="Data points for the chart")
    file_path: Optional[str] = Field(default=None, description="Saved file path for the graph image")

class Evaluation(BaseModel):
    criterion: str = Field(..., description="What aspect is being evaluated (e.g., relevance, reliability)")
    score: float = Field(..., description="Score between 0 and 1 or 0 and 10")
    comments: str = Field(..., description="Notes about the evaluation")

class EvaluationResult(BaseModel):
    topic: str = Field(..., description="The research topic")
    evaluations: List[Evaluation] = Field(..., description="List of evaluations for the gathered information")

class ResearchReportSection(BaseModel):
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content in detail")

class ResearchReport(BaseModel):
    topic: str = Field(..., description="The research topic")
    summary: str = Field(..., description="High-level summary of the research")
    key_findings: List[str] = Field(..., description="Bullet-point list of key findings")
    sections: List[ResearchReportSection] = Field(..., description="Detailed sections of the report")
    conclusion: Optional[str] = Field(default=None, description="Closing thoughts or recommendations")
    references: Optional[List[str]] = Field(default=None, description="List of references or sources cited")


# --- Move ResearchAgentState outside of ResearchReport ---
class ResearchAgentState(BaseModel):
    research_brief: str
    research_plan: Optional[ResearchPlan] = None
    gathered_information: Optional[GatheredInformation] = None
    graphs: List[Graph] = []
    graph_paths: List[str] = []
    evaluation: Optional[EvaluationResult] = None
    research_report: Optional[ResearchReport] = None
    iterations: int = 0
    max_iterations: int = 2
    current_step: Optional[str] = None
    messages: List[Union[AIMessage, HumanMessage]] = []


class ResearcherState(TypedDict):
    """
    State for the research agent containing message history and research metadata.

    This state tracks the researcher's conversation, iteration count for limiting
    tool calls, the research topic being investigated, compressed findings,
    and raw research notes for detailed analysis.
    """
    researcher_messages: Annotated[Sequence[BaseMessage], add_messages]
    tool_call_iterations: int
    research_topic: str
    compressed_research: str
    raw_notes: Annotated[List[str], operator.add]