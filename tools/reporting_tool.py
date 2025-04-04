# tools/reporting_tool.py (Corrected - Flexible Charting Implemented)

import os
from pathlib import Path
from langchain.tools import Tool
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import traceback
import io # Needed for saving chart to buffer

# --- Matplotlib Import and Check ---
MATPLOTLIB_AVAILABLE = False
try:
    import matplotlib.pyplot as plt
    # Set backend explicitly to Agg for non-interactive environments if needed, though often not necessary with savefig
    # plt.switch_backend('Agg')
    import pandas as pd # Need pandas to read the CSV string easily
    from io import StringIO # To read CSV string into pandas
    MATPLOTLIB_AVAILABLE = True
    print("DEBUG [reporting_tool.py]: Matplotlib and Pandas loaded successfully for charting.")
except ImportError:
    print("WARNING [reporting_tool.py]: Matplotlib or Pandas not found. PDF chart generation will not be possible.")
# --- ---

# --- Define Output Directory ---
try:
    OUTPUT_DIR = Path("outputs").resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"DEBUG [reporting_tool.py]: OUTPUT_DIR resolved to: {OUTPUT_DIR}")
except Exception as e:
    print(f"CRITICAL ERROR in reporting_tool.py: Failed to resolve or create OUTPUT_DIR. Error: {e}")
    OUTPUT_DIR = Path("outputs") # Fallback
# --- ---

def _resolve_pdf_path(filename: str) -> Path | None:
    """Helper to safely resolve PDF output paths relative to OUTPUT_DIR."""
    cleaned_filename = filename.strip().replace("\\", "/")
    if not cleaned_filename:
        print("PDF Path Error: Filename is empty.")
        return None
    # Basic check for directory characters in filename part
    if "/" in Path(cleaned_filename).stem or "\\" in Path(cleaned_filename).stem :
        print(f"PDF Path Error: Directory separators found within filename part '{Path(cleaned_filename).stem}'. Use simple filenames.")
        return None
    if ".." in cleaned_filename.split("/"): # Check again in full string just in case
        print(f"PDF Path Error: Path traversal '..' denied in '{cleaned_filename}'.")
        return None

    # Ensure it has a .pdf extension, add if missing
    if not cleaned_filename.lower().endswith('.pdf'):
        cleaned_filename += '.pdf'

    # Create the full path relative to the OUTPUT_DIR, using only filename part
    target_path = (OUTPUT_DIR / Path(cleaned_filename).name).resolve()

    # Final check: ensure the resolved path is still within OUTPUT_DIR
    try:
        if not target_path.is_relative_to(OUTPUT_DIR):
            print(f"PDF Path Security Error: Resolved path '{target_path}' is outside allowed directory '{OUTPUT_DIR}'.")
            return None
    except ValueError:
        print(f"PDF Path Security Error: Cannot compare path '{target_path}' with allowed directory '{OUTPUT_DIR}'.")
        return None
    except Exception as e:
        print(f"PDF Path Error: Unexpected error resolving path '{target_path}'. Error: {e}")
        return None

    return target_path

def create_basic_pdf_report(input_str: str) -> str:
    """
    Generates a simple PDF report containing only text.
    Input format: 'filename.pdf|Report Title|Report content'
    """
    print(f"DEBUG [create_basic_pdf_report]: Received request: '{input_str[:100]}...'")
    if not isinstance(input_str, str): return "Error: Input must be a string."
    try:
        parts = input_str.split('|', 2)
        if len(parts) != 3: return "Error: Input for basic PDF needs 3 parts: 'filename.pdf|Title|Content'."
        filename, title, content = parts[0].strip(), parts[1].strip(), parts[2].strip()

        target_path = _resolve_pdf_path(filename)
        if not target_path: return f"Error: Invalid or disallowed PDF filename/path '{filename}'."

        print(f"Reporting Tool: Generating basic PDF report at: {target_path}")
        doc = SimpleDocTemplate(str(target_path), pagesize=letter)
        styles = getSampleStyleSheet(); story = []
        story.append(Paragraph(title, styles['h1'])); story.append(Spacer(1, 0.2*inch))
        text_paragraphs = content.split('\n\n') # Split by double newline for paragraphs
        for para_text in text_paragraphs:
             cleaned_para = para_text.strip()
             if cleaned_para: story.append(Paragraph(cleaned_para, styles['Normal'])); story.append(Spacer(1, 0.1*inch))

        doc.build(story)
        print(f"Reporting Tool: Successfully created basic PDF report: {target_path}")
        # Return relative path from project root for clarity
        relative_path_out = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else filename
        return f"Successfully created PDF report at {relative_path_out}"

    except Exception as e:
        print(f"Reporting Tool Error: Failed basic PDF '{filename}'. Error: {e}")
        traceback.print_exc()
        return f"Error generating basic PDF '{filename}': {str(e)}"


# --- CORRECTED Function for PDF with Chart (Handles CSV Data & Column Selection) ---
def create_pdf_with_chart(input_str: str) -> str:
    """
    Generates a PDF report with text and a simple line chart from CSV data,
    using specified columns for X and Y axes.
    Input format: 'filename.pdf|Report Title|Report text|Chart Title|X_COLUMN_NAME|Y_COLUMN_NAME|CSV_DATA'
    """
    if not MATPLOTLIB_AVAILABLE:
        return "Error: Charting libraries (Matplotlib/Pandas) not available. Cannot generate PDF with chart."

    print(f"DEBUG [create_pdf_with_chart]: Received request: '{input_str[:100]}...'")
    if not isinstance(input_str, str): return "Error: Input must be a string."

    try:
        # --- Input Parsing (Expecting 7 parts) ---
        parts = input_str.split('|', 6) # Split max 6 times to get 7 parts
        if len(parts) != 7:
            print(f"DEBUG [create_pdf_with_chart]: Incorrect number of parts ({len(parts)}), expected 7.")
            return ("Error: Input for chart PDF needs exactly 7 parts separated by '|':\n"
                    "'filename.pdf|Report Title|Report text|Chart Title|X_COLUMN_NAME|Y_COLUMN_NAME|CSV_DATA'")
        # Assign parts after checking length
        filename, title, content, chart_title, x_col_name, y_col_name, csv_data_str = [p.strip() for p in parts]

        # Validate required parts are not empty
        if not all([filename, title, chart_title, x_col_name, y_col_name, csv_data_str]):
             return "Error: One or more required input parts (filename, titles, column names, csv_data) are empty."

        # Clean potential prefixes from CSV data string
        if csv_data_str.startswith("CSV Data:"): csv_data_str = csv_data_str.split("\n", 1)[1]
        if csv_data_str.startswith("Success:"): csv_data_str = csv_data_str.split("\n", 1)[1] # Assume data follows after first newline
        if not csv_data_str: return "Error: CSV data part is empty after cleaning prefixes."
        # --- End Input Parsing ---


        target_path = _resolve_pdf_path(filename)
        if not target_path:
             return f"Error: Invalid or disallowed PDF filename/path '{filename}'."

        print(f"Reporting Tool: Generating PDF with chart at: {target_path}")
        print(f"Reporting Tool: Plotting Column '{x_col_name}' vs '{y_col_name}'")

        # --- Matplotlib Chart Generation from CSV String ---
        img_buffer = None # Initialize buffer
        try:
            csv_file_like = StringIO(csv_data_str)
            df = pd.read_csv(csv_file_like)

            # --- Data Validation ---
            if df.empty: return "Error: Parsed CSV data is empty. Cannot generate chart."
            if x_col_name not in df.columns: return f"Error: Specified X-axis column '{x_col_name}' not found in CSV headers: {list(df.columns)}"
            if y_col_name not in df.columns: return f"Error: Specified Y-axis column '{y_col_name}' not found in CSV headers: {list(df.columns)}"

            # Ensure Y column is numeric, attempting conversion
            try:
                # Make a copy to avoid SettingWithCopyWarning if df is used later
                df_plot = df.copy()
                # Convert relevant columns before processing
                if x_col_name != y_col_name: # Avoid converting the same column twice if user specified same for X/Y
                     df_plot[x_col_name] = pd.to_numeric(df_plot[x_col_name], errors='ignore') # Try converting X too, ignore if fails (might be dates/strings)
                df_plot[y_col_name] = pd.to_numeric(df_plot[y_col_name], errors='coerce') # Coerce Y errors to NaN
                original_rows = len(df_plot)
                df_plot.dropna(subset=[y_col_name], inplace=True) # Drop rows where Y is not numeric
                if len(df_plot) < original_rows:
                     print(f"Reporting Tool Warning: Dropped {original_rows - len(df_plot)} non-numeric Y-value rows for column '{y_col_name}'.")
                if df_plot.empty: return f"Error: No valid numeric data found in Y-axis column '{y_col_name}' after cleaning."
            except KeyError as ke:
                 return f"Error: Column '{ke}' not found during numeric conversion preparation."
            except Exception as conv_err:
                 return f"Error converting Y-axis column '{y_col_name}' to numeric: {conv_err}"


            # --- Plotting ---
            print(f"DEBUG [create_pdf_with_chart]: Plotting {len(df_plot)} rows.")
            plt.style.use('seaborn-v0_8-darkgrid')
            fig, ax = plt.subplots(figsize=(8, 4)) # Width, Height in inches

            # Handle potential date conversion for X-axis formatting for nicer plots
            x_values_for_plot = df_plot[x_col_name]
            try:
                 # Attempt conversion, but plot original strings if it fails
                 x_dates = pd.to_datetime(df_plot[x_col_name])
                 ax.plot(x_dates, df_plot[y_col_name], marker='.', linestyle='-', linewidth=1.5)
                 fig.autofmt_xdate(rotation=30, ha='right') # Auto-format dates, rotate slightly
                 print("Reporting Tool: Plotted using auto-formatted datetime X-axis.")
            except (ValueError, TypeError, pd.errors.ParserError):
                 print("Reporting Tool Warning: Could not parse X-axis as dates/times, plotting as categories.")
                 # Plot using original (potentially string) values if date conversion fails
                 ax.plot(x_values_for_plot.astype(str), df_plot[y_col_name], marker='.', linestyle='-', linewidth=1.5)
                 # Limit number of ticks if many categories, and rotate
                 tick_limit = 15
                 if len(x_values_for_plot) > tick_limit:
                      step = max(1, len(x_values_for_plot) // tick_limit)
                      ax.set_xticks(ax.get_xticks()[::step])
                 plt.xticks(rotation=45, ha='right', fontsize=8)

            # Formatting
            ax.set_title(chart_title, fontsize=14, weight='bold')
            ax.set_xlabel(x_col_name, fontsize=10)
            ax.set_ylabel(y_col_name, fontsize=10)
            ax.grid(True, which='major', linestyle='--', linewidth=0.5)
            ax.tick_params(axis='both', which='major', labelsize=8)
            plt.tight_layout() # Adjust layout

            # Save chart to buffer
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150)
            img_buffer.seek(0)
            plt.close(fig) # IMPORTANT: Close plot to free memory
            print("Reporting Tool: Chart generated successfully.")
            # --- End Chart Generation ---

        except pd.errors.EmptyDataError:
             return f"Error: Provided CSV data string appears empty or invalid for chart generation."
        except Exception as chart_e:
            print(f"Reporting Tool Error: Failed during chart generation phase. Error: {chart_e}")
            traceback.print_exc()
            # Ensure buffer is closed if created
            if img_buffer: img_buffer.close()
            plt.close('all') # Close any potentially lingering plots
            return f"Error generating chart from provided data: {str(chart_e)}"


        # --- Build PDF Document ---
        if img_buffer is None: # Check if chart generation failed before buffer assignment
            return "Error: Chart could not be generated, cannot create PDF with chart."

        try:
            doc = SimpleDocTemplate(str(target_path), pagesize=letter)
            styles = getSampleStyleSheet(); story = []
            story.append(Paragraph(title, styles['h1'])); story.append(Spacer(1, 0.2*inch))
            text_paragraphs = content.split('\n\n')
            for para_text in text_paragraphs:
                 cleaned_para = para_text.strip()
                 if cleaned_para: story.append(Paragraph(cleaned_para, styles['Normal'])); story.append(Spacer(1, 0.1*inch))
            story.append(Spacer(1, 0.2*inch))
            chart_image = Image(img_buffer, width=7*inch, height=3.5*inch) # Adjust size as needed
            story.append(chart_image)
            doc.build(story)
            print(f"Reporting Tool: Successfully created PDF with chart: {target_path}")
            relative_path_out = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else filename
            return f"Successfully created PDF report with chart at {relative_path_out}"
        except Exception as pdf_build_e:
             print(f"Reporting Tool Error: Failed during PDF build phase. Error: {pdf_build_e}")
             traceback.print_exc()
             return f"Error building PDF document '{filename}' after chart generation: {str(pdf_build_e)}"
        finally:
             # Ensure buffer is closed after use
             if img_buffer: img_buffer.close()


    except Exception as e:
        # Catch-all for unexpected errors during input parsing or outer function scope
        print(f"Reporting Tool Error: Unexpected failure in create_pdf_with_chart for '{filename}'. Error: {e}")
        traceback.print_exc()
        # Ensure plot is closed if error happened before explicit close
        plt.close('all')
        return f"Error generating PDF report with chart '{filename}': {str(e)}"

# --- LangChain Tool Definitions ---
# (generate_basic_pdf_report_tool definition remains the same)
generate_basic_pdf_report_tool = Tool(
    name="Generate Basic PDF Report (Text Only)",
    func=create_basic_pdf_report,
    description="""
    Use this tool to generate a professional PDF report containing ONLY text (title and paragraphs).
    Input MUST be the desired PDF filename (e.g., 'analysis_report.pdf'), a pipe '|', the report title, another pipe '|', and the main text content.
    Paragraphs in the content should be separated by double newline (\\n\\n).
    Example: 'report.pdf|Analysis|First paragraph...\\n\\nSecond paragraph...'
    Saves the file inside the 'outputs' directory. Cannot include charts or complex formatting.
    """,
)

# --- CORRECTED LangChain Tool Definition for Charting PDF ---
generate_pdf_with_chart_tool = Tool(
    name="Generate PDF Report with Line Chart",
    func=create_pdf_with_chart,
    description="""
    Use this tool to generate a PDF report containing text AND a line chart created from CSV data using specified columns.
    **Requires Matplotlib/Pandas libraries.** Checks for specified columns and numeric Y-values.
    Input MUST be exactly 7 parts separated by pipes '|':
    'filename.pdf|Report Title|Report text content|Chart Title|X_COLUMN_NAME|Y_COLUMN_NAME|CSV_DATA'
    - filename.pdf: The desired output filename ending in .pdf (e.g., 'stock_analysis.pdf').
    - Report Title: The main title for the PDF document.
    - Report text content: Text paragraphs to include before the chart (use double newlines \\n\\n for paragraphs). Can be empty if only chart is needed.
    - Chart Title: The title to display directly above the chart image.
    - X_COLUMN_NAME: The exact header name from the CSV data to use for the X-axis (e.g., 'Date', 'Year', 'Category'). Case-sensitive.
    - Y_COLUMN_NAME: The exact header name from the CSV data to use for the Y-axis (e.g., 'Close', 'Value', 'Installations'). The tool expects this column to contain numeric data. Case-sensitive.
    - CSV_DATA: A multi-line string containing comma-separated values, starting with headers, typically obtained from the 'Get Stock Historical Data' or 'Extract Tables from Webpage' tool. **Remove any 'Success:' or 'CSV Data:' prefixes from the data before passing it here.**
    Example: 'stock_report.pdf|Stock Analysis|Prices shown below.|Stock Price Trend|Date|Close|Date,Open,High,Low,Close,Volume\\n2023-01-01,150.0,...\\n2023-01-02,152.1,...'
    Saves the file inside the 'outputs' directory. Returns a success message indicating the saved path or an error message if generation fails.
    """,
)