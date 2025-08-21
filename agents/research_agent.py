from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List
import json
import re

from .state import AgentState
from .tools import search_tool


llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

def create_research_agent():
    """Create the research agent graph based on the article's architecture"""
    
    
    def plan_research(state: AgentState):
        """Node to plan the research approach"""
        research_query = state["research_query"]
        
        
        plan_prompt = f"""
        You are a research assistant. The user has asked: {research_query}
        
        Break this down into 3-5 specific search queries that will help you gather comprehensive information.
        Consider different aspects, perspectives, and related topics.
        
        Return your response as a JSON array of search queries.
        Example: ["query 1", "query 2", "query 3"]
        """
        
        response = llm.invoke([HumanMessage(content=plan_prompt)])
        
        try:
            
            json_match = re.search(r'\[.*\]', response.content, re.DOTALL)
            if json_match:
                research_plan = json.loads(json_match.group())
            else:
                
                research_plan = [q.strip() for q in response.content.split("\n") if q.strip() and not q.startswith(('{', '['))]
        except Exception as e:
            
            research_plan = [research_query]
        
        return {
            "messages": [AIMessage(content=f"Research plan created: {research_plan}")],
            "research_plan": research_plan,
            "iterations": 0,
            "current_step": "Planning completed"
        }
    
    def gather_information(state: AgentState):
        """Node to gather information using search tools"""
        research_plan = state["research_plan"]
        gathered_info = state.get("gathered_information", [])
        iterations = state.get("iterations", 0)
        
        
        for query in research_plan:
            search_results = search_tool.process_search_results(query)
            gathered_info.append({
                "query": query,
                "results": search_results
            })
        
        return {
            "messages": [AIMessage(content=f"Information gathering completed. Iteration {iterations + 1}")],
            "gathered_information": gathered_info,
            "iterations": iterations + 1,
            "current_step": f"Gathering information (Iteration {iterations + 1})"
        }
    
    def evaluate_information(state: AgentState):
        """Node to evaluate if enough information has been gathered"""
        gathered_info = state["gathered_information"]
        research_query = state["research_query"]
        iterations = state["iterations"]
        max_iterations = state.get("max_iterations", 3)
        
        
        all_info = "\n\n".join([f"Query: {item['query']}\nResults: {item['results']}" 
                               for item in gathered_info])
        
        
        evaluation_prompt = f"""
        Based on the following research information, determine if we have enough comprehensive 
        information to answer the research query: "{research_query}"
        
        Gathered information:
        {all_info}
        
        Consider:
        1. Have we covered all aspects of the query?
        2. Are there any gaps in our understanding?
        3. Do we need to search for more specific information?
        
        If the information is sufficient, respond with "SUFFICIENT".
        If more information is needed, respond with "INSUFFICIENT" and provide 1-2 additional 
        search queries that would help fill the gaps, in JSON format: ["query 1", "query 2"]
        """
        
        response = llm.invoke([HumanMessage(content=evaluation_prompt)])
        response_text = response.content.strip()
        
        if "SUFFICIENT" in response_text.upper() or iterations >= max_iterations:
            
            return {
                "messages": [AIMessage(content="Information evaluation: Sufficient information gathered.")],
                "current_step": "Evaluation completed - sufficient information"
            }
        else:
            
            try:
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    additional_queries = json.loads(json_match.group())
                else:
                    
                    additional_queries = [f"more about {research_query}", f"detailed analysis of {research_query}"]
                
                return {
                    "messages": [AIMessage(content=f"Information evaluation: Need more information. New queries: {additional_queries}")],
                    "research_plan": additional_queries,
                    "current_step": "Evaluation completed - need more information"
                }
            except:
                
                return {
                    "messages": [AIMessage(content="Information evaluation: Continuing with original plan.")],
                    "current_step": "Evaluation completed - continuing with original plan"
                }
    
    def generate_report(state: AgentState):
        """Node to generate the final research report"""
        gathered_info = state["gathered_information"]
        research_query = state["research_query"]
        
        
        all_info = "\n\n".join([f"Query: {item['query']}\nResults: {item['results']}" 
                               for item in gathered_info])
        
        
        report_prompt = f"""
        Based on the following research information, create a comprehensive, well-structured report.
        
        Research query: {research_query}
        
        Gathered information:
        {all_info}
        
        Create a detailed report with:
        1. Introduction
        2. Key findings with proper citations (include URLs)
        3. Analysis and synthesis of information
        4. Conclusion
        5. References
        
        The report should be professional, informative, and well-organized.
        """
        
        response = llm.invoke([HumanMessage(content=report_prompt)])
        report = response.content
        
        return {
            "messages": [AIMessage(content=report)],
            "research_report": report,
            "current_step": "Report generation completed"
        }
    
    
    workflow = StateGraph(AgentState)
    
    
    workflow.add_node("plan_research", plan_research)
    workflow.add_node("gather_information", gather_information)
    workflow.add_node("evaluate_information", evaluate_information)
    workflow.add_node("generate_report", generate_report)
    
    
    workflow.set_entry_point("plan_research")
    workflow.add_edge("plan_research", "gather_information")
    workflow.add_edge("gather_information", "evaluate_information")
    
    
    def decide_next_step(state):
        last_message = state["messages"][-1].content if state["messages"] else ""
        if "Sufficient information" in last_message or state.get("iterations", 0) >= state.get("max_iterations", 3):
            return "generate_report"
        else:
            return "gather_information"
    
    workflow.add_conditional_edges(
        "evaluate_information",
        decide_next_step,
        {
            "generate_report": "generate_report",
            "gather_information": "gather_information"
        }
    )
    
    workflow.add_edge("generate_report", END)
    
   
    return workflow.compile()


research_agent = create_research_agent()