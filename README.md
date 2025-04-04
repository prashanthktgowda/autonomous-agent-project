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

```mermaid
graph LR
    subgraph User Interface
        direction LR
        CLI[main.py CLI]
        WEB[app.py Streamlit UI]
    end

    subgraph Agent Core
        direction TB
        A[LLM (e.g., Gemini)] -- Reasoning --> B(Agent Planner / ReAct Loop);
        B -- Chooses Tool --> C{Tool Executor};
    end

    subgraph Tools [Environment Interaction Layer]
        direction TB
        T_Search[DuckDuckGo Search]
        T_Browse_Text[Web Text Scraper]
        T_Browse_Table[Web Table Extractor]
        T_Stock[Stock Data (yfinance)]
        T_Terminal[Sandboxed Terminal/Script]
        T_FS_Read[Filesystem Read]
        T_FS_Write[Filesystem Write/Overwrite]
        T_FS_Append[Filesystem Append]
        T_FS_List[Filesystem List]
        T_FS_DeleteReq[Filesystem Delete Request]
        T_Data[Data Stats (Pandas)]
        T_PDF_Text[PDF Report (Text)]
        T_PDF_AutoChart[PDF Report (Auto-Chart)]
    end

    subgraph Execution Environment
        direction TB
        Net[Internet]
        LocalFS[Local Filesystem (./outputs, ./scripts)]
        PyEnv[Python Environment]
    end

    CLI --> B;
    WEB --> B;
    C --> T_Search;
    C --> T_Browse_Text;
    C --> T_Browse_Table;
    C --> T_Stock;
    C --> T_Terminal;
    C --> T_FS_Read;
    C --> T_FS_Write;
    C --> T_FS_Append;
    C --> T_FS_List;
    C --> T_FS_DeleteReq;
    C --> T_Data;
    C --> T_PDF_Text;
    C --> T_PDF_AutoChart;

    T_Search --> Net;
    T_Browse_Text --> Net;
    T_Browse_Table --> Net;
    T_Stock --> Net;
    T_Terminal --> PyEnv;
    T_FS_Read --> LocalFS;
    T_FS_Write --> LocalFS;
    T_FS_Append --> LocalFS;
    T_FS_List --> LocalFS;
    T_FS_DeleteReq --> B; # Returns confirmation string
    T_Data --> PyEnv; # Requires Pandas
    T_PDF_Text --> LocalFS; # Requires ReportLab
    T_PDF_AutoChart --> LocalFS; # Requires ReportLab
    T_PDF_AutoChart -- Uses --> PyEnv; # Requires Matplotlib/Pandas

    WEB -- Displays File List --> LocalFS;
    WEB -- Triggers Manual Delete --> LocalFS; # Bypasses Agent Core

    style Agent Core fill:#e3f2fd,stroke:#333,stroke-width:2px
    style Tools fill:#e8f5e9,stroke:#333,stroke-width:1px
    style User Interface fill:#fff3e0,stroke:#333,stroke-width:1px
    style Execution Environment fill:#fce4ec,stroke:#333,stroke-width:1px