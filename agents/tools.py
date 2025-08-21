from tavily import TavilyClient
from typing import List, Dict
import json

import os
from dotenv import load_dotenv

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