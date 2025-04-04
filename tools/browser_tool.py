# autonomous-agent-project/tools/browser_tool.py (Enhanced with Table Extraction)

import time
from langchain.tools import Tool
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup, Comment # Import Comment
import traceback # For detailed error logging
from io import StringIO # For converting DataFrame to CSV string

# --- Pandas Import and Check ---
PANDAS_AVAILABLE = False
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    print("DEBUG [browser_tool.py]: Pandas loaded successfully for table extraction.")
    # Check for optional dependencies often needed by read_html
    try:
         import lxml
         print("DEBUG [browser_tool.py]: lxml found.")
    except ImportError:
         print("INFO [browser_tool.py]: lxml not found, pd.read_html might have limitations.")
    try:
         import html5lib
         print("DEBUG [browser_tool.py]: html5lib found.")
    except ImportError:
         print("INFO [browser_tool.py]: html5lib not found, pd.read_html might have limitations.")

except ImportError:
    print("WARNING [browser_tool.py]: Pandas library not found. Table extraction tool will not be functional.")
# --- ---

# --- Core Browser Functions ---

def _get_page_html(url: str, timeout_ms: int = 60000) -> tuple[str | None, str | None]:
    """Helper function to launch browser, navigate, and return HTML content or error."""
    html_content = None
    error_message = None
    browser = None
    print(f"DEBUG [_get_page_html]: Attempting to get HTML for {url} with timeout {timeout_ms}ms")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(timeout_ms) # Apply overall timeout

            print(f"DEBUG [_get_page_html]: Navigating to {url}...")
            # Use domcontentloaded first, as networkidle can be very long/unreliable
            page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
            print(f"DEBUG [_get_page_html]: DOM loaded for {url}.")

            # Optional: Wait briefly for potential JS rendering after DOM load
            try:
                page.wait_for_load_state('networkidle', timeout=15000) # Shorter wait for network idle
                print(f"DEBUG [_get_page_html]: Network appears idle (or timeout reached).")
            except PlaywrightTimeoutError:
                print(f"DEBUG [_get_page_html]: Network idle wait timed out, proceeding anyway.")
            time.sleep(0.5) # Small fixed delay after waits

            print(f"DEBUG [_get_page_html]: Getting page content...")
            html_content = page.content()
            print(f"DEBUG [_get_page_html]: Content retrieved (length {len(html_content) if html_content else 0}). Closing browser.")

        except PlaywrightTimeoutError as te:
            error_message = f"ERROR: Playwright timed out ({timeout_ms}ms exceeded) loading {url}. Page too slow or blocking automation. Details: {str(te)}"
            print(f"Browser Tool Error (Playwright Timeout): {error_message}")
        except PlaywrightError as pe:
            error_message = f"ERROR: Playwright error during navigation/interaction with {url}. Details: {str(pe)}"
            print(f"Browser Tool Error (Playwright General): {error_message}")
        except Exception as e:
             error_message = f"ERROR: Unexpected browser error for {url}. Details: {type(e).__name__} - {str(e)}"
             print(f"Browser Tool Error (Unknown): {error_message}")
             traceback.print_exc() # Log unexpected errors fully
        finally:
            if browser:
                try:
                    browser.close()
                    print(f"DEBUG [_get_page_html]: Browser closed.")
                except Exception as close_err:
                    print(f"Browser Tool Warning: Error closing browser: {close_err}")

    return html_content, error_message


def navigate_and_scrape(url_and_task: str) -> str:
    """
    Navigates to a URL using Playwright, waits for content, and scrapes TEXT content,
    prioritizing common article/headline tags. For TABLE data, use 'Extract Tables from Webpage'.
    Input format: "URL|Task Description". Returns scraped text or an ERROR message.
    """
    print(f"DEBUG [navigate_and_scrape]: Received request: '{url_and_task}'")
    if not isinstance(url_and_task, str) or '|' not in url_and_task:
         return "Error: Input format incorrect. Needs 'URL|Task Description'."
    try:
        parts = url_and_task.split('|', 1)
        if len(parts) != 2: return "Error: Input format incorrect. Needs 'URL|Task Description'."
        url, task_description = parts[0].strip(), parts[1].strip()
        if not url.startswith(('http://', 'https://')): return f"Error: Invalid URL '{url}'. Must start http/https."

        print(f"Browser Tool (Scraper): Navigating to {url} for task: {task_description}")

        # Get HTML using helper function
        html_content, error = _get_page_html(url)

        if error: return error # Return error message from helper if navigation failed
        if not html_content: return f"ERROR: Failed to retrieve HTML content from {url}, cannot scrape."

        print(f"Browser Tool (Scraper): Parsing HTML content (length {len(html_content)})...")
        soup = BeautifulSoup(html_content, 'lxml')

        # --- Improved Content Extraction Logic (Keep from your version) ---
        tags_to_remove = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button', 'iframe', 'noscript', 'meta', 'link']
        for tag_name in tags_to_remove: [tag.decompose() for tag in soup.find_all(tag_name)]
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)): comment.extract()
        main_content = soup.find('main') or soup.find('article') or soup.find(role='main')
        target_node = main_content if main_content else soup
        headlines = [h.get_text(strip=True) for h in target_node.find_all(['h1', 'h2', 'h3', 'h4'])]
        paragraphs = [p.get_text(strip=True) for p in target_node.find_all('p')]
        important_texts = headlines + paragraphs
        all_texts = target_node.get_text(separator='\n', strip=True)
        combined_important = '\n\n'.join(filter(None, important_texts)) # Add double newline between items
        if len(combined_important) > 200:
             text_content = combined_important
             print("Browser Tool (Scraper): Extracted text focusing on headlines/paragraphs.")
        else:
             text_content = '\n'.join(filter(None, all_texts.splitlines()))
             print("Browser Tool (Scraper): Extracted text from main node (fallback).")
        # --- End Improved Content Extraction ---

        if not text_content:
             return f"Warning: Successfully navigated to {url}, but no significant text found after filtering."

        print(f"Browser Tool (Scraper): Extracted raw text length {len(text_content)}.")
        max_len = 6000 # Keep increased limit
        if len(text_content) > max_len:
             print(f"Browser Tool (Scraper): Truncating content to {max_len} chars.")
             text_content = text_content[:max_len].rsplit(' ', 1)[0] + "\n... (truncated)" # Try to truncate at space

        return text_content

    except Exception as e:
        print(f"Browser Tool Error (Outer Scraper Scope): Failed processing '{url_and_task}'. Error: {e}")
        traceback.print_exc()
        return f"ERROR: Unexpected error scraping text from '{url_and_task}'. Details: {str(e)}"


# --- NEW FUNCTION: Extract Tables ---
def extract_tables_as_csv(url: str) -> str:
    """
    Navigates to a URL, finds HTML tables, parses the most likely data table
    using pandas, and returns it as a CSV string. For general text, use 'Web Browser Scraper'.
    Input: URL string. Returns 'Success: ... CSV Data:\n...' or 'Error: ...'.
    """
    if not PANDAS_AVAILABLE:
        return "Error: Pandas library is not installed on the server. Cannot extract tables."

    print(f"DEBUG [extract_tables_as_csv]: Received request for URL: '{url}'")
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
         return f"Error: Invalid URL '{url}'. Must be a string starting http/https."

    # Get HTML using helper function
    html_content, error = _get_page_html(url)

    if error: return error # Return error message from helper if navigation failed
    if not html_content: return f"ERROR: Failed to retrieve HTML content from {url}, cannot extract tables."

    print(f"Browser Tool (Table Extractor): Parsing HTML (length {len(html_content)}) for tables...")
    try:
        # Use pandas.read_html to find all tables
        # Requires lxml or html5lib installed! -> pip install lxml html5lib
        tables = pd.read_html(StringIO(html_content)) # Use StringIO to read from string
        print(f"Browser Tool (Table Extractor): Found {len(tables)} table(s) using pandas.")

        if not tables:
            return f"Error: No HTML tables found or parsed by pandas on the page {url}."

        # --- Heuristic to find the 'best' table ---
        # Find table with most cells (rows * columns) as a simple proxy for data content
        best_table = None
        max_cells = -1
        selected_table_index = -1
        for i, table_df in enumerate(tables):
             # Basic check if table looks valid (e.g., has more than 1 row/col maybe?)
             if isinstance(table_df, pd.DataFrame) and not table_df.empty and table_df.size > 1:
                 if table_df.size > max_cells:
                      max_cells = table_df.size
                      best_table = table_df
                      selected_table_index = i

        if best_table is None:
            return f"Error: Found {len(tables)} tables, but none seemed suitable (empty or very small) on {url}."

        print(f"Browser Tool (Table Extractor): Selected table index {selected_table_index} as best candidate (size={best_table.size}).")

        # --- Basic Cleaning of the Selected DataFrame ---
        # 1. Drop columns/rows that are ENTIRELY empty (NaN)
        cleaned_table = best_table.dropna(axis=1, how='all').dropna(axis=0, how='all')
        # 2. Optional: Try to reset index if it looks like multi-level header caused issues
        # cleaned_table.columns = ['_'.join(col).strip() for col in cleaned_table.columns.values] # Example for multi-index
        # 3. Optional: Fill remaining NaN with empty strings for cleaner CSV output?
        # cleaned_table = cleaned_table.fillna('')

        if cleaned_table.empty:
             return f"Error: Best table candidate (index {selected_table_index}) became empty after basic cleaning."

        # Convert selected DataFrame to CSV string
        output_buffer = StringIO()
        cleaned_table.to_csv(output_buffer, index=False) # Don't include pandas index in CSV
        csv_data = output_buffer.getvalue()
        output_buffer.close()

        # --- Limit Output Size ---
        max_len = 5000 # Slightly less than text scraper, as CSV can be dense
        original_len = len(csv_data)
        if original_len > max_len:
             print(f"Browser Tool (Table Extractor): Truncating CSV data from {original_len} to {max_len} chars.")
             # Truncate at the last newline before the limit
             last_newline = csv_data[:max_len].rfind('\n')
             if last_newline != -1:
                 csv_data = csv_data[:last_newline] + "\n... (truncated)"
             else: # If no newline found within limit, just truncate raw
                  csv_data = csv_data[:max_len] + "...(truncated)"

        print(f"Browser Tool (Table Extractor): Successfully extracted table data as CSV (length {len(csv_data)}).")
        # Prepend Success message
        return f"Success: Extracted table data from {url}.\nCSV Data:\n{csv_data}"

    except ValueError as ve:
         # This specific ValueError often means read_html found nothing parseable as tables
         print(f"Browser Tool (Table Extractor) Error (ValueError): {ve}. Likely no tables found.")
         return f"Error: No HTML tables could be parsed by pandas on {url}."
    except ImportError:
         # Should be caught by PANDAS_AVAILABLE check, but as safeguard
         print("Browser Tool (Table Extractor) Error: Pandas or required dependency (lxml, html5lib) missing.")
         return "Error: Server-side dependency missing for table parsing."
    except Exception as e:
         print(f"Browser Tool (Table Extractor) Error: Failed during table extraction/processing. Error: {e}")
         traceback.print_exc()
         return f"Error: Failed to extract or process tables from {url}. Reason: {str(e)}"


# --- LangChain Tool Definitions ---

# Tool for general text scraping (updated description)
browser_tool = Tool(
    name="Web Browser Text Scraper",
    func=navigate_and_scrape,
    description=(
        "Use this tool to navigate to a web URL and extract its main TEXT content, trying to prioritize headlines (h1-h4) and paragraphs (p). "
        "Input MUST be a single string containing the valid URL (starting with http:// or https://) "
        "followed by a pipe '|' and then a brief description of the task (e.g., what information to look for). "
        "Example: 'https://www.example-news.com/article-on-ai|Extract the key points.' "
        "Output is the cleaned text content (up to 6000 chars) or an ERROR message if navigation/scraping fails. "
        "Use this primarily for reading articles or getting general textual information. "
        "**If you specifically need data from HTML TABLES, use the 'Extract Tables from Webpage' tool instead.**"
    ),
)

# NEW Tool specifically for extracting tables
extract_tables_tool = Tool(
    name="Extract Tables from Webpage",
    func=extract_tables_as_csv,
    description=(
        "Use this tool ONLY when you need to extract STRUCTURED DATA presented in HTML TABLES on a webpage. "
        "Input MUST be a single valid URL string (starting with http:// or https://). "
        "It attempts to find all tables, select the most relevant one (based on size), clean it slightly, and return it as CSV formatted data. "
        "This is useful for getting statistics or lists from sources like IEA, IRENA, Wikipedia, etc., IF they use standard HTML tables. "
        "Output starts with 'Success:' and contains the CSV data, or 'Error:' if no suitable tables are found, the URL fails, or parsing fails. "
        "The returned CSV data can then be used for analysis or possibly with the chart generation tool (if the format is compatible). "
        "For general text extraction from a page, use the 'Web Browser Text Scraper' tool."
    ),
    # return_direct=False # Agent needs to process the CSV result
)