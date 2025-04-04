# autonomous-agent-project/agent/planner.py (Using Unified Auto-Chart Tool & Gemini)

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI # Ensure this is the correct import for your setup
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
import traceback

# --- Tool Imports ---
from tools.browser_tool import browser_tool, extract_tables_tool
from tools.terminal_tool import terminal_tool_enhanced # Use enhanced version
from tools.filesystem_tool import read_file_tool, write_file_tool, list_directory_tool, append_file_tool
# --- Import CORRECT reporting tools ---
from tools.reporting_tool import (
    generate_basic_pdf_report_tool, # Keep text-only fallback
    generate_pdf_auto_chart_tool    # <-- Import the UNIFIED tool
    # Ensure generate_pdf_with_line_chart_tool & generate_pdf_with_bar_chart_tool are REMOVED or commented out if defined in reporting_tool.py
)
# --- ---
from tools.delete_file_tool import delete_confirmation_tool
from tools.stock_data_tool import stock_data_tool
from tools.data_processing_tool import describe_csv_tool
from langchain_community.tools import DuckDuckGoSearchRun
# --- End Tool Imports ---

load_dotenv() # Load .env variables early

# --- Default Model Configuration (For Google Gemini) ---
DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest" # Or "gemini-1.5-pro-latest", "gemini-1.0-pro"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.95
DEFAULT_TOP_K = 40
# --- ---

def initialize_agent(
    verbose: bool = False,
    model_name: str = DEFAULT_MODEL_NAME,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    top_k: int = DEFAULT_TOP_K
    ):
    """
    Initializes the LangChain agent with Google Gemini, specified parameters,
    and the toolset including the unified auto-charting PDF tool.
    """
    print(f"\n--- Initializing Agent (Google Gemini) ---")
    print(f"  Model: {model_name}, Temp: {temperature}, TopP: {top_p}, TopK: {top_k}, Verbose Run: {verbose}")
    print("-" * 40)

    # 1. Initialize LLM
    llm = None
    try:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            print("ERROR: GOOGLE_API_KEY not found in environment variables.")
            raise ValueError("Google API key not found in .env file. Please set GOOGLE_API_KEY.")

        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=google_api_key,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            convert_system_message_to_human=True # Often helpful for Gemini agents
        )
        print(f"Successfully initialized Google Gemini LLM: {model_name}")

    except Exception as e:
         print(f"ERROR: Failed to initialize Google Gemini LLM model '{model_name}'.")
         print(f"       Make sure model name is correct and API key is valid/enabled.")
         print(f"       Underlying Error: {e}"); traceback.print_exc(); raise

    # 2. Define FULL Tool List (Using UNIFIED chart tool)
    search_tool = DuckDuckGoSearchRun()
    tools = [
        # Research & Data Fetching
        search_tool,
        browser_tool,           # General text scraping
        extract_tables_tool,    # Specific table scraping
        stock_data_tool,        # Stock market data

        # Execution & Filesystem
        terminal_tool_enhanced, # Sandboxed/limited terminal access
        read_file_tool,
        write_file_tool,
        append_file_tool,
        list_directory_tool,
        delete_confirmation_tool,# Requests delete confirmation

        # Data Processing
        describe_csv_tool,      # Basic CSV stats

        # Reporting / Output
        generate_basic_pdf_report_tool, # Text-only PDF fallback
        generate_pdf_auto_chart_tool,   # <-- Use the UNIFIED tool
    ]

    # --- Optional Availability Checks ---
    try:
        # Check if reporting tool indicates charting is possible
        from tools.reporting_tool import MATPLOTLIB_AVAILABLE
        print(f"Matplotlib Available Check: {MATPLOTLIB_AVAILABLE}")
        if not MATPLOTLIB_AVAILABLE:
             print("  WARNING: Charting tools will report errors if used.")
             # Optionally filter out charting tools if libs are missing
             # tools = [t for t in tools if t.name != generate_pdf_auto_chart_tool.name]
    except ImportError: print("INFO: Matplotlib availability check skipped.")

    try:
        # Check if data processing tool indicates pandas is available
        from tools.data_processing_tool import PANDAS_AVAILABLE
        print(f"Pandas Available Check: {PANDAS_AVAILABLE}")
        if not PANDAS_AVAILABLE:
             print("  WARNING: Data processing/charting tools may error if used.")
             # Optionally filter out pandas-dependent tools
             # tools = [t for t in tools if t.name not in [extract_tables_tool.name, stock_data_tool.name, describe_csv_tool.name, generate_pdf_auto_chart_tool.name]]
    except ImportError: print("INFO: Pandas availability check skipped.")
    # --- ---

    tool_names = [tool.name for tool in tools]
    print(f"Agent will have access to {len(tools)} tools: {tool_names}") # Verify list

    # 3. Create Agent Prompt (Standard ReAct)
    try:
        prompt_template = hub.pull("hwchase17/react")
        print("DEBUG: Pulled ReAct prompt from LangChain Hub.")
    except Exception as e:
        print(f"Error pulling prompt: {e}. Check network/prompt ID."); raise

    # 4. Create the Agent
    try:
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt_template)
        print("ReAct agent created successfully.")
    except Exception as e:
        print(f"Error creating agent: {e}"); traceback.print_exc(); raise

    # 5. Create the Agent Executor
    try:
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=verbose, # Controls execution logging
            handle_parsing_errors=True, # More robust parsing
            max_iterations=25 # Allow enough steps for research+charting
        )
        print("Agent Executor created successfully.")
    except Exception as e:
        print(f"Error creating executor: {e}"); traceback.print_exc(); raise

    return agent_executor