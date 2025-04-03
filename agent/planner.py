# autonomous-agent-project/agent/planner.py

import os
from dotenv import load_dotenv
# from langchain_community.llms import HuggingFaceHub # REMOVE or COMMENT OUT
from langchain_google_genai import ChatGoogleGenerativeAI # <--- IMPORT THIS
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

# Import your tools (keep these)
from tools.browser_tool import browser_tool
from tools.terminal_tool import terminal_tool
from tools.filesystem_tool import read_file_tool, write_file_tool, list_directory_tool
from tools.reporting_tool import generate_pdf_report_tool
# from langchain_community.tools import DuckDuckGoSearchRun # Optional: Add if using search

# Load environment variables (like GOOGLE_API_KEY)
load_dotenv()

def initialize_agent(verbose: bool = False):
    """
    Initializes the LangChain agent with the defined tools and Google AI Studio (Gemini) LLM.
    """
    print("Initializing Google AI Studio (Gemini) LLM and Agent...")

    # 1. Choose LLM from Google AI Studio (Gemini)
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("Google API key not found in .env file. Please set GOOGLE_API_KEY.")

    # Select a Gemini model. "gemini-1.5-flash-latest" is often fast and capable for free tier.
    # Other options: "gemini-pro", "gemini-1.5-pro-latest" (check Google AI Studio for available models)
    model_name = "gemini-1.5-flash-latest"
    # model_name = "gemini-pro" # Solid alternative

    print(f"Using Google Gemini model: {model_name}")

    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=google_api_key,
            temperature=0.1, # Low temperature for more deterministic planning
            # convert_system_message_to_human=True # May be needed for some older models/prompts if system messages cause issues
        )
        # Test the connection briefly (optional but recommended)
        # llm.invoke("test")
        print("Successfully initialized Google Gemini LLM.")
    except Exception as e:
         print(f"Error initializing Google Gemini LLM: {e}")
         print("Please ensure your GOOGLE_API_KEY is correct and you have enabled the API in your Google Cloud project if required.")
         raise # Re-raise the exception to stop execution


    # 2. Define Tools (SAME AS BEFORE)
    # search_tool = DuckDuckGoSearchRun() # Optional Search
    tools = [
        # search_tool, # Add search first if needed
        browser_tool,
        terminal_tool,
        read_file_tool,
        write_file_tool,
        list_directory_tool,
        generate_pdf_report_tool,
    ]
    print(f"Agent will have access to {len(tools)} tools: {[tool.name for tool in tools]}")


    # 3. Create Agent Prompt (SAME AS BEFORE)
    # Use a standard ReAct prompt suitable for tool use.
    try:
        # This prompt generally works well with Gemini models too
        prompt_template = hub.pull("hwchase17/react")
    except Exception as e:
        print(f"Error pulling prompt from LangChain Hub: {e}")
        raise


    # 4. Create the Agent (SAME AS BEFORE)
    try:
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt_template)
        print("Agent created successfully.")
    except Exception as e:
        print(f"Error creating agent: {e}")
        raise


    # 5. Create the Agent Executor (SAME AS BEFORE)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        handle_parsing_errors=True, # Helps manage LLM formatting mistakes
        max_iterations=15,
        # early_stopping_method="generate",
    )
    print("Agent Executor created.")

    return agent_executor