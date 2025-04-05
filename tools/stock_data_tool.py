# tools/stock_data_tool.py (Return Raw CSV on Success)

import yfinance as yf
import pandas as pd
from langchain.tools import Tool
from io import StringIO
from pathlib import Path
import traceback

# --- Define Output Directory ---
try:
    OUTPUT_DIR = Path("outputs").resolve(); OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"DEBUG [stock_data_tool.py]: OUTPUT_DIR: {OUTPUT_DIR}")
except Exception as e: print(f"CRITICAL ERROR setting OUTPUT_DIR: {e}"); OUTPUT_DIR = Path("outputs")
# --- ---

def get_stock_history(ticker_and_period: str) -> str:
    """ Fetches stock history. Input: 'TICKER|PERIOD'. Returns RAW CSV DATA string on success or 'Error:...'. """
    print(f"DEBUG [Stock Tool]: Request: '{ticker_and_period}'")
    # ... (Input validation remains the same) ...
    if not isinstance(ticker_and_period, str) or '|' not in ticker_and_period: return "Error: Invalid input format. Needs 'TICKER_SYMBOL|PERIOD'."
    try:
        parts=ticker_and_period.split('|',1); ticker_symbol=parts[0].strip().upper(); period=parts[1].strip().lower()
        if not ticker_symbol: return "Error: Ticker symbol empty."
        valid_periods=['1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max']
        if period not in valid_periods: return f"Error: Invalid period '{period}'. Valid: {', '.join(valid_periods)}"

        print(f"DEBUG [Stock Tool]: Fetching: {ticker_symbol}, Period: {period}")
        stock=yf.Ticker(ticker_symbol); hist=stock.history(period=period)
        if hist.empty: guidance=" Check ticker (use '.NS' for NSE India like 'MRF.NS')." if ".NS" not in ticker_symbol else ""; return f"Error: No data found for '{ticker_symbol}' period '{period}'.{guidance}"

        available_cols=[col for col in ['Open','High','Low','Close','Volume'] if col in hist.columns]
        if not available_cols or 'Close' not in available_cols: return f"Error: Essential columns (esp. 'Close') missing for '{ticker_symbol}'."
        hist=hist[available_cols].reset_index()
        date_col = 'Date' if 'Date' in hist.columns else 'Datetime' if 'Datetime' in hist.columns else None
        if date_col: hist.rename(columns={date_col:'Date'},inplace=True); hist['Date']=pd.to_datetime(hist['Date']).dt.strftime('%Y-%m-%d')

        max_rows=150; original_rows=len(hist)
        if original_rows>max_rows: print(f"DEBUG [Stock]: Truncating {original_rows} rows to {max_rows}."); hist=hist.tail(max_rows)

        output_buffer=StringIO(); hist.to_csv(output_buffer, index=False, date_format='%Y-%m-%d'); csv_data=output_buffer.getvalue(); output_buffer.close()
        print(f"DEBUG [Stock]: Fetched {len(hist)} rows for {ticker_symbol}.")

        # --- MODIFIED RETURN ---
        # Return *only* the CSV data string on success
        return csv_data
        # --- END MODIFICATION ---

    except Exception as e:
        error_name=type(e).__name__; print(f"Stock Tool Error: {error_name} - {e}"); traceback.print_exc()
        # Ensure error messages start clearly with "Error:"
        return f"Error: Could not fetch stock data for '{ticker_and_period}'. Reason: {error_name} - {str(e)}. Check symbol/period/network."

# --- Tool Definition (Updated Description) ---
stock_data_tool = Tool(
    name="Get Stock Historical Data",
    func=get_stock_history,
    description=(
        "Use this tool to fetch historical stock market data (like Date, Open, High, Low, Close, Volume) for a specific stock ticker symbol over a standard period. "
        "Input MUST be a string in the exact format 'TICKER_SYMBOL|PERIOD'. "
        "Use standard ticker symbols (e.g., 'AAPL', 'GOOGL', 'MRF.NS' for NSE India). "
        "Valid PERIOD options: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'. "
        "On success, the tool returns ONLY the raw CSV data string (potentially truncated). " # <-- UPDATED DESCRIPTION
        "On failure, it returns an error message starting with 'Error:'. " # <-- UPDATED DESCRIPTION
        "Use the returned CSV data string directly as input for analysis or for the 'Generate PDF Report with Line Chart' tool."
    ),
    return_direct=False
)