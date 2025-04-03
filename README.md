# Autonomous AI Agent Project (using Hugging Face Hub)

## Overview

This project implements an autonomous AI agent capable of understanding natural language instructions, executing tasks across different environments (web browser, terminal, file system), and delivering results. It uses Large Language Models (LLMs) hosted on the **Hugging Face Hub Inference API** as its core reasoning engine. The agent operates autonomously after receiving the initial instruction.

This was developed as a college assignment based on the provided assessment brief.

## Features

*   **Natural Language Understanding:** Parses user instructions to determine the goal using an LLM from Hugging Face Hub.
*   **Task Planning:** Breaks down complex tasks into sequential steps using the LLM and the ReAct agent framework within LangChain.
*   **Multi-Environment Execution:**
    *   **Browser:** Navigates websites and extracts text content (using Playwright).
    *   **Terminal:** Executes **strictly limited** shell commands (with security warnings and basic filtering).
    *   **File System:** Reads, writes, and lists files **strictly within** a designated `outputs` directory for safety.
*   **Reporting:** Can generate text files and basic PDF reports.
*   **Autonomous Operation:** Requires no further user input after the initial command.

## Architecture

The system is built using Python and the LangChain framework.

*   **`main.py`**: Entry point, handles user input (`argparse`), loads environment variables (`.env`), initializes the agent, runs the main execution loop, and handles top-level errors.
*   **`agent/planner.py`**: Initializes the LLM connection to **Hugging Face Hub** (`HuggingFaceHub` class), defines the list of available tools, loads the agent prompt (e.g., ReAct prompt from `langchain.hub`), creates the agent logic (`create_react_agent`), and wraps it in an `AgentExecutor` which runs the main reasoning loop.
*   **`tools/`**: Contains modules wrapping environment interactions as LangChain `Tool` objects. Each tool has a specific Python function (`func`) and a descriptive string (`description`) that the LLM uses to decide *when* and *how* to use the tool. Input formats are specified in the descriptions.
    *   `browser_tool.py`: Web navigation and scraping via Playwright.
    *   `terminal_tool.py`: Shell command execution (with **critical security warnings** and basic allowlist).
    *   `filesystem_tool.py`: File I/O operations (**strictly sandboxed** to the `./outputs` directory).
    *   `reporting_tool.py`: Report generation (TXT via filesystem tool, basic PDF via ReportLab).
*   **`outputs/`**: **Designated directory** where all generated files and reports are saved. Filesystem tools are restricted to operate only within this directory.
*   **`requirements.txt`**: Lists Python dependencies.
*   **`.env`**: Stores API keys (specifically `HUGGINGFACEHUB_API_TOKEN`). **DO NOT COMMIT THIS FILE.**
*   **`.gitignore`**: Specifies files and directories to be ignored by Git.
*   **`README.md`**: This file - documentation.

### Verification Stages Diagram (Conceptual)

```mermaid
graph LR
    A[User Input] --> B{Agent Core (HF LLM + ReAct Planner)};
    B -- Thought --> C{Tool Selection};
    C -- Action Input --> D[Browser Tool];
    C -- Action Input --> E[Terminal Tool];
    C -- Action Input --> F[File System Tool];
    C -- Action Input --> G[Reporting Tool];
    D -- Observation --> B;
    E -- Observation --> B;
    F -- Observation --> B;
    G -- Observation --> B;
    B -- Final Answer --> H[Output to Console / File in ./outputs];