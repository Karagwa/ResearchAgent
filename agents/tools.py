from datetime import datetime
from pathlib import Path
from tavily import TavilyClient
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from langchain.tools import tool
import matplotlib.pyplot as plt

# Folder to save generated graphs
GRAPH_OUTPUT_DIR = "graphs"
os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)

load_dotenv()

class SearchTool:
    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment variables.")
        self.client = TavilyClient(api_key=api_key)
    
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        try:
            response = self.client.search(query=query, max_results=max_results)
            return response.get('results', [])
        except Exception as e:
            return [{"error": f"Search failed: {str(e)}"}]
    
    def process_search_results(self, query: str, max_results: int = 5) -> str:
        results = self.search(query, max_results)
        if not results or "error" in results[0]:
            return "No results found or search failed."
        
        formatted_results = f"Search results for '{query}':\n\n"
        for i, result in enumerate(results, 1):
            formatted_results += f"{i}. {result.get('title', 'No title')}\n"
            formatted_results += f"   URL: {result.get('url', 'No URL')}\n"
            formatted_results += f"   Content: {result.get('content', 'No content')[:200]}...\n\n"
        
        return formatted_results

search_tool = SearchTool()

@tool(parse_docstring=True)
def tavily_search(query: str, max_results: int = 5) -> str:
    """
    Perform a search using Tavily and return formatted results.

    Args:
        query (str): The search query string
        max_results (int): Maximum number of results to return (default 5)

    Returns:
        str: Formatted string of search results
    """
    return search_tool.process_search_results(query=query, max_results=max_results)


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """
    Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    Creates a deliberate pause in the research workflow for quality decision-making.

    Args:
        reflection (str): Detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        str: Confirmation that reflection was recorded
    """
    return f"Reflection recorded: {reflection}"


@tool(parse_docstring=True)
def draw_graph(
    title: str,
    data: List[Dict],
    chart_type: str = "bar",
    x_key: Optional[str] = None,
    y_key: Optional[str] = None,
    x_label: str = "",
    y_label: str = "",
    filename: str = "graph.png"
) -> str:
    """
    Draw a graph (bar, line, pie) from structured data and save as an image.

    Args:
        title (str): Title of the graph
        data (List[Dict]): List of dictionaries containing data points
        chart_type (str): 'bar', 'line', or 'pie'
        x_key (str, optional): Key in each dict for X-axis (ignored for pie)
        y_key (str, optional): Key in each dict for Y-axis (ignored for pie)
        x_label (str): Label for X-axis
        y_label (str): Label for Y-axis
        filename (str): Output filename (saved in graphs folder)

    Returns:
        str: File path to the saved graph image
    """
    plt.figure(figsize=(10,6))

    if chart_type.lower() == "bar":
        x_data = [item[x_key] for item in data]
        y_data = [item[y_key] for item in data]
        plt.bar(x_data, y_data, color='skyblue')
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.xticks(rotation=45, ha='right')

    elif chart_type.lower() == "line":
        x_data = [item[x_key] for item in data]
        y_data = [item[y_key] for item in data]
        plt.plot(x_data, y_data, marker='o', linestyle='-', color='green')
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.xticks(rotation=45, ha='right')

    elif chart_type.lower() == "pie":
        labels = [item[x_key] for item in data]
        sizes = [item[y_key] for item in data]
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)

    else:
        return f"Error: Unsupported chart_type '{chart_type}'. Choose 'bar', 'line', or 'pie'."

    plt.title(title)
    plt.tight_layout()

    output_path = os.path.join(GRAPH_OUTPUT_DIR, filename)
    plt.savefig(output_path)
    plt.close()
    return f"Graph saved to: {output_path}"


def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.now().strftime("%a %b %-d, %Y")

def get_current_dir() -> Path:
    """Get the current directory of the module.

    This function is compatible with Jupyter notebooks and regular Python scripts.

    Returns:
        Path object representing the current directory
    """
    try:
        return Path(__file__).resolve().parent
    except NameError:  # __file__ is not defined
        return Path.cwd()
