# autonomous-agent-project/agent/planner.py (Integrating Enhanced Terminal Tool)

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
import traceback # Import traceback for error logging

# --- Tool Imports ---
# --- Standard Tools ---
from tools.browser_tool import browser_tool, extract_tables_tool # Keep both
from tools.filesystem_tool import read_file_tool, write_file_tool, list_directory_tool, append_file_tool # Keep all FS tools
from tools.reporting_tool import generate_basic_pdf_report_tool, generate_pdf_with_chart_tool # Keep both PDF tools
from tools.delete_file_tool import delete_confirmation_tool # Keep delete confirmation
from tools.stock_data_tool import stock_data_tool # Keep stock tool
from tools.data_processing_tool import describe_csv_tool # Keep data processing tool
from langchain_community.tools import DuckDuckGoSearchRun # Keep search tool

# --- IMPORT ENHANCED TERMINAL TOOL ---
# from tools.terminal_tool import terminal_tool # <-- Comment out or remove the OLD basic terminal tool import
from tools.terminal_tool import terminal_tool_enhanced # <-- Import the NEW enhanced terminal tool
# --- End Tool Imports ---

load_dotenv()

# --- Default Model Configuration ---
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
    """
    Initializes the LangChain agent with all enhanced tools, including the
    enhanced terminal tool for running allowed commands and safe scripts.
    """
    print(f"\n--- Initializing Agent (Google Gemini) ---")
    print(f"  Model: {model_name}, Temp: {temperature}, TopP: {top_p}, TopK: {top_k}, Verbose Run: {verbose}")
    print("-" * 40)

    # 1. Initialize LLM
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key: raise ValueError("GOOGLE_API_KEY not found.")
    try:
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=google_api_key, temperature=temperature, top_p=top_p, top_k=top_k, convert_system_message_to_human=True)
        print(f"Successfully initialized Google Gemini LLM: {model_name}")
    except Exception as e: print(f"Error initializing LLM: {e}"); traceback.print_exc(); raise

    # 2. Define FULL Tool List (Using terminal_tool_enhanced)
    search_tool = DuckDuckGoSearchRun()
    tools = [
        search_tool,
        browser_tool,               # For general text
        extract_tables_tool,        # Specifically for HTML tables
        stock_data_tool,            # Keep if used for other tasks
        terminal_tool_enhanced,
        read_file_tool,
        write_file_tool,
        append_file_tool,
        list_directory_tool,
        delete_confirmation_tool,
        describe_csv_tool,
        generate_basic_pdf_report_tool,
        generate_pdf_with_chart_tool, # Keep flexible charting tool
    ]

    # (Optional availability checks can remain here)
    try: from tools.reporting_tool import MATPLOTLIB_AVAILABLE; print(f"Matplotlib Available: {MATPLOTLIB_AVAILABLE}")
    except ImportError: print("INFO: Matplotlib availability check skipped.")
    try: from tools.data_processing_tool import PANDAS_AVAILABLE; print(f"Pandas Available: {PANDAS_AVAILABLE}")
    except ImportError: print("INFO: Pandas availability check skipped.")
    # Add check for yfinance if desired

    tool_names = [tool.name for tool in tools]
    print(f"Agent will have access to {len(tools)} tools: {tool_names}") # Verify terminal tool name is updated

    # 3. Create Agent Prompt
    try: prompt_template = hub.pull("hwchase17/react")
    except Exception as e: print(f"Error pulling prompt: {e}"); raise

    # 4. Create the Agent
    try: agent = create_react_agent(llm=llm, tools=tools, prompt=prompt_template)
    except Exception as e: print(f"Error creating agent: {e}"); raise

    # 5. Create the Agent Executor
    try:
        agent_executor = AgentExecutor(
            agent=agent, tools=tools, verbose=verbose, handle_parsing_errors=True,
            max_iterations=25
        )
    except Exception as e: print(f"Error creating executor: {e}"); raise

    print("Agent Executor created successfully.")
    return agent_executor