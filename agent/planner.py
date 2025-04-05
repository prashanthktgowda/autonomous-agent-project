# autonomous-agent-project/agent/planner.py (Corrected Imports for Separate PDF Tools)

import os
from dotenv import load_dotenv
# --- Choose and import your LLM ---
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_openai import ChatOpenAI
# from langchain_community.llms import HuggingFaceHub
# --- ---
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
import traceback

# --- Tool Imports ---
from tools.browser_tool import browser_tool, extract_tables_tool
from tools.terminal_tool import terminal_tool_enhanced # Use enhanced terminal
from tools.filesystem_tool import (
    read_file_tool, write_file_tool, list_directory_tool, append_file_tool
    # replace_text_tool, # Ensure exists if uncommented
)
# --- MODIFY REPORTING IMPORTS ---
from tools.reporting_tool import (
    generate_basic_pdf_report_tool, # <-- IMPORT BASIC TOOL
    generate_pdf_with_chart_tool    # <-- IMPORT EXPLICIT CHART TOOL
    # from tools.reporting_tool import generate_pdf_tool # <-- REMOVE THIS LINE (or comment out)
)
# --- END MODIFY ---
from tools.delete_file_tool import delete_confirmation_tool
from tools.stock_data_tool import stock_data_tool
from tools.data_processing_tool import describe_csv_tool
from langchain_community.tools import DuckDuckGoSearchRun
# --- End Tool Imports ---

load_dotenv() # Load .env variables early

# --- Default Model Configuration (For Google Gemini) ---
DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest"
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
    """Initializes agent with specified model parameters and the separate PDF tools."""
    # (Keep print statements and LLM initialization)
    print(f"\n--- Initializing Agent (Google Gemini) ---")
    print(f"  Model: {model_name}, Temp: {temperature}, TopP: {top_p}, TopK: {top_k}, Verbose Run: {verbose}")
    print("-" * 40)
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key: raise ValueError("GOOGLE_API_KEY not found.")
    try:
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=google_api_key, temperature=temperature, top_p=top_p, top_k=top_k, convert_system_message_to_human=True)
        print(f"Successfully initialized Google Gemini LLM: {model_name}")
    except Exception as e: print(f"ERROR initializing LLM: {e}"); traceback.print_exc(); raise

    # --- Define FULL Tool List (using SEPARATE PDF tools) ---
    search_tool = DuckDuckGoSearchRun()
    tools = [
        search_tool,
        browser_tool,
        extract_tables_tool,
        stock_data_tool,
        terminal_tool_enhanced,
        read_file_tool,
        write_file_tool,
        append_file_tool,
        # replace_text_tool,
        list_directory_tool,
        delete_confirmation_tool,
        describe_csv_tool,
        # --- USE SEPARATE PDF TOOLS ---
        generate_basic_pdf_report_tool, # <-- Use Basic Tool
        generate_pdf_with_chart_tool,   # <-- Use Explicit Chart Tool
        # generate_pdf_tool,            # <-- REMOVE CONSOLIDATED TOOL
        # --- END REPLACE ---
    ]

    # (Optional availability checks can remain here)
    try:
        from tools.reporting_tool import MATPLOTLIB_AVAILABLE, PANDAS_AVAILABLE
        print(f"Matplotlib Available: {MATPLOTLIB_AVAILABLE}"); print(f"Pandas Available: {PANDAS_AVAILABLE}")
        if not MATPLOTLIB_AVAILABLE: print("  WARNING: Charting tool will error if used.")
        if not PANDAS_AVAILABLE: print("  WARNING: Tools needing Pandas (charting, data processing, table extract) may error.")
    except ImportError: print("INFO: Could not check lib availability flags.")


    tool_names = [tool.name for tool in tools]
    print(f"Agent will have access to {len(tools)} tools: {tool_names}") # Verify list

    # --- Create Agent Prompt ---
    try: prompt_template = hub.pull("hwchase17/react")
    except Exception as e: print(f"Error pulling prompt: {e}"); raise

    # --- Create the Agent ---
    try: agent = create_react_agent(llm=llm, tools=tools, prompt=prompt_template)
    except Exception as e: print(f"Error creating agent: {e}"); raise

    # --- Create the Agent Executor ---
    try:
        agent_executor = AgentExecutor(
            agent=agent, tools=tools, verbose=verbose, handle_parsing_errors=True,
            max_iterations=25
        )
    except Exception as e: print(f"Error creating executor: {e}"); raise

    print("Agent Executor created successfully.")
    return agent_executor