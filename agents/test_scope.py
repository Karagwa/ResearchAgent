
import uuid
import json
from langchain_core.messages import AIMessage, HumanMessage
from scoping_agent import agent  # Your compiled StateGraph
from state import ResearchAgentState  # Your Pydantic state schema

# -----------------------------
# CONFIG
# -----------------------------
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}

# -----------------------------
# INTERACTIVE USER INPUT FOR REQUIRED FIELDS
# -----------------------------
def prompt_required_fields():
    print("Please provide your raw research request. The agent will transform this into a comprehensive research brief.")
    user_input = input("Describe your research request: ").strip()
    initial_message = f"User research request: {user_input}"
    return {
        "user_input": user_input,
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

# -----------------------------
# RUN AGENT END-TO-END
# -----------------------------
state = prompt_required_fields()
step_counter = 1

while True:
    # Always ensure user_input is present in state before invoking agent
    if not state.get("user_input"):
        state["user_input"] = input("Describe your research request: ").strip()

    state = agent.invoke(state, config=config)

    # Print last AI message if any
    if state.get("messages"):
        last_ai = state["messages"][-1]
        print(f"\n=== Step {step_counter} AI Output ===")
        print(getattr(last_ai, "content", str(last_ai)))
        step_counter += 1

    # If AI asks a clarification question, prompt user for input
    if state.get("messages") and "?" in getattr(state["messages"][-1], "content", ""):
        clarification = input("\n--- Clarification requested ---\n" + getattr(state["messages"][-1], "content", "") + "\nYour reply: ")
        state["messages"].append(HumanMessage(content=clarification))
        # Optionally, prompt for missing fields if question matches known schema
        if "location" in getattr(state["messages"][-1], "content", "").lower():
            location = input("Location (city/country): ").strip()
            state["user_input"] += f" in {location}"
        if "graph type" in getattr(state["messages"][-1], "content", "").lower():
            graph_type = input("Graph type (bar, line, pie, etc.): ").strip()
            state["user_input"] += f" with a {graph_type} graph"
        if "x-axis" in getattr(state["messages"][-1], "content", "").lower():
            x_axis = input("X-axis label: ").strip()
            state["user_input"] += f" (X-axis: {x_axis})"
        if "y-axis" in getattr(state["messages"][-1], "content", "").lower():
            y_axis = input("Y-axis label: ").strip()
            state["user_input"] += f" (Y-axis: {y_axis})"

    # Print the research brief if available
    if state.get("research_brief"):
        print("\n=== RESEARCH BRIEF ===\n")
        print(state["research_brief"])

    # Print the research plan if available
    if state.get("research_plan"):
        print("\n=== RESEARCH PLAN ===\n")
        print(state["research_plan"])

    # Print gathered information if available
    if state.get("gathered_information"):
        print("\n=== GATHERED INFORMATION ===\n")
        print(state["gathered_information"])

    # Print the research report if generated
    if state.get("research_report"):
        print("\n=== FINAL RESEARCH REPORT ===\n")
        print(json.dumps(state["research_report"], indent=2))
        break

    # Optional: safety check to prevent infinite loops
    if step_counter > 20:
        print("Reached max steps, exiting loop to avoid infinite run.")
        break
