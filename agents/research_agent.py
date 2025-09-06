import json
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List, Dict
import re
import os

from .state import ResearchAgentInput, ResearchAgentState, ResearchPlan, ResearchStep
from .tools import tavily_search, think_tool, draw_graph
from agents import state


llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
tools = [tavily_search, think_tool, draw_graph]
llm = llm.bind_tools(tools) # Integrate tools with the LLM
# binding to tools to the LLM

def create_research_agent():

    # --------------------------
    # 1. Plan research
    # --------------------------
    def plan_research(state: ResearchAgentState):
        research_brief = state.research_brief

        plan_prompt = f"""
        You are an expert research assistant. Based on the following research brief, create a structured step-by-step research plan.

        Research brief: {research_brief}

        The plan should include:
        1. A clear research topic.
        2. A list of specific steps to gather information, analyze data, and generate insights.
        3. Each step should have a step number, action (e.g., search, summarize, analyze), and a brief description.

        Format the output as JSON matching the ResearchPlan schema.
        """
        response = llm.invoke([HumanMessage(content=plan_prompt)])
        
        try:
            plan_data = json.loads(response.content)
            research_plan = ResearchPlan(**plan_data)
            steps = [step.dict() for step in research_plan.steps]
            return {
                "messages": [AIMessage(content=f"Research plan created with {len(steps)} steps.")],
                "research_plan": [step.description for step in steps],
                "current_step": "Planning completed"
            }
        except Exception as e:
            return {
                "messages": [AIMessage(content=f"Failed to parse research plan: {str(e)}")],
                "research_plan": [],
                "current_step": "Planning failed"
            }


    # --------------------------
    # 2. Gather information
    # --------------------------
    def gather_information(state: ResearchAgentState):
        research_plan = state.research_plan
        gathered_info = state.gathered_information
        iterations = state.iterations

        for query in research_plan:
            results = tavily_search(query)
            gathered_info.append({
                "query": query,
                "results": results
            })

        return {
            "messages": [AIMessage(content=f"Information gathering completed. Iteration {iterations + 1}")],
            "gathered_information": gathered_info,
            "iterations": iterations + 1,
            "current_step": f"Gathering information (Iteration {iterations + 1})"
        }

    # --------------------------
    # 3. Generate graphs
    # --------------------------
    def generate_graph_node(state: ResearchAgentState):
        gathered = state.gathered_information

        # Extract numeric data dynamically (example: assume each result has a 'score' or similar field)
        data = []
        for item in gathered:
            for r in item["results"].split("\n"):
                # Very simple extraction: treat lines containing numbers as numeric metrics
                match = re.search(r'(\d+(\.\d+)?)', r)
                if match:
                    data.append({"name": r[:50], "value": float(match.group(1))})

        if not data:
            return {"messages": [AIMessage(content="No numeric data found to generate a graph.")]}

        graph_path = draw_graph(
            title=state.get("graph_title", "Research Data"),
            data=data,
            chart_type=state.get("graph_type", "bar"),
            x_key="name",
            y_key="value",
            x_label=state.get("graph_x_label", "Entity"),
            y_label=state.get("graph_y_label", "Metric"),
            filename=state.get("graph_filename", "research_graph.png")
        )

        return {
            "messages": [AIMessage(content=f"Graph created at {graph_path}")],
            "graph_path": graph_path
        }

    # --------------------------
    # 4. Evaluate information
    # --------------------------
    def evaluate_information(state: ResearchAgentState):
        gathered_info = state.gathered_information
        iterations = state.iterations
        max_iterations = state.max_iterations

        # Simple heuristic: if we have more than 1 iteration, consider sufficient
        if iterations >= max_iterations:
            return {
                "messages": [AIMessage(content="Information evaluation: Sufficient information gathered.")],
                "current_step": "Evaluation completed - sufficient information"
            }

        # Otherwise, request more searches (optional)
        additional_queries = [f"More info on {item['query']}" for item in gathered_info]
        return {
            "messages": [AIMessage(content=f"Need more information. Additional queries: {additional_queries}")],
            "research_plan": additional_queries,
            "current_step": "Evaluation completed - need more information"
        }

    # --------------------------
    # 5. Generate report
    # --------------------------
    def generate_report(state: ResearchAgentState):
        gathered_info = state.gathered_information
        research_brief = state.research_brief

        all_info = "\n\n".join([f"Query: {item['query']}\nResults: {item['results']}" 
                               for item in gathered_info])

        report_prompt = f"""
        Based on the following research information, create a comprehensive, well-structured report.

        Research brief: {research_brief}

        Gathered information:
        {all_info}

        Create a report with Introduction, Key Findings, Analysis, Conclusion, and References.
        """
        response = llm.invoke([HumanMessage(content=report_prompt)])
        report = response.content

        return {
            "messages": [AIMessage(content=report)],
            "research_report": report,
            "current_step": "Report generation completed"
        }

    # --------------------------
    # Build the workflow
    # --------------------------
    workflow = StateGraph(ResearchAgentState)
    workflow.add_node("plan_research", plan_research)
    workflow.add_node("gather_information", gather_information)
    workflow.add_node("generate_graph", generate_graph_node)
    workflow.add_node("evaluate_information", evaluate_information)
    workflow.add_node("generate_report", generate_report)

    workflow.set_entry_point("plan_research")
    workflow.add_edge("plan_research", "gather_information")
    workflow.add_edge("gather_information", "generate_graph")
    workflow.add_edge("generate_graph", "evaluate_information")
    workflow.add_edge("evaluate_information", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()


agent = create_research_agent()
