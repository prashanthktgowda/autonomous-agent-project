# autonomous-agent-project/tools/browser_tool.py

import time
from langchain.tools import Tool
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup, Comment # Import Comment

# --- Core Browser Functions ---

def navigate_and_scrape(url_and_task: str) -> str:
    """
    Navigates to a URL using Playwright, waits for content, and scrapes text content,
    prioritizing common article/headline tags.
    Input format: "URL|Task Description". Returns scraped text or an ERROR message.
    """
    # ... (Input parsing and URL validation remain the same) ...
    try:
        parts = url_and_task.split('|', 1)
        if len(parts) != 2:
            return "Error: Input must be in the format 'URL|Task Description'. Example: 'https://example.com|Summarize the page'"
        url, task_description = parts[0].strip(), parts[1].strip()

        if not (url.startswith('http://') or url.startswith('https://')):
            return f"Error: Invalid URL '{url}'. Must start with http:// or https://"

        print(f"Browser Tool: Navigating to {url} for task: {task_description}")
        html_content = ""

        # Launch Playwright and Navigate (with increased timeout and specific wait)
        with sync_playwright() as p:
            browser = None
            try:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(60000) # 60 seconds timeout

                print(f"Browser Tool: Attempting to go to {url}")
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                print(f"Browser Tool: DOM loaded for {url}.")

                # Wait for a basic indicator of content (e.g., body tag is present)
                # You can still refine the headline_selector based on target sites
                content_indicator_selector = "body" # Wait for body to ensure page structure exists
                print(f"Browser Tool: Waiting up to 30s for selector: '{content_indicator_selector}'...")
                try:
                    page.wait_for_selector(content_indicator_selector, state='attached', timeout=30000)
                    print(f"Browser Tool: Found selector '{content_indicator_selector}'.")
                    # Give a brief moment for dynamic content loading after basic structure
                    time.sleep(1) # Small fixed delay
                except PlaywrightTimeoutError:
                    print(f"Browser Tool Warning: Page loaded but waiting for '{content_indicator_selector}' timed out. Scraping might be incomplete.")

                print(f"Browser Tool: Getting page content...")
                html_content = page.content()
                print(f"Browser Tool: Content retrieved (length {len(html_content)}). Closing browser.")
                browser.close()
                print(f"Browser Tool: Browser closed.")

            # ... (Error handling for PlaywrightTimeoutError, PlaywrightError, Exception remains the same) ...
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


        if not html_content:
             return f"ERROR: Failed to retrieve HTML content from {url}, cannot scrape."

        print(f"Browser Tool: Parsing HTML content...")
        soup = BeautifulSoup(html_content, 'lxml')

        # --- Improved Content Extraction ---
        # 1. Remove script, style, comments, and common clutter tags
        tags_to_remove = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button', 'iframe', 'noscript', 'meta', 'link']
        for tag_name in tags_to_remove:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # 2. Attempt to find main content areas (prioritize these if found)
        main_content = soup.find('main') or soup.find('article') or soup.find(role='main')
        target_node = main_content if main_content else soup # Use whole soup if no main area found

        # 3. Extract text, prioritizing headlines and paragraphs
        # Get headlines first
        headlines = [h.get_text(strip=True) for h in target_node.find_all(['h1', 'h2', 'h3', 'h4'])]
        # Get paragraph text
        paragraphs = [p.get_text(strip=True) for p in target_node.find_all('p')]

        # Combine, prioritizing headlines, then paragraphs, remove duplicates implicitly via set
        important_texts = headlines + paragraphs
        all_texts = target_node.get_text(separator='\n', strip=True) # Fallback if needed

        # Simple heuristic: if headlines/paragraphs give decent text, use that, else use all text
        combined_important = '\n'.join(filter(None, important_texts))
        if len(combined_important) > 200: # Arbitrary threshold: use focused text if substantial
             text_content = combined_important
             print("Browser Tool: Extracted text focusing on headlines and paragraphs.")
        else:
             text_content = '\n'.join(filter(None, all_texts.splitlines())) # Cleanup all_texts
             print("Browser Tool: Extracted text from the main node (fallback).")
        # --- End Improved Content Extraction ---


        if not text_content:
             return f"Warning: Successfully navigated to {url} and parsed HTML, but no significant text content found after filtering/extraction. Page might lack text or have unusual structure."

        print(f"Browser Tool: Extracted raw text length {len(text_content)} characters from {url}")

        # Limit Output Size
        max_len = 6000 # Increased slightly
        if len(text_content) > max_len:
             print(f"Browser Tool: Truncating content from {len(text_content)} to {max_len} chars.")
             text_content = text_content[:max_len] + "\n... (truncated)"

        return text_content

    except Exception as e:
        # ... (Outer error handling remains the same) ...
        print(f"Browser Tool Error (Outer Scope): Failed processing '{url_and_task}'. Error: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging server-side
        return f"ERROR: An unexpected error occurred while processing the browser request for '{url_and_task}'. Details: {str(e)}"


# --- LangChain Tool Definition --- (Description slightly updated)

browser_tool = Tool(
    name="Web Browser Scraper",
    func=navigate_and_scrape,
    description=(
        "Use this tool to navigate to a web URL and extract its main text content, trying to prioritize headlines (h1-h4) and paragraphs (p). "
        "Input MUST be a single string containing the valid URL (starting with http:// or https://) "
        "followed by a pipe '|' and then a brief description of the task or information needed. "
        "Example: 'https://www.example-news.com/article-on-ai|Extract the key points.' "
        "Output is the cleaned text content (up to 6000 chars) or an ERROR message if navigation/scraping fails (e.g., due to timeout). "
        "Use this after a Search tool if the URL is unknown, or directly if the URL is known. "
        "It's best for reading articles or getting textual information from a page."
    ),
)