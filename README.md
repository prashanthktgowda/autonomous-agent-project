# Autonomous AI Agent Project (using Google Gemini)

![Project Banner](assets/project_banner.png) <!-- Replace with an actual banner image -->

## Overview

This project implements an autonomous AI agent capable of understanding natural language instructions, executing tasks across different environments (web search, browser, terminal, file system), performing analysis, and delivering results including professional reports with visualizations. It uses Google's Gemini models via the Google AI Studio API as its core reasoning engine. The agent operates autonomously after receiving the initial instruction, minimizing user effort while maximizing utility.

> **Assignment Context:** This project was developed to fulfill the requirements of the Autonomous AI Agent Assessment.

---

## Features

### 🌟 Key Capabilities
- **Natural Language Understanding:** Parses user instructions to determine the goal using the Google Gemini LLM.
- **Task Planning:** Breaks down complex tasks into sequential steps using the LLM and the ReAct agent framework within LangChain.
- **Multi-Environment Execution:**
  - **Web Search:** Uses DuckDuckGo to find relevant information and URLs online.
  - **Browser:** Navigates websites using Playwright to extract and scrape text content.
  - **Terminal:** Executes **strictly limited** shell commands (with security warnings and basic filtering).
  - **File System:** Reads, writes, and lists files **strictly within** a designated `outputs` directory for safety.
- **Reporting & Visualization:**
  - Generates organized text files.
  - Creates professional PDF reports containing text-based analysis.
  - Generates PDF reports with **bar chart visualizations** using Matplotlib and ReportLab.
- **Autonomous Operation:** Requires no further user input after the initial command is given.

---

## Architecture

![Architecture Diagram](assets/architecture_diagram.png) <!-- Replace with an actual architecture diagram -->

The system is built using Python and the LangChain framework, interacting with the Google AI Studio API.

### Key Components
- **`main.py`**: Entry point for the application. Handles command-line arguments, initializes the agent, and manages top-level error reporting.
- **`agent/planner.py`**: Defines the agent's reasoning loop, tool integration, and LLM connection.
- **`tools/`**: Contains modules for environment interactions as LangChain `Tool` objects.
- **`outputs/`**: Designated safe directory for generated files (text, PDF).
- **`requirements.txt`**: Lists all necessary Python dependencies.
- **`.env`**: Stores the necessary API key (`GOOGLE_API_KEY`).

---

## Setup

### 1️⃣ Clone the Repository
```bash
git clone <your-repo-url>
cd autonomous-agent-project
```

### 2️⃣ Create and Activate a Virtual Environment
```bash
python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Install Playwright Browser Binaries
```bash
playwright install
```

### 5️⃣ Set Up Google AI Studio API Key
1. Go to Google AI Studio and sign in.
2. Click "Get API key" and create a new API key if needed.
3. Create a `.env` file in the project root and add your API key:
   ```plaintext
   GOOGLE_API_KEY="YOUR_GOOGLE_AI_STUDIO_API_KEY_HERE"
   ```

> **Note:** Ensure `.env` is listed in `.gitignore` to prevent accidentally committing your secret key.

---

## Usage

### Basic Command
Run the agent with a natural language instruction:
```bash
python main.py "Your natural language instruction here"
```

### Verbose Mode (Recommended for Debugging)
```bash
python main.py -v "Your natural language instruction here"
```

### Example Commands
#### Basic Level
```bash
python main.py -v "Find 5 recent headlines about Artificial Intelligence and save them to 'ai_headlines.txt'."
```

#### Intermediate Level
```bash
python main.py -v "Summarize reviews of the 'Google Pixel 8' and save the analysis to 'pixel8_review_summary.txt'."
```

#### Advanced Level
```bash
python main.py -v "Analyze global solar PV capacity trends and generate a PDF report with a bar chart."
```

---

## Verification Stages

### Conceptual Flow Diagram
```mermaid
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
```

---

## Video Demonstration

[![Watch the Video](assets/video_thumbnail.png)](https://example.com/video-demo) <!-- Replace with actual video link -->

---

## Known Limitations & Future Work

### Limitations
- **Terminal Security:** The terminal tool's safety filter is basic. Use in a sandboxed environment.
- **Browser Reliability:** Web scraping is fragile and may fail on dynamic or anti-scraping websites.
- **LLM Reliability:** The LLM may misinterpret instructions or hallucinate information.
- **Error Handling:** Complex errors might cause the agent to fail or get stuck.

### Future Work
- Improve terminal tool security.
- Add support for more visualization types.
- Enhance error recovery mechanisms.

---

## Dependencies

- `langchain`
- `langchain-community`
- `langchain-google-genai`
- `google-generativeai`
- `python-dotenv`
- `playwright`
- `beautifulsoup4`
- `lxml`
- `reportlab`
- `matplotlib`
- `duckduckgo-search`

---

## Contact

For questions or feedback, please contact [Your Name](mailto:your-email@example.com).

---

## Assets

- **Project Banner:** `assets/project_banner.png`
- **Architecture Diagram:** `assets/architecture_diagram.png`
- **Video Thumbnail:** `assets/video_thumbnail.png`
- 
