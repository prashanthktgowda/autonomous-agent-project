# autonomous-agent-project/agent/planner.py

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

# --- Tool Imports ---
from tools.browser_tool import browser_tool
from tools.terminal_tool import terminal_tool
from tools.filesystem_tool import read_file_tool, write_file_tool, list_directory_tool
# Import BOTH PDF tools now
from tools.reporting_tool import generate_basic_pdf_report_tool, generate_pdf_with_chart_tool
# Import Search Tool
from langchain_community.tools import DuckDuckGoSearchRun
# --- End Tool Imports ---

load_dotenv()

def initialize_agent(verbose: bool = False):
    """
    Initializes the LangChain agent with tools including Search and Charting PDF.
    """
    print("Initializing Google AI Studio (Gemini) LLM and Agent...")

    # 1. Initialize LLM (Same as before)
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("Google API key not found in .env file. Please set GOOGLE_API_KEY.")
    model_name = "gemini-1.5-flash-latest"
    print(f"Using Google Gemini model: {model_name}")
    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=google_api_key,
            temperature=0.1,
        )
        print("Successfully initialized Google Gemini LLM.")
    except Exception as e:
         print(f"Error initializing Google Gemini LLM: {e}")
         raise

    # 2. Define Tools (ADD Search and Charting PDF tool)
    search_tool = DuckDuckGoSearchRun()
    tools = [
        search_tool, # Add search tool, often useful first
        browser_tool,
        terminal_tool, # Keep security warnings in mind
        read_file_tool,
        write_file_tool,
        list_directory_tool,
        generate_basic_pdf_report_tool, # Tool for text-only PDFs
        generate_pdf_with_chart_tool,   # Tool for PDFs with a chart
    ]
    # Check if matplotlib is available and potentially disable the chart tool if not
    # (The tool function itself checks, but good practice to inform the user here too)
    try:
         from tools.reporting_tool import MATPLOTLIB_AVAILABLE
         if not MATPLOTLIB_AVAILABLE:
              print("WARNING: Matplotlib not found. PDF chart generation tool will be available but return an error if used.")
              # Optionally remove the tool if unavailable:
              # tools = [t for t in tools if t.name != "Generate PDF Report with Bar Chart"]
    except ImportError:
         print("WARNING: Could not check Matplotlib availability. Ensure it's installed for chart generation.")


    print(f"Agent will have access to {len(tools)} tools: {[tool.name for tool in tools]}")


    # 3. Create Agent Prompt (Same as before - ReAct prompt is generally suitable)
    try:
        prompt_template = hub.pull("hwchase17/react")
    except Exception as e:
        print(f"Error pulling prompt from LangChain Hub: {e}")
        raise


    # 4. Create the Agent (Same as before)
    try:
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt_template)
        print("Agent created successfully.")
    except Exception as e:
        print(f"Error creating agent: {e}")
        raise


    # 5. Create the Agent Executor (Same as before)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        handle_parsing_errors="Check your output and make sure it conforms!", # More direct error feedback
        max_iterations=20, # Increased slightly for potentially longer research tasks
        # early_stopping_method="generate",
    )
    print("Agent Executor created.")

    return agent_executor