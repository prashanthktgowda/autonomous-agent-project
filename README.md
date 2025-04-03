# Autonomous AI Agent

## Overview

This project implements an autonomous AI agent capable of understanding natural language instructions, executing tasks across different environments (web search, browser, terminal, file system), performing analysis, and delivering results including professional reports with visualizations. It uses Google's Gemini models via the Google AI Studio API as its core reasoning engine. The agent operates autonomously after receiving the initial instruction, minimizing user effort while maximizing utility, as outlined in the assignment brief.

This project was developed to fulfill the requirements of the Autonomous AI Agent Assessment.

## Features

*   **Natural Language Understanding:** Parses user instructions to determine the goal using the Google Gemini LLM.
*   **Task Planning:** Breaks down complex tasks into sequential steps using the LLM and the ReAct agent framework within LangChain.
*   **Multi-Environment Execution:**
    *   **Web Search:** Uses DuckDuckGo to find relevant information and URLs online.
    *   **Browser:** Navigates websites using Playwright to extract and scrape text content, attempting to prioritize relevant sections.
    *   **Terminal:** Executes **strictly limited** shell commands (with security warnings and basic filtering).
    *   **File System:** Reads, writes, and lists files **strictly within** a designated `outputs` directory for safety, correctly handling multi-line text formatting.
*   **Reporting & Visualization:**
    *   Generates organized text files.
    *   Creates professional PDF reports containing text-based analysis.
    *   Generates PDF reports including both textual analysis and **bar chart visualizations** based on provided data (using Matplotlib and ReportLab).
*   **Autonomous Operation:** Requires no further user input after the initial command is given.

## Architecture

The system is built using Python and the LangChain framework, interacting with the Google AI Studio API.

*   **`main.py`**: Entry point for the application. Handles command-line arguments (`argparse`), loads environment variables (`.env`), initializes the agent planner, executes the agent reasoning loop, and manages top-level error reporting.
*   **`agent/planner.py`**: Initializes the LLM connection to **Google AI Studio** (`ChatGoogleGenerativeAI`), defines the list of available tools (Search, Browser, Terminal, Filesystem, Basic PDF, Charting PDF), loads the agent prompt (ReAct prompt from `langchain.hub`), creates the agent logic (`create_react_agent`), and wraps it in an `AgentExecutor` which runs the main reasoning loop.
*   **`tools/`**: Contains Python modules wrapping environment interactions as LangChain `Tool` objects. Each tool has a specific function (`func`) and a detailed description (`description`) that the LLM uses to decide *when* and *how* to use the tool. Input formats are specified clearly in the descriptions.
    *   `browser_tool.py`: Web navigation and scraping via Playwright.
    *   `terminal_tool.py`: Shell command execution (with **critical security warnings** and basic allowlist).
    *   `filesystem_tool.py`: File I/O operations (**strictly sandboxed** to the `./outputs` directory, correctly handles newlines).
    *   `reporting_tool.py`: Contains functions and tools for generating both text-only PDFs and PDFs with Matplotlib bar charts via ReportLab. Includes robust input validation for the charting tool.
*   **Search Tool Integration:** Uses `langchain_community.tools.DuckDuckGoSearchRun` integrated directly in `agent/planner.py`.
*   **`outputs/`**: **Designated safe directory** where all generated files (text, PDF) and reports are saved. Filesystem tools are restricted to operate only within this directory.
*   **`requirements.txt`**: Lists all necessary Python dependencies.
*   **`.env`**: Stores the necessary API key (`GOOGLE_API_KEY`). **DO NOT COMMIT THIS FILE.**
*   **`.gitignore`**: Specifies files and directories (like `.env`, `venv`, `__pycache__`) to be ignored by Git.
*   **`README.md`**: This file - project documentation, setup, and usage instructions.

### Verification Stages Diagram (Conceptual Flow)

mermaid
graph LR
    A[User Input] --> B{Agent Core (Gemini LLM + ReAct Planner)};
    B -- Thought --> C{Tool Selection};
    C -- Action Input --> D[DuckDuckGo Search];
    C -- Action Input --> E[Web Browser Scraper];
    C -- Action Input --> F[Terminal Executor];
    C -- Action Input --> G[Filesystem Tools (Read/Write/List)];
    C -- Action Input --> H[Basic PDF Tool];
    C -- Action Input --> I[Charting PDF Tool];
    D -- Observation --> B;
    E -- Observation --> B;
    F -- Observation --> B;
    G -- Observation --> B;
    H -- Observation --> B;
    I -- Observation --> B;
    B -- Final Answer --> J[Output to Console / File in ./outputs];

Setup

Clone the repository:

git clone <your-repo-url>
cd autonomous-agent-project
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

Create and activate a Python virtual environment:

python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows (Command Prompt/PowerShell):
# venv\Scripts\activate
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

Install dependencies:

pip install -r requirements.txt
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

Install Playwright browser binaries: (Required for the browser tool)

playwright install
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

Set up Google AI Studio API Key:

Go to Google AI Studio and sign in.

Click "Get API key" and create a new API key if needed.

Create a file named .env in the project root directory (autonomous-agent-project/.env).

Add your API key to the .env file in the following format:

GOOGLE_API_KEY="YOUR_GOOGLE_AI_STUDIO_API_KEY_HERE"
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Env
IGNORE_WHEN_COPYING_END

IMPORTANT: Ensure .env is listed in your .gitignore file to prevent accidentally committing your secret key.

Usage

Run the agent from your terminal within the activated virtual environment. Provide the task instruction as a command-line argument enclosed in quotes.

Basic Command:

python main.py "Your natural language instruction here"
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

Verbose Mode (Recommended for Debugging):
Use the -v flag to see the agent's step-by-step thought process, actions, and tool observations.

python main.py -v "Your natural language instruction here"
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

Examples (Based on Assignment Test Cases):

Basic Level:

python main.py -v "Find 5 recent headlines about Artificial Intelligence from a major news source like Reuters or Associated Press. Format these headlines as a **numbered list**, with each headline on a new line. Save this formatted list into a text file named 'ai_headlines.txt' in the outputs directory."
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

(Expected Output: outputs/ai_headlines.txt with a numbered list of headlines)

Intermediate Level:

python main.py -v "First, use the search tool to find 2-3 web links for recent text reviews of the 'Google Pixel 8' smartphone. Second, use the browser tool to visit each link and scrape the main review text. Third, analyze the combined text from the reviews to identify the key advantages mentioned (Pros) and the key disadvantages mentioned (Cons). Fourth, create the text content for the output file. This text MUST be clearly organized using the following headings on separate lines, followed by bullet points or numbered lists for the items: 'Pros:', 'Cons:', and 'Overall Summary:'. Write a brief overall summary based on the pros and cons. Finally, use the 'Write Text to File' tool to save this organized text content into a file named 'pixel8_review_summary.txt' inside the outputs directory."
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

(Expected Output: outputs/pixel8_review_summary.txt with organized Pros, Cons, and Summary)

Advanced Level:

python main.py -v "Execute the following multi-step plan for renewable energy analysis:\n1.  **Research:** Use the search tool to find recent data (ideally for 2021, 2022, 2023) on global installed solar PV capacity (in GW or MW) from reputable sources (IEA, IRENA, etc.).\n2.  **Data Extraction & Analysis (Internal Thought):** Review the search results and scraped text. Identify the numerical capacity figure for three distinct recent years (e.g., 2021, 2022, 2023). Based *only* on this extracted data, formulate a brief analysis (2-3 paragraphs) summarizing the growth trend. *Do not try to call a tool for this internal analysis.*\n3.  **Chart Data Preparation (Internal Thought):** Format the extracted data needed for the chart. Prepare a comma-separated string for the years found (e.g., '2021,2022,2023') for the Labels. Prepare another comma-separated string containing **only the corresponding numerical capacity figures** (e.g., '1000,1200,1600' if using GW) for the Values. Ensure labels and values match in count.\n4.  **Final Output Generation:** **Once you have formulated the analysis text AND the formatted Labels/Values strings in your thought process**, your *only* next action MUST be to call the **'Generate PDF Report with Bar Chart' tool**. Provide ALL 6 required inputs formatted correctly as a single string separated by pipes '|':\n    'solar_capacity_analysis.pdf|Global Solar PV Capacity Trend Analysis|{Your analysis text from step 3}|Installed Capacity (MW or GW) by Year|{Your prepared Labels string from step 4}|{Your prepared Values string from step 4}'."
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

(Expected Output: outputs/solar_capacity_analysis.pdf containing the analysis text AND a bar chart visualization)

Check the outputs/ directory for the generated files after each run.

Test Cases & Verification Stages Fulfillment

This project is designed to meet the requirements of the assignment's verification stages:

Stage 1 (Individual Environment Execution): Achieved through the distinct tools provided to the agent. Simple commands can test individual tools (e.g., writing a file, listing directory, attempting to browse a specific URL).

Stage 2 (Dual Environment Integration): Demonstrated by tasks requiring sequential tool use, such as searching for information (duckduckgo_search) and then scraping a resulting URL (Web Browser Scraper), or scraping information (Web Browser Scraper) and then saving it (Write Text to File). The Intermediate test case command explicitly tests this.

Stage 3 (Full System Integration): Demonstrated by the Advanced test case, which requires searching, potentially browsing, internal analysis and data formatting by the LLM, and finally generating a complex output (PDF with chart) using the appropriate tool and structured data. Error handling across transitions is managed by the agent framework and tool feedback.

The sample test cases provided in the assignment brief can be executed using the example commands above.

Video Demo

(As required by the assignment submission requirements)

[Link to Video Demonstration - Replace this with your actual video link]

Known Limitations & Future Work

Terminal Security: CRITICAL RISK. The terminal tool's safety filter is basic. Executing LLM-generated commands is inherently dangerous. Use with extreme caution, ideally in a sandboxed environment (like Docker). Never run with elevated privileges.

Browser Reliability: Web scraping is fragile. Website structure changes can break the scraping logic. Dynamic content loaded via JavaScript might be missed. Some sites employ anti-scraping measures that could block the browser tool. Timeout errors may occur on slow sites.

LLM Reliability & Data Extraction: The accuracy of the analysis and the success of data extraction (especially numerical data for charts) heavily depend on the chosen LLM's capabilities (Gemini Flash used here). The LLM might misinterpret instructions, fail to extract data accurately, hallucinate information, or struggle with complex formatting requirements, especially from varied web content.

Error Handling: While the agent can handle some tool errors (e.g., retrying search after browser failure), complex or unexpected errors might cause the agent to fail or get stuck. More sophisticated error recovery could be implemented.

Context Window: Very long web pages or extremely complex multi-step instructions might exceed the LLM's context window limit, leading to errors or forgotten information.

API Costs/Limits: Google AI Studio API has free tier limits. Extensive use might require upgrading or hitting usage quotas.

Chart Complexity: The current implementation only supports simple bar charts. More visualization types would require additional code.

Dependencies

langchain

langchain-community

langchain-google-genai

google-generativeai

python-dotenv

playwright

beautifulsoup4

lxml

reportlab

matplotlib

duckduckgo-search

IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
IGNORE_WHEN_COPYING_END
