# tools/browser_tool.py (Enhanced with Text Scraper, Table Extractor, Click & Scrape)

import time
from langchain.tools import Tool
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup, Comment
import traceback
from io import StringIO
import re # For regex fallback in text scraper

# --- Pandas Import and Check ---
PANDAS_AVAILABLE = False
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    print("DEBUG [browser_tool.py]: Pandas loaded.")
    try: import lxml; print("DEBUG [browser_tool.py]: lxml found.")
    except ImportError: print("INFO [browser_tool.py]: lxml not found.")
    try: import html5lib; print("DEBUG [browser_tool.py]: html5lib found.")
    except ImportError: print("INFO [browser_tool.py]: html5lib not found.")
except ImportError: print("WARNING [browser_tool.py]: Pandas missing. Table extraction disabled.")
# --- ---

# === Helper Function: Get Page HTML (Handles Navigation & Basic Waits) ===
def _get_page_html(url: str, timeout_ms: int = 60000) -> tuple[str | None, str | None]:
    """Helper: Launches browser, navigates, waits, returns HTML content or error message."""
    html_content = None
    error_message = None
    browser = None
    page = None # Define page in outer scope for potential error messages
    print(f"DEBUG [_get_page_html]: Getting HTML: {url}, Timeout: {timeout_ms}ms")

    # --- Playwright Context Manager ---
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) # Consider headless=False for debugging visibility
            page = browser.new_page()
            page.set_default_timeout(timeout_ms)

            print(f"DEBUG [_get_page_html]: Navigating to {url}...")
            # Use 'domcontentloaded' as it's generally faster and sufficient for initial structure
            page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
            print(f"DEBUG [_get_page_html]: DOM loaded for {url}.")

            # Optional sophisticated wait: wait for network to be idle briefly *after* DOM load
            try:
                # print(f"DEBUG [_get_page_html]: Waiting for network idle (max 15s)...")
                page.wait_for_load_state('networkidle', timeout=15000)
                print(f"DEBUG [_get_page_html]: Network appears idle (or short timeout reached).")
            except PlaywrightTimeoutError:
                print(f"DEBUG [_get_page_html]: Network idle wait timed out, proceeding.")

            # Add small fixed delay for any final JS adjustments
            time.sleep(1.0)

            print(f"DEBUG [_get_page_html]: Getting page content...")
            html_content = page.content()
            print(f"DEBUG [_get_page_html]: Content length {len(html_content) if html_content else 0}.")

    # --- Error Handling ---
    except PlaywrightTimeoutError as te:
        page_url = page.url if page else url # Get current URL if possible
        error_message = f"ERROR: Playwright timed out ({timeout_ms}ms) loading or waiting on '{page_url}'. Page slow/complex or blocking automation. Details: {str(te)[:200]}"
        print(f"Browser Tool Error (Timeout): {error_message}")
    except PlaywrightError as pe:
        page_url = page.url if page else url
        # Classify common Playwright errors if possible
        if "net::ERR_NAME_NOT_RESOLVED" in str(pe): error_message = f"ERROR: Could not resolve hostname for URL '{page_url}'. Check URL validity/DNS."
        elif "net::ERR_CONNECTION_REFUSED" in str(pe): error_message = f"ERROR: Connection refused by server for '{page_url}'. Server down or blocking?"
        else: error_message = f"ERROR: Playwright navigation/interaction error with '{page_url}'. Details: {str(pe)[:250]}"
        print(f"Browser Tool Error (Playwright): {error_message}")
    except Exception as e:
         page_url = page.url if page else url
         error_message = f"ERROR: Unexpected browser error for '{page_url}'. Details: {type(e).__name__} - {str(e)[:200]}"
         print(f"Browser Tool Error (Unknown): {error_message}"); traceback.print_exc()
    # --- Browser Closing (Ensure it happens) ---
    finally:
        if browser:
            try: browser.close(); print(f"DEBUG [_get_page_html]: Browser closed.")
            except Exception as ce: print(f"Warning: Error closing browser: {ce}")

    return html_content, error_message


# === Tool 1: Text Scraper (Enhanced) ===
def navigate_and_scrape_text(url_and_task: str) -> str:
    """ Navigates, waits, scrapes TEXT. Includes weather heuristics. Use table tool for tables. """
    # ... (Keep implementation from previous 'weather heuristics' version) ...
    # ... Calls _get_page_html, parses with BS4, tries specific selectors, falls back ...
    print(f"DEBUG [navigate_and_scrape_text]: Request: '{url_and_task}'")
    if not isinstance(url_and_task, str) or '|' not in url_and_task: return "Error: Input format 'URL|Task'."
    try:
        parts = url_and_task.split('|', 1); url, task_desc = parts[0].strip(), parts[1].strip()
        if not url.startswith(('http://','https://')): return f"Error: Invalid URL '{url}'."
        print(f"Browser (Text Scraper): Navigating {url} for task: {task_desc}")
        html_content, error = _get_page_html(url)
        if error: return error
        if not html_content: return f"ERROR: No HTML from {url}."
        print(f"Browser (Text Scraper): Parsing HTML (len {len(html_content)})...")
        soup = BeautifulSoup(html_content, 'lxml')
        # Cleaning
        tags_to_remove = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button', 'iframe', 'noscript', 'meta', 'link', 'svg', 'path', 'img', 'picture', 'video', 'audio']
        for tag_name in tags_to_remove: [tag.decompose() for tag in soup.find_all(tag_name)]
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)): comment.extract()
        # Weather Heuristics
        selectors = {'location': ['#wob_loc', '.CurrentConditions--location--1YWj_'], 'temperature': ['#wob_tm', '.CurrentConditions--tempValue--MHmYY'], 'condition': ['#wob_dc', '.CurrentConditions--phraseValue--mZC_p'], 'precip': ['#wob_pp', '[data-testid="PercentageValue"]'], 'humidity': ['#wob_hm', '[data-testid="PercentageValue"]'], 'wind': ['#wob_ws', '[data-testid="Wind"]']}
        weather_data = {}; found_specific = False
        for key, sel_list in selectors.items():
            for selector in sel_list:
                try:
                    element = soup.select_one(selector)
                    if element: text = element.get_text(strip=True);
                    if text: weather_data[key] = text; found_specific = True; break
                except Exception: pass # Ignore selector errors
        # Format Weather Data if Found
        if found_specific and weather_data:
            summary_parts = []; added_percent = False
            if 'location' in weather_data: summary_parts.append(f"Location: {weather_data['location']}")
            if 'temperature' in weather_data: summary_parts.append(f"Temperature: {weather_data['temperature']}°")
            if 'condition' in weather_data: summary_parts.append(f"Conditions: {weather_data['condition']}")
            if 'precip' in weather_data and not added_percent: summary_parts.append(f"Precipitation: {weather_data['precip']}"); added_percent=True
            if 'humidity' in weather_data and not added_percent: summary_parts.append(f"Humidity: {weather_data['humidity']}")
            if 'wind' in weather_data: summary_parts.append(f"Wind: {weather_data['wind']}")
            if summary_parts: text_content = "\n".join(summary_parts); print("Browser (Text Scraper): Using specific weather data."); return text_content
        # Fallback Text Extraction
        main_content = soup.find('main') or soup.find('article') or soup.find(role='main'); target_node = main_content if main_content else soup
        headlines = [h.get_text(strip=True) for h in target_node.find_all(['h1','h2','h3','h4'])]; paragraphs = [p.get_text(strip=True) for p in target_node.find_all('p')]; all_texts = target_node.get_text(separator='\n', strip=True)
        combined_important = '\n\n'.join(filter(None, headlines + paragraphs))
        if len(combined_important) > 100: text_content = combined_important; print("Browser (Text Scraper) Fallback: Headlines/Paras.")
        else: text_content = '\n'.join(line.strip() for line in all_texts.splitlines() if line.strip()); print("Browser (Text Scraper) Fallback: All text.")
        if not text_content: return f"Warning: Navigated {url}, no significant text found."
        # Regex Fallback (simplified)
        if not found_specific:
            temp_m=re.search(r'(\d{1,3})\s?°', text_content); cond_m=re.search(r'(Cloudy|Sunny|Partly Cloudy|Rain|Snow|Clear|Overcast|Fog|Mist)', text_content, re.I)
            if temp_m or cond_m: regex_s="Regex Found:\n";
            if temp_m: regex_s+=f"- Temp ~ {temp_m.group(1)}°\n"
            if cond_m: regex_s+=f"- Cond ~ {cond_m.group(0)}\n"
            text_content=regex_s+"---\n"+text_content; print("Browser (Text Scraper) Fallback: Added regex finds.")
        # Truncate
        max_len = 6000;
        if len(text_content)>max_len: print(f"Browser (Text Scraper): Truncating..."); text_content=text_content[:max_len].rsplit('\n',1)[0]+"\n... (truncated)"
        return text_content
    except Exception as e: print(f"Error (Outer Scraper): {e}"); traceback.print_exc(); return f"ERROR: Unexpected scraping text: {str(e)}"


# === Tool 2: Table Extractor ===
def extract_tables_as_csv(url: str) -> str:
    """ Navigates, finds HTML tables, parses best via pandas, returns as CSV string. """
    # ... (Keep implementation from previous 'combined' version - calls _get_page_html) ...
    if not PANDAS_AVAILABLE: return "Error: Pandas not available."
    print(f"DEBUG [extract_tables_as_csv]: Request URL: '{url}'")
    if not isinstance(url, str) or not url.startswith(('http://','https://')): return f"Error: Invalid URL '{url}'."
    html_content, error = _get_page_html(url);
    if error: return error;
    if not html_content: return f"ERROR: Failed to get HTML from {url}."
    print(f"Browser (Table): Parsing HTML (len {len(html_content)}) for tables...")
    try:
        tables = pd.read_html(StringIO(html_content)); print(f"Browser (Table): Found {len(tables)} table(s).")
        if not tables: return f"Error: No HTML tables parsed on {url}."
        # (Select best table logic...)
        best_table=None; max_cells=-1; idx=-1
        for i, df in enumerate(tables):
             if isinstance(df, pd.DataFrame) and not df.empty and df.size>1:
                 if df.size > max_cells: max_cells=df.size; best_table=df; idx=i
        if best_table is None: return f"Error: No suitable tables found on {url}."
        print(f"Browser (Table): Selected table index {idx} (size={max_cells}).")
        # (Cleaning logic...)
        ct=best_table.dropna(axis=1,how='all').dropna(axis=0,how='all').fillna('')
        if ct.empty: return f"Error: Best table empty after cleaning."
        # (CSV conversion...)
        out_buf=StringIO(); ct.to_csv(out_buf, index=False); csv_data=out_buf.getvalue(); out_buf.close()
        # (Truncation logic...)
        max_len=5000;
        if len(csv_data) > max_len: csv_data=csv_data[:max_len].rsplit('\n',1)[0]+"\n... (truncated)"
        print(f"Browser (Table): Extracted CSV (len {len(csv_data)}).")
        return f"Success: Extracted table data from {url}.\nCSV Data:\n{csv_data}"
    except ValueError as ve: return f"Error: No tables parsed ({ve})." # Often 'No tables found'
    except Exception as e: print(f"Error (Table): {e}"); traceback.print_exc(); return f"Error extracting tables: {str(e)}"


# === Tool 3: Click Element and Scrape Text (NEW & EXPERIMENTAL) ===
def click_element_and_scrape_text(url_and_selector: str) -> str:
    """
    EXPERIMENTAL: Navigates to URL, waits, CLICKS element specified by CSS selector,
    waits briefly for potential updates, then scrapes TEXT content like the main scraper.
    Input format: "URL|CSS_SELECTOR". Use precise CSS selectors.
    Returns scraped text AFTER click or an ERROR message. Might fail on complex JS sites.
    """
    print(f"DEBUG [click_and_scrape]: Received request: '{url_and_selector}'")
    if not isinstance(url_and_selector, str) or '|' not in url_and_selector:
         return "Error: Input format incorrect. Needs 'URL|CSS_SELECTOR'."

    try:
        parts = url_and_selector.split('|', 1)
        if len(parts) != 2: return "Error: Input must be 'URL|CSS_SELECTOR'."
        url, css_selector = parts[0].strip(), parts[1].strip()
        if not url.startswith(('http://', 'https://')): return f"Error: Invalid URL '{url}'."
        if not css_selector: return f"Error: CSS Selector cannot be empty."

        print(f"Browser Tool (Click & Scrape): Navigating to {url}, will click '{css_selector}'")

        # --- Playwright Interaction ---
        html_content_after_click = None
        error_message = None
        browser = None
        page = None
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(60000) # 60s timeout

                print(f"DEBUG [click_and_scrape]: Navigating to {url}...")
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                print(f"DEBUG [click_and_scrape]: DOM loaded. Waiting for element '{css_selector}'...")

                # Wait for the element to be present and potentially visible/stable
                try:
                    target_element = page.locator(css_selector).first # Use .first to avoid ambiguity if multiple match
                    target_element.wait_for(state='visible', timeout=20000) # Wait up to 20s for visibility
                    print(f"DEBUG [click_and_scrape]: Element '{css_selector}' located and visible.")
                except PlaywrightTimeoutError:
                    return f"ERROR: Timed out waiting for element '{css_selector}' to become visible on {url}."
                except Exception as loc_err: # Catch other locator errors
                     return f"ERROR: Could not reliably locate element '{css_selector}' on {url}. Check selector validity. Details: {loc_err}"

                # Perform the click
                print(f"DEBUG [click_and_scrape]: Clicking element '{css_selector}'...")
                target_element.click(timeout=10000) # Timeout for the click action itself
                print(f"DEBUG [click_and_scrape]: Click performed.")

                # --- Wait for potential page changes ---
                # This is the tricky part. How long to wait? What to wait for?
                # Option 1: Fixed delay (simplest, least reliable)
                wait_time = 3 # Wait 3 seconds
                print(f"DEBUG [click_and_scrape]: Waiting {wait_time}s for potential page updates...")
                time.sleep(wait_time)
                # Option 2: Wait for network idle again (might work for AJAX)
                # try:
                #     page.wait_for_load_state('networkidle', timeout=15000)
                #     print(f"DEBUG [click_and_scrape]: Network idle after click.")
                # except PlaywrightTimeoutError:
                #     print(f"DEBUG [click_and_scrape]: Network idle wait after click timed out.")
                # Option 3: Wait for a specific element expected AFTER the click (most reliable if predictable)
                # try:
                #     page.locator("SOME_SELECTOR_EXPECTED_AFTER_CLICK").wait_for(state='visible', timeout=15000)
                #     print(f"DEBUG [click_and_scrape]: Found expected element after click.")
                # except PlaywrightTimeoutError:
                #     print(f"DEBUG [click_and_scrape]: Did not find expected element after click.")

                print(f"DEBUG [click_and_scrape]: Getting page content AFTER click...")
                html_content_after_click = page.content()

            # --- Error Handling (Copy from _get_page_html, adjust messages) ---
            except PlaywrightTimeoutError as te: error_message = f"ERROR: Playwright timeout occurred during click/wait process on {url} after trying to click '{css_selector}'. Details: {str(te)[:200]}"
            except PlaywrightError as pe: error_message = f"ERROR: Playwright error during click/wait process on {url} for selector '{css_selector}'. Details: {str(pe)[:250]}"
            except Exception as e: error_message = f"ERROR: Unexpected error during click/wait for '{css_selector}' on {url}. Details: {type(e).__name__} - {str(e)[:200]}"; traceback.print_exc()
            finally:
                if browser:
                    try: browser.close(); print(f"DEBUG [click_and_scrape]: Browser closed.")
                    except Exception as ce: print(f"Warning: Error closing browser: {ce}")
        # --- End Playwright Interaction ---

        if error_message: return error_message # Return error if click/wait failed
        if not html_content_after_click: return f"ERROR: Got no HTML content AFTER clicking '{css_selector}' on {url}."

        # --- Scrape Text Content AFTER the click (using same logic as navigate_and_scrape) ---
        print(f"Browser Tool (Click & Scrape): Parsing HTML after click (len {len(html_content_after_click)})...")
        soup = BeautifulSoup(html_content_after_click, 'lxml')
        tags_to_remove = ['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'button', 'iframe', 'noscript', 'meta', 'link', 'svg', 'path', 'img', 'picture', 'video', 'audio']
        for tag_name in tags_to_remove: [tag.decompose() for tag in soup.find_all(tag_name)]
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)): comment.extract()
        main_content = soup.find('main') or soup.find('article') or soup.find(role='main'); target_node = main_content if main_content else soup
        headlines = [h.get_text(strip=True) for h in target_node.find_all(['h1','h2','h3','h4'])]; paragraphs = [p.get_text(strip=True) for p in target_node.find_all('p')]
        text_content = '\n\n'.join(filter(None, headlines + paragraphs)) # Prioritize these
        if len(text_content) < 100: # If not much structured text, get all
             all_texts = target_node.get_text(separator='\n', strip=True)
             text_content = '\n'.join(line.strip() for line in all_texts.splitlines() if line.strip())
        if not text_content: return f"Warning: Clicked '{css_selector}' on {url}, but no significant text found AFTER click."
        print(f"Browser Tool (Click & Scrape): Extracted text length {len(text_content)} after click.")
        max_len=6000
        if len(text_content)>max_len: print(f"Browser (Click & Scrape): Truncating..."); text_content=text_content[:max_len].rsplit('\n',1)[0]+"\n... (truncated)"
        return text_content

    except Exception as e:
        print(f"Browser Tool Error (Outer Click Scope): Failed processing '{url_and_selector}'. Error: {e}")
        traceback.print_exc()
        return f"ERROR: Unexpected error performing click/scrape for '{url_and_selector}'. Details: {str(e)}"


# --- LangChain Tool Definitions ---

browser_tool = Tool(
    name="Web Browser Text Scraper",
    func=navigate_and_scrape_text, # Use updated text scraping function
    description=( # Updated description
        "Use this tool to navigate to a web URL and extract its main TEXT content. "
        "Tries to find specific weather elements first, then falls back to headlines/paragraphs/general text. "
        "Input MUST be 'URL|Task Description' (e.g., 'https://google.com/search?q=weather+london|Get current temp'). "
        "Output is extracted text (max ~6000 chars) or an ERROR. "
        "Use for reading articles/general info. Use 'Extract Tables' for HTML TABLE data. "
        "Use 'Click Element and Scrape' if you need to click something FIRST."
    ),
)

extract_tables_tool = Tool(
    name="Extract Tables from Webpage",
    func=extract_tables_as_csv, # Keep existing table tool function
    description=( # Keep existing description
        "Use ONLY to extract STRUCTURED DATA from HTML TABLES. Input: URL string. "
        "Parses best table into CSV. Output: 'Success:...CSV...' or 'Error:...'. Requires pandas/lxml/html5lib. "
        "Use 'Web Browser Text Scraper' for general text."
    ),
)

# --- NEW Click and Scrape Tool ---
click_and_scrape_tool = Tool(
    name="Click Element and Scrape Text",
    func=click_element_and_scrape_text,
    description=(
        "EXPERIMENTAL: Use to CLICK an element (button, link) on a page using a CSS SELECTOR, wait briefly, then scrape the resulting page's TEXT content. "
        "Input MUST be 'URL|CSS_SELECTOR'. Example: 'https://example.com/products|button.load-more'. "
        "Use browser developer tools to find the correct CSS selector for the element to click. Be precise. "
        "Output is the TEXT content found AFTER the click (similar to the main text scraper) or an ERROR message. "
        "This might fail on pages with complex JavaScript or delayed loading after clicks. "
        "Use 'Web Browser Text Scraper' if no click is needed."
    )
)