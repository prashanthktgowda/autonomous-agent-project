# tools/data_processing_tool.py (NEW FILE)

import pandas as pd
from io import StringIO
from langchain.tools import Tool
import traceback

# --- Pandas Check ---
PANDAS_AVAILABLE = False
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    print("DEBUG [data_processing_tool.py]: Pandas loaded.")
except ImportError:
    print("WARNING [data_processing_tool.py]: Pandas not found. Data processing tool will not function.")

# --- Core Processing Functions ---

def get_csv_summary_statistics(csv_data_str: str) -> str:
    """
    Calculates and returns basic summary statistics (count, mean, std, min, 25%, 50%, 75%, max)
    for the numeric columns of the provided CSV data using pandas describe().
    Input: A multi-line string containing CSV data, starting with headers.
    Returns: A string containing the summary statistics or an error message.
    """
    if not PANDAS_AVAILABLE: return "Error: Pandas library not available for data processing."
    print("DEBUG [Data Processing]: Received request for summary statistics.")

    # Clean potential prefixes from input data
    if csv_data_str.startswith("CSV Data:"): csv_data_str = csv_data_str.split("\n", 1)[1]
    if csv_data_str.startswith("Success:"): csv_data_str = csv_data_str.split("\n", 1)[1]
    if not csv_data_str: return "Error: Input CSV data string is empty."

    try:
        csv_file_like = StringIO(csv_data_str)
        df = pd.read_csv(csv_file_like)

        if df.empty: return "Error: Parsed CSV data is empty."

        # Select only numeric columns for describe()
        numeric_df = df.select_dtypes(include='number')

        if numeric_df.empty:
            return "Error: No numeric columns found in the provided CSV data to describe."

        # Get summary statistics
        summary = numeric_df.describe()

        # Format the summary for better readability as a string
        summary_str = summary.to_string()

        print("DEBUG [Data Processing]: Successfully generated summary statistics.")
        return f"Summary Statistics for Numeric Columns:\n{summary_str}"

    except pd.errors.EmptyDataError:
         return f"Error: Provided CSV data string appears empty or invalid after cleaning prefixes."
    except Exception as e:
        print(f"Data Processing Error (describe): {e}")
        traceback.print_exc()
        return f"Error calculating summary statistics: {str(e)}"


# --- LangChain Tool Definitions ---

describe_csv_tool = Tool(
    name="Summarize CSV Data Statistics",
    func=get_csv_summary_statistics,
    description=(
        "Use this tool to calculate basic summary statistics (count, mean, standard deviation, min, max, quartiles) "
        "for the NUMERIC columns in provided CSV data. "
        "Input MUST be a multi-line string containing the CSV data, including a header row. "
        "The CSV data might come from the 'Get Stock Historical Data' or 'Extract Tables from Webpage' tools. "
        "Remove any 'Success:' or 'CSV Data:' prefixes before passing the data here. "
        "Example Input:\nHeader1,NumericHeader2\\nValueA,10\\nValueB,25\\nValueC,15 "
        "Output is a string containing the summary statistics table or an error message."
    ),
)

# --- Optional: Add more processing tools here ---
# e.g., Filter rows based on column value, select specific columns, calculate simple correlations
# def filter_csv(csv_data_and_filter: str) -> str:
#     # Input: "COLUMN_NAME|OPERATOR|VALUE|CSV_DATA" (e.g., "Age|>|30|Name,Age\n...")
#     # Use pandas query() or boolean indexing
#     pass
# filter_csv_tool = Tool(...)