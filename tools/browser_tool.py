# autonomous-agent-project/tools/browser_tool.py

import time
from langchain.tools import Tool
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

# --- Core Browser Functions ---

def navigate_and_scrape(url_and_task: str) -> str:
    """
    Navigates to a URL using Playwright, waits for content (specifically headlines if possible),
    and scrapes the main text content using BeautifulSoup.
    Input should be a single string containing the URL and the task description,
    separated by a pipe '|'. Example: "https://example.com|Find main points".
    Returns the scraped text or an explicit error message.
    """
    try:
        # 1. Parse Input
        parts = url_and_task.split('|', 1)
        if len(parts) != 2:
            return "Error: Input must be in the format 'URL|Task Description'. Example: 'https://example.com|Summarize the page'"
        url, task_description = parts[0].strip(), parts[1].strip()

        # 2. Validate URL
        if not (url.startswith('http://') or url.startswith('https://')):
            return f"Error: Invalid URL '{url}'. Must start with http:// or https://"

        print(f"Browser Tool: Navigating to {url} for task: {task_description}")
        html_content = ""

        # 3. Launch Playwright and Navigate
        with sync_playwright() as p:
            browser = None # Initialize browser variable
            try:
                # Launch browser (headless=True recommended for automation)
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                # Set INCREASED default timeout (in milliseconds) for operations
                page.set_default_timeout(60000) # 60 seconds

                print(f"Browser Tool: Attempting to go to {url}")

                # --- Improved Waiting Strategy ---
                # a) Go to URL, wait for basic DOM structure first
                page.goto(url, wait_until='domcontentloaded', timeout=60000) # Increased timeout
                print(f"Browser Tool: DOM loaded for {url}.")

                # b) Wait specifically for a likely headline element
                # ** ACTION REQUIRED: Inspect bbc.com/news and find a better selector if possible! **
                # Examples: 'h3.gs-c-promo-heading__title', 'article h3', '[data-testid="headline"] a'
                headline_selector = "h3" # Using generic h3 as a starting point
                print(f"Browser Tool: Waiting up to 45s for selector: '{headline_selector}'...")
                try:
                    # Wait for the *first* element matching the selector to appear
                    page.wait_for_selector(headline_selector, state='visible', timeout=45000) # Wait up to 45s *after* DOM load
                    print(f"Browser Tool: Found selector '{headline_selector}'. Page likely has headlines.")
                    # Optional: add a small sleep AFTER selector found if content loads dynamically within elements
                    # time.sleep(2)
                except PlaywrightTimeoutError:
                    # If the specific selector times out, don't fail entirely, just warn and proceed
                    print(f"Browser Tool Warning: Page loaded but waiting for specific selector '{headline_selector}' timed out. Scraping available content anyway.")
                # --- End Improved Waiting Strategy ---

                print(f"Browser Tool: Getting page content...")
                html_content = page.content() # Get HTML after waiting
                print(f"Browser Tool: Content retrieved (length {len(html_content)}). Closing browser.")
                browser.close()
                print(f"Browser Tool: Browser closed.")

            except PlaywrightTimeoutError as te:
                error_message = f"ERROR: Playwright timed out ({page.context.timeout}ms exceeded) while trying to load or wait for elements on {url}. The page might be too slow, complex, or blocking automation. Details: {str(te)}"
                print(f"Browser Tool Error (Playwright Timeout): {error_message}")
                if browser: browser.close() # Ensure browser is closed on timeout
                return error_message
            except PlaywrightError as pe:
                error_message = f"ERROR: Playwright encountered an error during navigation/interaction with {url}. Details: {str(pe)}"
                print(f"Browser Tool Error (Playwright General): {error_message}")
                if browser: browser.close() # Ensure browser is closed on other playwright errors
                return error_message
            except Exception as e: # Catch other potential errors during browser ops
                 error_message = f"ERROR: An unexpected error occurred during browser operation for {url}. Details: {str(e)}"
                 print(f"Browser Tool Error (Unknown): {error_message}")
                 if browser: browser.close() # Ensure browser is closed
                 return error_message

        # 4. Parse with BeautifulSoup if content was retrieved
        if not html_content:
             # This case should ideally be caught by exceptions above, but as a safeguard:
             return f"ERROR: Failed to retrieve HTML content from {url}, cannot scrape."

        print(f"Browser Tool: Parsing HTML content...")
        soup = BeautifulSoup(html_content, 'lxml') # Use lxml for robustness

        # 5. Basic Tag Cleaning (Remove common clutter)
        tags_to_remove = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button', 'iframe', 'noscript']
        for tag_name in tags_to_remove:
             for tag in soup.find_all(tag_name):
                 tag.decompose()

        # 6. Extract Text
        # Consider finding a main content area if possible (e.g., soup.find('main') or soup.find('article'))
        # For now, extract all remaining text
        raw_text = soup.get_text(separator=' ', strip=True)

        # Simple text cleanup (remove excessive whitespace/newlines)
        lines = (line.strip() for line in raw_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text_content = '\n'.join(chunk for chunk in chunks if chunk) # Rejoin with single newline

        if not text_content:
             return f"Warning: Successfully navigated to {url} and parsed HTML, but no significant text content found after filtering common tags like ({', '.join(tags_to_remove)}). The page structure might be unusual or primarily non-text."

        print(f"Browser Tool: Scraped {len(text_content)} characters from {url}")

        # 7. Limit Output Size
        max_len = 5000 # Truncate to avoid overwhelming LLM context
        if len(text_content) > max_len:
             print(f"Browser Tool: Truncating content from {len(text_content)} to {max_len} chars.")
             text_content = text_content[:max_len] + "\n... (truncated)"

        return text_content

    except Exception as e:
        # Catch-all for errors outside the Playwright block (e.g., input parsing)
        print(f"Browser Tool Error (Outer Scope): Failed processing '{url_and_task}'. Error: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging server-side
        return f"ERROR: An unexpected error occurred while processing the browser request for '{url_and_task}'. Details: {str(e)}"

# --- LangChain Tool Definition ---

browser_tool = Tool(
    name="Web Browser Scraper",
    func=navigate_and_scrape,
    description=(
        "Use this tool to navigate to a web URL and extract its main text content after filtering common tags "
        "(like navigation, footer, scripts). It tries to wait for headlines (h3 tags by default) to appear. "
        "Input MUST be a single string containing the valid URL (starting with http:// or https://) "
        "followed by a pipe '|' and then a brief description of the task or information needed. "
        "Example: 'https://www.bbc.com/news|Extract the key headlines.' "
        "Output is the cleaned text content of the page (up to 5000 chars) or an ERROR message if navigation/scraping fails (e.g., due to timeout). "
        "Use this for finding information, reading articles, or getting general website text. "
        "Do NOT use this for complex interactions like filling forms or clicking specific buttons."
    ),
)