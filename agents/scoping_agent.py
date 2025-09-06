def propagate_state(state, update_dict):
    """Merge current state with update dict, ensuring all required fields are present."""
    # Always start with all required fields from state, then overwrite with update_dict
    required_fields = [
        "research_brief", "research_plan", "gathered_information", "graphs", "graph_paths",
        "evaluation", "research_report", "iterations", "max_iterations", "current_step", "messages"
    ]
    base = {}
    # If state is an object, use attribute access; if dict, use dict access
    for field in required_fields:
        if isinstance(state, dict):
            base[field] = state.get(field)
        else:
            base[field] = getattr(state, field, None)
    # Overwrite with any updates
    for k, v in update_dict.items():
        base[k] = v
    return base

"""User Clarification and Research Brief Generation.

This module implements the scoping phase of the research workflow, where we:
1. Assess if the user's request needs clarification
2. Generate a detailed research brief from the conversation

The workflow uses structured output to make deterministic decisions about
whether sufficient context exists to proceed with research.
"""

from datetime import datetime
import json
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from typing_extensions import Literal
from langchain_core.messages import HumanMessage, AIMessage, get_buffer_string
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langgraph.graph import MessagesState



from agents.state import ResearchPlan, ResearchReport, ResearchAgentState
from agents.tools import tavily_search, think_tool, draw_graph
from agents.prompts import clarify_with_user_instructions, transform_messages_into_research_topic_prompt
from agents.state_scope import ClarifyWithUser, ResearchQuestion, AgentInputState

from dotenv import load_dotenv
import os
load_dotenv()

# Get the API key from the environment variable
api_key = os.getenv("GOOGLE_API_KEY")
# ===== UTILITY FUNCTIONS =====
tools = [tavily_search, think_tool, draw_graph]


from datetime import datetime

def get_today_str() -> str:
    """Get current date in a human-readable format."""
    
    today = datetime.now()
    return f"{today.strftime('%a %b')} {today.day}, {today.year}"

# ===== CONFIGURATION =====

# Initialize model
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0, api_key=api_key)
model = model.bind_tools(tools) 
# ===== WORKFLOW NODES =====

def clarify_with_user(state: ResearchAgentState) -> Command[Literal["write_research_brief", "__end__"]]:
    """
    Determine if the user's request contains sufficient information to proceed with research.

    Uses structured output to make deterministic decisions and avoid hallucination.
    Routes to either research brief generation or ends with a clarification question.
    """
    # Set up structured output model
    structured_output_model = model.with_structured_output(ClarifyWithUser)

    # Invoke the model with clarification instructions
    response = structured_output_model.invoke([
        HumanMessage(content=clarify_with_user_instructions.format(
            messages=get_buffer_string(messages=state.messages), 
            date=get_today_str()
        ))
    ])

    
    if response.need_clarification:
        return Command(
            goto=END,
            update=propagate_state(state, {"messages": [{"type": "ai", "content": response.question}]})
        )
    else:
        return Command(
            goto="write_research_brief",
            update=propagate_state(state, {"messages": [{"type": "ai", "content": response.verification}]})
        )

def write_research_brief(state: ResearchAgentState):
    """
    Transform the conversation history into a comprehensive research brief.

    Uses structured output to ensure the brief follows the required format
    and contains all necessary details for effective research.
    """
    # Always use the full conversation history for the prompt
    full_history = get_buffer_string(getattr(state, "messages", []))
    prompt = transform_messages_into_research_topic_prompt.format(
        messages=full_history,
        date=get_today_str()
    )
    structured_output_model = model.with_structured_output(ResearchQuestion)
    response = structured_output_model.invoke([
        HumanMessage(content=prompt)
    ])

    # Fallback: If the research brief is too short or just echoes the last message, use the initial request and clarification
    brief = response.research_brief
    if not brief or len(brief.strip()) < 20:
        user_msgs = [m.content for m in getattr(state, "messages", []) if isinstance(m, HumanMessage)]
        brief = " ".join(user_msgs)

    messages = state["messages"] if isinstance(state, dict) else state.messages
    messages = list(messages) if messages else []
    messages.append({"type": "ai", "content": brief})
    return propagate_state(state, {
        "research_brief": brief,
        "messages": messages,
        "supervisor_messages": [{"type": "human", "content": f"{brief}."}]
    })

# ===== RESEARCH PHASE NODES =====
def plan_research(state: ResearchAgentState):
    research_brief = state.research_brief
    plan_prompt = f"""
    You are an expert research assistant. Based on the following research brief,
    create a structured step-by-step research plan.

    Research brief: {research_brief}

    Format output as JSON matching the ResearchPlanSchema.
    """
    structured_output_model = model.with_structured_output(ResearchPlan)
    response = structured_output_model.invoke([HumanMessage(content=plan_prompt)])

    steps = [step.dict() for step in response.steps]
    return propagate_state(state, {
        "messages": [{"type": "ai", "content": f"Research plan created with {len(steps)} steps."}],
        "research_plan": response,
        "current_step": "Planning completed"
    })


def gather_information(state: ResearchAgentState):

    # Ensure gathered_info is a list
    gathered_info = state.gathered_information or []
    iterations = state.iterations

    # Get steps from research_plan
    steps = state.research_plan.steps if (state.research_plan is not None and hasattr(state.research_plan, 'steps')) else []
    for step in steps:
        # Use step.description or step.action as the query
        query = step.description
        # Use .invoke for langchain tool
        results = tavily_search.invoke(query)
        gathered_info.append({"query": query, "results": results})

    from agents.state import GatheredInformation, InformationItem
    # Convert dicts to InformationItem objects if needed
    info_items = []
    for item in gathered_info:
        if isinstance(item, dict):
            info_items.append(InformationItem(
                query=item.get("query", ""),
                source=item.get("source", ""),
                snippet=item.get("results", ""),
                metadata=None
            ))
        else:
            info_items.append(item)

    gathered_obj = GatheredInformation(topic=state.research_brief, items=info_items)
    return propagate_state(state, {
        "messages": [{"type": "ai", "content": f"Information gathered. Iteration {iterations + 1}"}],
        "gathered_information": gathered_obj,
        "iterations": iterations + 1,
        "current_step": f"Gathering info (Iteration {iterations + 1})"
    })


def generate_graph_node(state: ResearchAgentState):

    import re
    gathered = state.gathered_information
    data = []
    # Determine axes from state or fallback
    x_label = getattr(state, "graph_x_label", "X")
    y_label = getattr(state, "graph_y_label", "Y")
    chart_type = getattr(state, "graph_type", "bar")
    items = gathered.items if hasattr(gathered, "items") else gathered

    # Try to extract pairs based on axis labels
    for item in items:
        snippet = item.snippet if hasattr(item, "snippet") else str(item)
        # Try to find lines with both axis values
        # Example: "Year: 2020, Price: 2.5" or "Region: Central, Quantity: 1000"
        pattern = rf"{x_label}[:\s]*([\w\-]+)[,;\s]+{y_label}[:\s]*([\d\.]+)"
        matches = re.findall(pattern, snippet, re.IGNORECASE)
        for x_val, y_val in matches:
            try:
                data.append({"name": str(x_val), "value": float(y_val)})
            except Exception:
                continue

    # Fallback: If no pairs found, try to extract any number for y, and use line index for x
    if not data:
        for idx, item in enumerate(items):
            snippet = item.snippet if hasattr(item, "snippet") else str(item)
            match = re.search(r"(\d+(\.\d+)?)", snippet)
            if match:
                data.append({"name": f"{x_label} {idx+1}", "value": float(match.group(1))})

    # If still no data, generate mock data
    if not data:
        if chart_type == "bar" or chart_type == "line":
            mock_x = [f"{x_label} {i}" for i in range(1, 11)]
            mock_y = [round(10 + i * 2 + (i % 3), 2) for i in range(10)]
            data = [{"name": x, "value": y} for x, y in zip(mock_x, mock_y)]
        elif chart_type == "pie":
            mock_x = [f"{x_label} {i}" for i in range(1, 6)]
            mock_y = [round(20 + i * 5, 2) for i in range(5)]
            data = [{"name": x, "value": y} for x, y in zip(mock_x, mock_y)]
        msg = f"No structured data found. Mock data generated for visualization."
    else:
        msg = f"Graph created from extracted data."

    graph_input = {
        "title": getattr(state, "graph_title", "Research Data"),
        "data": data,
        "chart_type": chart_type,
        "x_key": "name",
        "y_key": "value",
        "x_label": x_label,
        "y_label": y_label,
        "filename": getattr(state, "graph_filename", "research_graph.png")
    }
    graph_path = draw_graph.invoke(graph_input)

    return propagate_state(state, {
        "messages": [{"type": "ai", "content": f"{msg} Graph saved to: {graph_path}"}],
        "graph_paths": state.graph_paths + [graph_path]
    })


def evaluate_information(state: ResearchAgentState):
    iterations = state["iterations"] if isinstance(state, dict) else state.iterations
    gathered_info = state["gathered_information"] if isinstance(state, dict) else state.gathered_information
    # Handle GatheredInformation object or fallback to list/tuple
    if iterations >= (state["max_iterations"] if isinstance(state, dict) else state.max_iterations):
        return propagate_state(state, {
            "messages": [{"type": "ai", "content": "Enough information collected."}],
            "current_step": "Evaluation complete"
        })
    if hasattr(gathered_info, "items"):
        items = gathered_info.items
    elif isinstance(gathered_info, (list, tuple)):
        items = gathered_info
    else:
        items = []
    extra_queries = []
    for i in items:
        if hasattr(i, 'query'):
            extra_queries.append(f"More info on {getattr(i, 'query', '')}")
        elif isinstance(i, dict):
            extra_queries.append(f"More info on {i.get('query', '')}")
        else:
            extra_queries.append("More info on (unknown)")
    return propagate_state(state, {
        "messages": [{"type": "ai", "content": "More info needed."}],
        # Optionally, add extra_queries to messages or a new field if needed
        "current_step": "Evaluation requested more info"
    })


def generate_report(state: ResearchAgentState):
    gathered_info = state["gathered_information"] if isinstance(state, dict) else state.gathered_information
    research_brief = state["research_brief"] if isinstance(state, dict) else state.research_brief
    # Handle GatheredInformation object or fallback to list/tuple
    if hasattr(gathered_info, "items"):
        items = gathered_info.items
    elif isinstance(gathered_info, (list, tuple)):
        items = gathered_info
    else:
        items = []
    all_info = "\n\n".join([
        f"Query: {i.get('query', '') if isinstance(i, dict) else getattr(i, 'query', '')}\nResults: {i.get('results', '') if isinstance(i, dict) else getattr(i, 'snippet', '')}"
        for i in items
    ])

    report_prompt = f"""
    Based on the following research info, create a comprehensive report.

    Research brief: {research_brief}

    Info:
    {all_info}

    Use structured output: ResearchReportSchema
    """
    structured_output_model = model.with_structured_output(ResearchReport)
    response = structured_output_model.invoke([HumanMessage(content=report_prompt)])

    return propagate_state(state, {
        "messages": [{"type": "ai", "content": f"Report generated: {response.topic}"}],
        "research_report": response.dict(),
        "current_step": "Report generation complete"
    })


# ===== GRAPH CONSTRUCTION =====
checkpointer = InMemorySaver()
research_builder = StateGraph(ResearchAgentState, input_schema=ResearchAgentState)

# Scoping nodes
research_builder.add_node("clarify_with_user", clarify_with_user)
research_builder.add_node("write_research_brief", write_research_brief)

# Research nodes
research_builder.add_node("plan_research", plan_research)
research_builder.add_node("gather_information", gather_information)
research_builder.add_node("generate_graph", generate_graph_node)
research_builder.add_node("evaluate_information", evaluate_information)
research_builder.add_node("generate_report", generate_report)

# Edges
research_builder.add_edge(START, "clarify_with_user")
research_builder.add_edge("clarify_with_user", "write_research_brief")
research_builder.add_edge("write_research_brief", "plan_research")
research_builder.add_edge("plan_research", "gather_information")
research_builder.add_edge("gather_information", "generate_graph")
research_builder.add_edge("generate_graph", "evaluate_information")
research_builder.add_edge("evaluate_information", "generate_report")
research_builder.add_edge("generate_report", END)

# Compile
agent = research_builder.compile(checkpointer=checkpointer)




