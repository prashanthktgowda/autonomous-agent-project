# Autonomous AI Agent Project (Enhanced)

## Overview

This project implements an advanced autonomous AI agent capable of understanding complex natural language instructions and executing tasks across multiple environments: web browsing (text and table scraping), stock data retrieval, terminal command execution (sandboxed), file system operations (read, write, append, list, delete with confirmation), data analysis, and professional PDF report generation (including text, automated line/bar charts).

The agent operates autonomously after receiving the initial instruction, leveraging a Large Language Model (LLM) – configured for Google Gemini by default – for reasoning and planning, and a suite of specialized tools for interacting with its environment. The project includes both a command-line interface (`main.py`) and a web interface (`app.py` using Streamlit) with real-time streaming output.

This project aims to simulate capabilities similar to advanced AI assistant platforms, providing a framework for complex task automation developed as part of a college assignment.

## Features

*   **Natural Language Understanding:** Parses user instructions using a powerful LLM (e.g., Google Gemini).
*   **Multi-Step Planning:** Breaks down complex tasks into sequential steps using the ReAct agent framework within LangChain.
*   **Multi-Environment Tool Use:**
    *   **Web Search:** Finds relevant information online (using DuckDuckGo).
    *   **Web Browsing (Text):** Navigates websites and extracts cleaned textual content, prioritizing headlines and paragraphs.
    *   **Web Browsing (Tables):** Attempts to find, parse, and extract data from HTML tables on webpages into CSV format (requires `pandas`, `lxml`, `html5lib`).
    *   **Stock Data:** Fetches historical stock market data for specified tickers and periods using `yfinance` (requires `yfinance`, `pandas`).
    *   **Terminal:** Executes a limited set of explicitly allowed, safe shell commands (OS-aware) OR designated Python scripts within the project structure (with path validation). Returns structured JSON output (stdout, stderr, exit code). **USE WITH EXTREME CAUTION.**
    *   **File System:** Reads, writes (overwrite), appends, lists files, and requests deletion confirmation, **strictly sandboxed** within the `./outputs` directory. Handles `\n` escapes in write/append.
    *   **Data Processing:** Performs basic summary statistics (`describe`) on provided CSV data using Pandas (requires `pandas`).
    *   **Reporting (Text):** Generates simple, text-only PDF reports using ReportLab.
    *   **Reporting (Auto-Chart):** Generates PDF reports including text and **attempts to automatically create** a relevant line or bar chart if suitable CSV data is provided, inferring columns and chart type (requires `reportlab`, `pandas`, `matplotlib`). Falls back to text-only if charting fails or libraries are missing.
*   **Agent-Initiated Deletion with Confirmation:** Agent can request file deletion via a specific tool, which requires explicit user confirmation via the UI or CLI before execution.
*   **Streaming UI:** The Streamlit web interface (`app.py`) shows the agent's thought process and tool usage in near real-time using LangChain Callbacks and threading.
*   **Configurable Model:** Allows selection of different LLM models (if configured in `planner.py`) and adjustment of parameters like temperature via the Streamlit sidebar or CLI arguments.

## Architecture

The system is built using Python, leveraging the LangChain framework for agent logic and tool integration, and Streamlit for the web UI.

**Conceptual Flow:**

```mermaid
graph TD
    subgraph User Interface
        UI_Input[User Instruction (CLI or Web UI)]
    end

    subgraph Agent_System [Agent System]
        A_Planner[Agent Planner (ReAct Loop + LLM Reasoning)]
        A_Tools[Tool Executor]
    end

    subgraph Available_Tools [Available Tools Layer]
        T_Search(Web Search)
        T_Browse(Web Scraping: Text/Tables)
        T_Stock(Stock Data)
        T_Terminal(Terminal/Script Exec)
        T_FS(Filesystem Ops: RWLA, Del Req)
        T_Data(Data Analysis)
        T_Report(PDF Reporting: Text/Auto-Chart)
        T_Other(...)
    end

    subgraph Environment
        Env_Net[Internet]
        Env_FS[Local Filesystem (outputs/, scripts/)]
        Env_Py[Python Environment (Libs)]
    end

    UI_Input --> A_Planner;
    A_Planner -- Selects Tool & Input --> A_Tools;
    A_Tools -- Executes --> Available_Tools;

    Available_Tools -- Interact --> Environment;
    Environment -- Result/Data --> Available_Tools;
    Available_Tools -- Observation --> A_Planner;

    A_Planner -- Final Answer --> User Interface;

    style Agent_System fill:#e3f2fd,stroke:#333,stroke-width:2px
    style Available_Tools fill:#e8f5e9,stroke:#333,stroke-width:1px
    style User_Interface fill:#fff3e0,stroke:#333,stroke-width:1px
    style Environment fill:#fce4ec,stroke:#333,stroke-width:1px
## Demo Video

<video controls>
    <source src="/home/prashanthktgowda/academics_project/autonomus-AI/autonomous-agent-project/demo video.webm" type="video/mp4">
    Your browser does not support the video tag.
</video>