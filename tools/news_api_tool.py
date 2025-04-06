# tools/news_api_tool.py

import os
import requests # Library to make HTTP requests
import json # To parse the response
from langchain.tools import Tool
import traceback
from datetime import datetime, timedelta

# --- Configuration ---
NEWSAPI_BASE_URL = "https://newsapi.org/v2/"
# --- End Configuration ---

def get_news_headlines(query_or_source: str) -> str:
    """
    Fetches top headlines from NewsAPI.org based on a source ID (like 'hacker-news',
    'bbc-news', 'techcrunch') or a query string.
    Input: A single string which is either a SOURCE_ID or a search QUERY.
           Common Source IDs: hacker-news, bbc-news, reuters, associated-press,
                              techcrunch, the-verge, engadget, ars-technica.
           For general search use a query string like 'AI advancements' or 'latest tech news'.
    Returns: A formatted string listing top headlines (title and source) or an error message.
    Limits the number of headlines returned.
    """
    print(f"DEBUG [News Tool]: Received request: '{query_or_source}'")
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        return "Error: NEWSAPI_API_KEY not found in environment variables."
    if not isinstance(query_or_source, str) or not query_or_source.strip():
        return "Error: Input query or source ID cannot be empty."

    query = query_or_source.strip()
    params = {'apiKey': api_key, 'pageSize': 10} # Fetch 10, agent can decide how many to use
    endpoint = 'top-headlines' # Default endpoint

    # Basic heuristic: If input looks like a common source ID, use the 'sources' parameter.
    # Otherwise, treat it as a query string 'q'.
    # List from NewsAPI docs (check for updates) - this is not exhaustive!
    known_sources = ['hacker-news', 'bbc-news', 'reuters', 'associated-press', 'techcrunch', 'the-verge', 'engadget', 'ars-technica', 'google-news', 'cnn', 'fox-news', 'the-wall-street-journal', 'the-washington-post', 'time', 'wired']
    if query.lower() in known_sources:
        params['sources'] = query.lower()
        print(f"DEBUG [News Tool]: Using source ID: {query.lower()}")
    else:
        params['q'] = query
        # Optionally switch endpoint for keyword search if needed, but top-headlines often works
        # endpoint = 'everything' # 'everything' endpoint allows more params like date ranges
        print(f"DEBUG [News Tool]: Using query term: {query}")

    try:
        url = f"{NEWSAPI_BASE_URL}{endpoint}"
        print(f"DEBUG [News Tool]: Requesting URL: {url} with params: {params.get('q', params.get('sources'))}")
        response = requests.get(url, params=params, timeout=15) # 15 second timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        data = response.json()

        if data.get("status") != "ok":
            return f"Error: NewsAPI returned status '{data.get('status')}'. Code: {data.get('code')}, Message: {data.get('message', 'No message provided.')}"

        articles = data.get("articles", [])
        if not articles:
            return f"Success: No news articles found for '{query}'."

        print(f"DEBUG [News Tool]: Found {len(articles)} articles.")

        # Format the output for the agent
        output_lines = [f"Top {len(articles)} Headlines for '{query}':"]
        for i, article in enumerate(articles):
            title = article.get('title', 'N/A')
            source_name = article.get('source', {}).get('name', 'N/A')
            # url = article.get('url', '#') # Could include URL if needed
            output_lines.append(f"{i+1}. {title} (Source: {source_name})")

        return "\n".join(output_lines)

    except requests.exceptions.Timeout:
        print(f"News Tool Error: Request timed out for '{query}'.")
        return f"Error: Timeout connecting to NewsAPI for '{query}'."
    except requests.exceptions.RequestException as e:
        print(f"News Tool Error: Request failed for '{query}'. Error: {e}")
        traceback.print_exc()
        return f"Error: Failed to fetch news for '{query}'. Reason: {str(e)}"
    except json.JSONDecodeError:
         print(f"News Tool Error: Could not decode JSON response for '{query}'.")
         return f"Error: Invalid response format from NewsAPI for '{query}'."
    except Exception as e:
        print(f"News Tool Error: Unexpected error for '{query}'. Error: {e}")
        traceback.print_exc()
        return f"Error: An unexpected error occurred while fetching news for '{query}': {str(e)}"

# --- LangChain Tool Definition ---
news_api_tool = Tool(
    name="Get News Headlines",
    func=get_news_headlines,
    description=(
        "Use this tool to fetch recent top news headlines based on a specific source ID OR a search query. "
        "Input should be a single string: either a known SOURCE_ID (e.g., 'hacker-news', 'bbc-news', 'techcrunch') "
        "OR a search QUERY (e.g., 'artificial intelligence regulation', 'stock market trends'). "
        "The tool identifies if the input is likely a known source ID and queries accordingly. "
        "Output is a formatted list of the top headlines (title and source name) found for the input, or an error message. "
        "Use this instead of general web scraping for reliable news headlines."
    ),
)