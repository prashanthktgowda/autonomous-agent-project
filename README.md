# Autonomous AI Agent Project

## Overview

This project implements an advanced autonomous AI agent capable of understanding complex natural language instructions and executing tasks across diverse digital environments. Inspired by platforms requiring minimal user intervention, this agent leverages Large Language Models (LLMs) for reasoning and planning, integrated with a suite of tools for interacting with web browsers, the local file system (sandboxed), external APIs (stocks), data processing scripts, and the command line (restricted). The primary interface is a Streamlit web application featuring real-time streaming of the agent's thought process.

This project aims to demonstrate the core principles of building autonomous systems, including instruction understanding, task decomposition, tool use, safety considerations, and result generation, suitable for educational or experimental purposes.

**Developed for:** [Your Course Name/Assignment Purpose - Optional]
Workflow demo video link - (https://drive.google.com/file/d/1mpKe6iGCAEsTkF8HKpEHgB3XhxbEfV3K/view?usp=drive_link)

## Core Approach

The agent operates based on a **Reasoning and Acting (ReAct)** framework, orchestrated by the LangChain library. The core loop involves:

1.  **Instruction Parsing:** The user provides a natural language instruction (e.g., "Research X, analyze the data, and generate a charted report Y").
2.  **LLM Reasoning (Thought):** An LLM (configured via `agent/planner.py`, currently set for Google Gemini) analyzes the instruction and the descriptions of available tools. It formulates a plan or decides the next immediate action needed.
3.  **Tool Selection (Action):** Based on its thought process, the LLM selects the most appropriate tool from its toolkit (e.g., Web Search, Stock Data Fetcher, File Writer, PDF Chart Generator, Script Runner).
4.  **Input Formulation (Action Input):** The LLM generates the necessary input string required by the selected tool, adhering to the specific format defined in the tool's description.
5.  **Tool Execution:** The selected tool's underlying Python function is executed with the provided input. Tools interact with the external environment (web, files, APIs, terminal).
6.  **Result Acquisition (Observation):** The output (data, success/error message, confirmation request) from the executed tool is captured.
7.  **Cycle Continuation:** The observation is fed back to the LLM. Steps 2-6 repeat until the LLM determines it has enough information to provide a final answer or complete the task.
8.  **Confirmation Handling:** Specific tools (like file deletion) return special strings (`CONFIRM_DELETE|...`) that pause the agent loop and require explicit user confirmation via the UI or CLI before the action is finalized by separate helper functions.
9.  **Final Output:** The agent provides a final textual response summarizing the outcome or delivering the requested information. Generated files (reports, data) are saved in the `outputs` directory.

**Key Design Principles:**

*   **Modularity:** Tools are implemented as separate Python modules for clarity and maintainability.
*   **Tool Descriptions:** Precise tool descriptions are crucial for the LLM's ability to select and use tools correctly.
*   **Safety:** Filesystem and terminal interactions are sandboxed or restricted to minimize risk. Destructive actions like deletion require explicit user confirmation.
*   **Flexibility:** Configuration (LLM model, temperature) is adjustable via the Streamlit UI sidebar.
*   **User Experience:** The Streamlit UI provides real-time streaming feedback of the agent's actions.

## Features

*   **Natural Language Understanding:** Powered by configurable LLMs (Gemini, potentially others).
*   **Multi-Environment Interaction:**
    *   **Web:** Search (DuckDuckGo), Text Scraping (prioritizing content), HTML Table Extraction (Pandas-based).
    *   **Financial Data:** Fetch historical stock data (via `yfinance`).
    *   **File System (Sandboxed):** Read, Write (Overwrite), Append, List files/directories **strictly within** the `./outputs` directory.
    *   **File Deletion (Agent-Initiated):** Agent can *request* file deletion, requiring explicit user confirmation via the UI/CLI before execution.
    *   **Terminal (Restricted):** Execute a predefined list of safe commands (`ls`, `pwd`, `cat`, etc.) OR run specific Python scripts located in allowed project directories (`scripts/`, project root). **USE WITH EXTREME CAUTION.**
*   **Data Processing:**
    *   Basic CSV summary statistics calculation via an allowed Python script (`scripts/process_data.py`) executed through the terminal tool.
*   **Reporting:**
    *   Generate basic text-only PDF reports.
    *   Generate PDF reports including text and a **line chart** based on provided CSV data, with **user-specifiable X and Y columns**.
*   **Configuration:** Adjust LLM model and temperature via the Streamlit UI sidebar.
*   **User Interface:**
    *   Modern Streamlit web app.
    *   **Real-time streaming** of agent thoughts and actions.
    *   Dedicated file browser for the `outputs` directory with preview, download, and **manual delete (with confirmation)** capabilities.
    *   Handles agent-requested delete confirmations.
*   **Command-Line Interface:** Alternative `main.py` script for running the agent via terminal, including support for delete confirmations.

## Architecture

The project follows a modular structure:

*   **`app.py`**: Main Streamlit web application entry point. Handles UI, agent invocation (threaded), streaming callbacks, and UI-based file operations/confirmations.
*   **`main.py`**: Command-line interface entry point. Handles CLI arguments, agent invocation, and CLI-based delete confirmations.
*   **`agent/planner.py`**: Core agent initialization logic. Selects and configures the LLM, defines the list of available tools, pulls/configures the agent prompt (ReAct), and creates the LangChain `AgentExecutor`. Accepts configuration parameters (model, temperature).
*   **`tools/`**: Directory containing Python modules for each tool. Each module defines:
    *   The core Python function(s) performing the action (e.g., `get_stock_history`).
    *   The LangChain `Tool` object wrapping the function, including the crucial `name` and `description` for the LLM.
    *   Helper functions (e.g., path validation).
    *   Includes: `browser_tool.py`, `data_processing_tool.py`, `delete_file_tool.py`, `filesystem_tool.py`, `reporting_tool.py`, `stock_data_tool.py`, `terminal_tool.py`.
*   **`scripts/`**: Directory containing safe Python scripts allowed to be executed by the enhanced terminal tool (e.g., `process_data.py`).
*   **`outputs/`**: Designated sandboxed directory where all agent-generated files (reports, data) are saved. Filesystem tools cannot operate outside this directory.
*   **`.env` / `.env.example`**: Stores API keys (Google, HF, OpenAI, LangSmith). **`.env` is ignored by Git.**
*   **`requirements.txt`**: Lists all Python dependencies.
*   **`.gitignore`**: Specifies files/directories ignored by Git.
*   **`README.md`**: This documentation file.

## Tool Descriptions (Summary for Agent)

*(This section summarizes the tools the agent has access to, mirroring the descriptions used in the code)*

*   **`duckduckgo_search`**: Searches the web for information. Input: search query string. Output: Search results summary.
*   **`Web Browser Text Scraper`**: Navigates to a URL & scrapes TEXT (headlines/paragraphs). Input: `URL|Task Description`. Output: Cleaned text or ERROR. Use for articles/general text. **For TABLES, use 'Extract Tables from Webpage'.**
*   **`Extract Tables from Webpage`**: Navigates to URL, finds HTML tables, extracts best one as CSV. Input: URL string. Output: `Success:...CSV Data...` or `Error:...`. Use for structured data in tables. Requires pandas/lxml/html5lib.
*   **`Get Stock Historical Data`**: Fetches stock history (Date, O, H, L, C, V). Input: `TICKER|PERIOD` (e.g., `AAPL|1y`, `MRF.NS|6mo`). Periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max. Output: `Success:...CSV...` or `Error:...`. Data might be truncated.
*   **`Run Terminal Command or Safe Script`**: Executes allowed basic shell commands (`ls`, `pwd`, `cat`, `head`, `tail`, `grep`, `wc`) OR safe Python scripts (`python scripts/my_script.py [args]`). Input: full command string. Script path must be relative and within allowed project dirs. Prohibited commands (`rm`, `sudo`, `pip`, etc.) blocked. Output: JSON string `{"stdout": "...", "stderr": "...", "exit_code": 0}`. Check `exit_code` and `stderr`. **USE WITH EXTREME CAUTION.**
*   **`Read File Content`**: Reads text from a file inside `outputs`. Input: relative path (e.g., `data/report.txt`). No `..` or absolute paths. Output: File content or Error.
*   **`Write Text to File`**: Writes/Overwrites text to a file inside `outputs`. Input: `relative/path.txt|content`. Use `\\n` for newlines. Creates dirs. **OVERWRITES existing files.** Output: Success message or Error.
*   **`Append Text to File`**: Adds text to the END of a file inside `outputs` (creates if needed). Input: `relative/path.txt|content`. Use `\\n` for newlines. Doesn't overwrite. Output: Success message or Error.
*   **`List Directory Contents`**: Lists files/subdirs inside a directory within `outputs`. Input: relative path (e.g., `.`, `subdir`). No `..` or absolute paths. Output: List `outputs/... \n item (TYPE)\n...` or Error.
*   **`Request File Deletion Confirmation`**: Use ONLY when user explicitly asks to delete a file in `outputs`. Input: relative path (e.g., `report.txt`). Validates path/file. Returns `CONFIRM_DELETE|filepath` for UI/CLI confirmation, or Error message. **Does NOT delete directly.** Tool output is final step for this action.
*   **`Summarize CSV Data Statistics`**: Calculates basic stats (count, mean, std, min, max, quartiles) for NUMERIC columns in CSV data. Input: Multi-line CSV string (with header). Remove `Success:/CSV Data:` prefixes. Output: Stats table string or Error.
*   **`Generate Basic PDF Report (Text Only)`**: Generates PDF with text only. Input: `filename.pdf|Title|Content`. Paragraphs separated by `\\n\\n`. Saves to `outputs`.
*   **`Generate PDF Report with Line Chart`**: Generates PDF with text & line chart from CSV using specified columns. Input: `filename.pdf|RptTitle|RptText|ChartTitle|XColName|YColName|CSV_DATA`. Specify exact X/Y column headers from CSV. Remove prefixes from CSV_DATA. Requires Matplotlib/Pandas. Saves to `outputs`.

## Setup

1.  **Clone Repository:**
    ```bash
    git clone <your-repo-url>
    cd autonomous-agent-project
    ```
2.  **Create Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate    # Windows
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Install Playwright Browsers:**
    ```bash
    playwright install
    ```
5.  **Configure API Keys:**
    *   Rename `.env.example` to `.env`.
    *   Open `.env` and add your **Google API Key** (for Gemini).
    *   Add other keys (Hugging Face, OpenAI, LangSmith) if you modify `agent/planner.py` to use those services or enable tracing.
    *   **Ensure `.env` is listed in `.gitignore`!**
6.  **Create Directories (if needed):**
    *   The scripts attempt to create `outputs/` and `scripts/` automatically, but ensure they exist if you encounter issues.
    *   Place the example `scripts/process_data.py` (or your own safe scripts) inside the `scripts/` directory.

## Usage

### Streamlit Web UI (Recommended)

1.  Activate your virtual environment (`source venv/bin/activate`).
2.  Run the Streamlit app from the project root:
    ```bash
    streamlit run app.py
    ```
3.  Open the provided URL in your web browser.
4.  Configure model parameters in the sidebar (optional).
5.  Enter your instruction in the main text area.
6.  Click "▶️ Run Agent".
7.  Observe the agent's actions in the "Agent Execution Stream" section.
8.  View the final result and check the "Output Files Browser" for generated files (use the refresh button if needed).
9.  Handle any agent-requested delete confirmations that appear in the UI.

### Command Line Interface

1.  Activate your virtual environment.
2.  Run from the project root:
    ```bash
    python main.py "Your instruction here" [options]
    ```
3.  **Options:**
    *   `-v` or `--verbose`: Show detailed agent execution logs in the terminal.
    *   `-m <model_name>` or `--model <model_name>`: Specify LLM model (defaults to value in `planner.py`).
    *   `-t <temperature>` or `--temperature <temperature>`: Specify LLM temperature.
4.  Respond to any delete confirmation prompts directly in the terminal (`yes`/`no`).
5.  Check the `outputs/` directory for generated files.

## Example Prompts

*   **Basic File I/O:**
    *   `"Write a short story about an AI agent exploring the web and save it to 'story.txt'"`
    *   `"Read the content of 'story.txt'"`
    *   `"List the files currently in the outputs directory"`
    *   `"Append the line 'The agent learned much.' to the end of 'story.txt'"`
    *   `"Please delete the file 'story.txt'"` (Will trigger confirmation)
*   **Web Research & Reporting:**
    *   `"Search for the latest news about autonomous agents. Summarize the top 3 findings in a text file named 'agent_news.txt'"`
    *   `"Find the main contact email address listed on the LangChain documentation website's main page."`
*   **Data & Charting:**
    *   `"Fetch the stock closing prices for TSLA for the last 6 months. Then generate a PDF report named 'tsla_report.pdf' containing a brief summary and a line chart of the closing prices over time titled 'TSLA Closing Price (6mo)'. Use the Date column for the x-axis and Close for the y-axis."`
    *   `"Go to the Wikipedia page for 'List of largest technology companies by revenue'. Extract the main table as CSV data. Then calculate summary statistics for the numeric columns in that data."` (Might succeed or fail depending on table complexity)
*   **Script Execution:**
    *   `"Create a csv file named 'sample_input.csv' with columns 'Category,Value' and rows 'A,10', 'B,25', 'A,15'. Then run the python script 'scripts/process_data.py' using 'outputs/sample_input.csv' as input."`

## Known Limitations & Future Work

*   **Terminal Security:** **HIGH RISK.** The terminal tool has improved safety checks but executing *any* command via LLM poses risks. The allowlist is restrictive, and script execution is limited to specific directories. **Use extremely cautiously, ideally in a sandboxed environment (e.g., Docker).**
*   **Web Scraping Brittleness:** Both text and table scraping depend heavily on website structure and can break easily if sites change. `pandas.read_html` struggles with complex/non-standard tables. JavaScript-heavy sites might not render fully for scraping without more advanced Playwright techniques.
*   **Data Extraction Accuracy:** The agent might misinterpret scraped text or poorly structured table data. The quality of extracted CSV from tables depends on the heuristic used to select the "best" table.
*   **LLM Reliability:** Performance (planning, tool use, error handling, result quality) varies significantly based on the chosen LLM. Complex multi-step tasks might require more powerful models or sophisticated prompting/agent types (e.g., Plan-and-Execute). Hallucinations or incorrect tool usage can occur.
*   **Context Window:** Very long web pages, extensive tool logs, or complex instructions might exceed the LLM's context window, leading to errors or forgotten information. Summarization tools or vector memory could mitigate this.
*   **Error Recovery:** While `handle_parsing_errors` is enabled, the agent's ability to recover from tool errors or unexpected situations is limited. More advanced self-correction logic could be added.
*   **Concurrency (UI):** The Streamlit app runs the agent in a single background thread. Running multiple complex agent tasks simultaneously is not supported in this basic setup.

**Potential Future Enhancements:**

*   Implement Plan-and-Execute or Function Calling agents.
*   Add memory (vector stores, summarization buffer).
*   Integrate more specific APIs (Weather, News, Wikipedia).
*   Develop more advanced, targeted scraping tools.
*   Implement robust sandboxing for code/terminal execution.
*   Add user controls for intermediate steps in the UI.
*   Build a more comprehensive evaluation suite.

---
