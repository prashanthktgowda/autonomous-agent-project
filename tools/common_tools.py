# tools/common_tools.py (Contains Calculator, DateTime, Summarizer Function)

from langchain.tools import Tool
from datetime import datetime
import numexpr # Using numexpr for safe evaluation - install with: pip install numexpr
import traceback
# We need the LLM type hint for the summarizer function
from langchain_core.language_models.chat_models import BaseChatModel

# --- Calculator Tool ---
def calculate(expression: str) -> str:
    """
    Safely evaluates a mathematical expression string using numexpr.
    Supports basic arithmetic, powers, parentheses, and common math functions.
    Input: Mathematical expression string (e.g., '2 * (3+4) / sqrt(16)').
    Output: String 'Result: <value>' or 'Error: <reason>'.
    """
    # Strip potential markdown backticks sometimes added by LLMs
    cleaned_expression = expression.strip().strip('`')
    print(f"DEBUG [Calculator]: Evaluating '{cleaned_expression}'")
    if not cleaned_expression:
        return "Error: Empty expression provided."
    try:
        # Use numexpr for safer evaluation than eval()
        result = numexpr.evaluate(cleaned_expression)
        # Convert result to standard Python types (e.g., from numpy floats)
        if hasattr(result, 'item'): # Handles numpy array scalars
             result = result.item()
        # Format potentially long floats
        if isinstance(result, float):
             result_str = f"{result:.10g}" # Format to reasonable precision
        else:
             result_str = str(result)
        print(f"DEBUG [Calculator]: Result = {result_str}")
        return f"Result: {result_str}"
    except SyntaxError:
        print(f"Calculator Error: Syntax error in '{cleaned_expression}'")
        return "Error: Invalid mathematical syntax in expression."
    except NameError as e:
        # numexpr raises NameError for undefined variables/functions
        print(f"Calculator Error: Name error in '{cleaned_expression}': {e}")
        return f"Error: Invalid expression or unsupported function/variable used: {e}"
    except Exception as e:
        print(f"Calculator Error: Failed evaluation for '{cleaned_expression}'. Error: {e}")
        traceback.print_exc()
        return f"Error: Could not evaluate expression. Reason: {type(e).__name__} - {e}"

calculator_tool = Tool(
    name="Calculator",
    func=calculate,
    description=(
        "Use this tool ONLY for evaluating mathematical expressions. "
        "Input MUST be a valid mathematical expression string (e.g., '150 * 3 / 5 + (2**3)', 'sqrt(144) * 2', '(10 + 5) * 4'). "
        "Supports: +, -, *, /, ** (power), parentheses (). Common functions: sqrt, sin, cos, tan, log, log10, exp. "
        "Do NOT input natural language questions, only the expression itself. "
        "Output is the calculated result prefixed with 'Result:' or an 'Error:' message."
    )
)

# --- Current Date/Time Tool ---
def get_current_datetime(ignored_input: str = "") -> str:
    """Returns the current date and time in ISO-like format with timezone."""
    try:
        now = datetime.now().astimezone() # Get current time in local timezone
        # ISO 8601 format is standard and includes timezone offset
        formatted_time = now.isoformat(sep=' ', timespec='seconds')
        print(f"DEBUG [DateTime]: Returning current time: {formatted_time}")
        return f"Current date and time is: {formatted_time}"
    except Exception as e:
        print(f"DateTime Tool Error: {e}"); traceback.print_exc()
        return f"Error: Could not retrieve current date/time. Reason: {e}"


datetime_tool = Tool(
    name="Get Current Date and Time",
    func=get_current_datetime,
    description=(
        "Use this tool to get the current exact date and time, including the local timezone information. "
        "Takes no meaningful input (can be an empty string or ignored). "
        "Output is a string stating the current date and time in a standard format (YYYY-MM-DD HH:MM:SS+ZZ:ZZ)."
    )
)

# --- Text Summarization Tool Function ---
# This function requires the LLM instance to be passed in.
# The Tool object itself is created dynamically in planner.py.

def summarize_text_func(llm_instance: BaseChatModel, text_to_summarize: str) -> str:
    """Uses the provided LLM instance to summarize a piece of text."""
    if not llm_instance: # Safety check
        print("Summarizer Error: LLM instance was not provided to the function.")
        return "Error: Summarization tool not configured correctly (missing LLM)."
    if not text_to_summarize or not isinstance(text_to_summarize, str):
        return "Error: No valid text provided for summarization."

    # Strip potential prefixes added by other tools
    if text_to_summarize.startswith("Success:"): text_to_summarize = text_to_summarize.split("\n", 1)[1]
    if text_to_summarize.startswith("CSV Data:"): text_to_summarize = text_to_summarize.split("\n", 1)[1]
    text_to_summarize = text_to_summarize.strip()
    if not text_to_summarize: return "Error: Text empty after cleaning prefixes."


    print(f"DEBUG [Summarizer]: Request to summarize text (length {len(text_to_summarize)})...")
    # Limit input length robustly
    max_summary_input = 15000 # Max chars to send for summary (adjust based on LLM limits/cost)
    if len(text_to_summarize) > max_summary_input:
        print(f"DEBUG [Summarizer]: Input truncated from {len(text_to_summarize)} to {max_summary_input} chars.")
        text_to_summarize = text_to_summarize[:max_summary_input].rsplit(' ', 1)[0] + "... (original text truncated)" # Try truncating at space

    # Simple, direct prompt for summarization
    # You might refine this prompt further based on desired summary style/length
    prompt = f"""Please provide a concise and informative summary of the following text:

    --- TEXT START ---
    {text_to_summarize}
    --- TEXT END ---

    Concise Summary:"""

    try:
        # Invoke the LLM passed into the function
        print(f"DEBUG [Summarizer]: Sending text to LLM for summarization...")
        summary_result = llm_instance.invoke(prompt)
        # Extract content depending on LLM response type (AIMessage, string, etc.)
        if hasattr(summary_result, 'content'):
            summary = summary_result.content.strip()
        else:
            summary = str(summary_result).strip()

        if not summary:
             print("Summarizer Warning: LLM returned empty summary.")
             return "Summary: The LLM returned an empty summary for the provided text."

        print(f"DEBUG [Summarizer]: Summary generated (length {len(summary)}).")
        return f"Summary:\n{summary}"
    except Exception as e:
        print(f"Summarizer Error: Failed to get summary from LLM. Error: {e}")
        traceback.print_exc()
        return f"Error: Could not generate summary. LLM Reason: {type(e).__name__} - {str(e)}"

# --- Note ---
# The LangChain Tool object for the summarizer ('summarizer_tool') is created
# dynamically within agent/planner.py because it needs the initialized LLM instance.