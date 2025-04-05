# tools/reporting_tool.py (Corrected - Explicit Column Charting Tool + Basic Text Tool)

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
PANDAS_AVAILABLE = False
try:
    import matplotlib.pyplot as plt
    # Set backend explicitly if needed: plt.switch_backend('Agg')
    import pandas as pd
    from io import StringIO
    MATPLOTLIB_AVAILABLE = True
    PANDAS_AVAILABLE = True # Pandas needed for CSV parsing
    print("DEBUG [reporting_tool.py]: Matplotlib and Pandas loaded successfully.")
except ImportError as import_err:
    try: # Check separately for pandas as it might still be useful
        import pandas as pd
        from io import StringIO
        PANDAS_AVAILABLE = True
        print(f"WARNING [reporting_tool.py]: Matplotlib import failed ({import_err}). Charting disabled, Pandas available.")
    except ImportError:
         print(f"WARNING [reporting_tool.py]: Matplotlib AND Pandas import failed ({import_err}). Charting and CSV processing disabled.")
except Exception as e:
    print(f"WARNING [reporting_tool.py]: Error importing charting/data libs: {e}")
    traceback.print_exc()
# --- ---

# --- Define Output Directory & Path Resolver ---
try:
    OUTPUT_DIR = Path("outputs").resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"DEBUG [reporting_tool.py]: OUTPUT_DIR: {OUTPUT_DIR}")
except Exception as e:
    print(f"CRITICAL ERROR setting OUTPUT_DIR in reporting_tool.py: {e}")
    OUTPUT_DIR = Path("outputs") # Fallback

def _resolve_pdf_path(filename: str) -> Path | None:
    """Helper to safely resolve PDF output paths relative to OUTPUT_DIR."""
    if not isinstance(filename, str): print("PDF Path Err: Not string."); return None
    cleaned_filename = filename.strip().replace("\\", "/")
    if not cleaned_filename: print("PDF Path Err: Filename empty."); return None
    # Prevent directory structure in filename itself (allow in path before filename.pdf)
    if "/" in Path(cleaned_filename).name or "\\" in Path(cleaned_filename).name :
         print(f"PDF Path Err: Dir chars in final filename part '{Path(cleaned_filename).name}'."); return None
    if ".." in cleaned_filename.split("/"): print(f"PDF Path Err: '..' denied: '{cleaned_filename}'."); return None
    # Ensure name ends with .pdf
    if not cleaned_filename.lower().endswith('.pdf'): cleaned_filename += '.pdf'
    # Create full path, ensure only filename is used at the end to prevent tricks
    target_path = (OUTPUT_DIR / Path(cleaned_filename).name).resolve()
    # Final check: ensure the resolved path is still within OUTPUT_DIR
    try:
        if not target_path.is_relative_to(OUTPUT_DIR): print(f"PDF Path Security Err: Path '{target_path}' outside '{OUTPUT_DIR}'."); return None
    except ValueError: print(f"PDF Path Security Err: Cannot compare '{target_path}' and '{OUTPUT_DIR}'."); return None
    except Exception as e: print(f"PDF Path Err: Unexpected error resolving '{target_path}': {e}"); return None
    return target_path

# --- Basic Text PDF Report Function ---
def create_basic_pdf_report(input_str: str) -> str:
    """
    Generates a simple PDF report containing only text.
    Input format: 'filename.pdf|Report Title|Report content'
    """
    print(f"DEBUG [create_basic_pdf_report]: Request: '{input_str[:100]}...'")
    if not isinstance(input_str, str): return "Error: Input must be string."
    try:
        parts = input_str.split('|', 2)
        if len(parts) != 3: return "Error: Input for basic PDF needs 3 parts: 'filename.pdf|Title|Content'."
        filename, title, content = [p.strip() for p in parts]
        if not filename or not title: return "Error: Filename and Title required for basic PDF."

        target_path = _resolve_pdf_path(filename);
        if not target_path: return f"Error: Invalid/disallowed PDF path '{filename}'."

        print(f"Reporting Tool: Generating basic PDF: {target_path}")
        doc = SimpleDocTemplate(str(target_path), pagesize=letter); styles = getSampleStyleSheet(); story = []
        story.append(Paragraph(title, styles['h1'])); story.append(Spacer(1, 0.2*inch))
        # Ensure content is treated as a string before splitting
        content_str = str(content) if content is not None else ""
        for para_text in content_str.split('\n\n'): # Split by double newline
             cleaned_para = para_text.strip()
             if cleaned_para: story.append(Paragraph(cleaned_para, styles['Normal'])); story.append(Spacer(1, 0.1*inch))

        doc.build(story); print(f"Reporting Tool: Created basic PDF: {target_path}")
        relative_path_out = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else filename
        return f"Successfully created basic PDF report at {relative_path_out}"
    except Exception as e:
        print(f"Error basic PDF '{filename}': {e}"); traceback.print_exc();
        return f"Error generating basic PDF '{filename}': {str(e)}"


# --- CORRECTED Function for PDF with Chart (Handles CSV Data & SPECIFIED Columns) ---
def create_pdf_with_chart(input_str: str) -> str:
    """
    Generates a PDF report with text and a simple line chart from CSV data,
    using SPECIFIED columns for X and Y axes.
    Input format: 'filename.pdf|Report Title|Report text|Chart Title|X_COLUMN_NAME|Y_COLUMN_NAME|CSV_DATA'
    """
    if not MATPLOTLIB_AVAILABLE: return "Error: Charting libraries (Matplotlib/Pandas) not available."
    print(f"DEBUG [create_pdf_with_chart]: Request: '{input_str[:100]}...'")
    if not isinstance(input_str, str): return "Error: Input must be string."
    img_buffer = None; chart_generated = False; chart_error_msg = None; df = None; filename = "[unknown_pdf]"
    try:
        # --- Input Parsing (Expecting 7 parts) ---
        parts = input_str.split('|', 6);
        if len(parts) != 7: print(f"DEBUG [create_pdf_with_chart]: Incorrect parts ({len(parts)}), expected 7."); return ("Error: Input needs 7 parts: 'filename.pdf|RptTitle|RptText|ChartTitle|XCol|YCol|CSV_DATA'")
        filename, title, content, chart_title, x_col_name, y_col_name, csv_data_str = [p.strip() for p in parts]
        if not all([filename, title, chart_title, x_col_name, y_col_name, csv_data_str]): return "Error: Required parts missing (filename, titles, X/Y column names, CSV data)."
        # Clean prefixes
        if csv_data_str.startswith("CSV Data:"): csv_data_str = csv_data_str.split("\n", 1)[1]
        if csv_data_str.startswith("Success:"): csv_data_str = csv_data_str.split("\n", 1)[1]
        if not csv_data_str.strip(): return "Error: CSV data empty after cleaning prefixes."
        # --- End Input Parsing ---

        target_path = _resolve_pdf_path(filename);
        if not target_path: return f"Error: Invalid/disallowed PDF path '{filename}'."
        print(f"Reporting Tool: Generating PDF with chart: {target_path}")
        print(f"Reporting Tool: Plotting Column '{x_col_name}' vs '{y_col_name}'") # Log specified columns

        # --- Matplotlib Chart Generation ---
        try:
            csv_file_like = StringIO(csv_data_str); df = pd.read_csv(csv_file_like)
            if df.empty: raise ValueError("Parsed CSV empty.")
            if x_col_name not in df.columns: raise ValueError(f"X-col '{x_col_name}' not in CSV headers: {list(df.columns)}")
            if y_col_name not in df.columns: raise ValueError(f"Y-col '{y_col_name}' not in CSV headers: {list(df.columns)}")

            df_plot = df[[x_col_name, y_col_name]].copy();
            df_plot[y_col_name] = pd.to_numeric(df_plot[y_col_name], errors='coerce') # Convert Y to numeric
            original_rows = len(df_plot); df_plot.dropna(subset=[y_col_name], inplace=True) # Drop non-numeric Y rows
            if len(df_plot) < original_rows: print(f"Warn: Dropped {original_rows - len(df_plot)} non-numeric Y-rows ('{y_col_name}').")
            if df_plot.empty: raise ValueError(f"No valid numeric Y-data in '{y_col_name}'.")
            if len(df_plot) < 2: raise ValueError(f"Not enough valid data points ({len(df_plot)}) to plot '{y_col_name}'.")

            # --- Plotting ---
            print(f"DEBUG [Chart]: Plotting {len(df_plot)} rows.")
            plt.style.use('seaborn-v0_8-darkgrid'); fig, ax = plt.subplots(figsize=(8, 4))
            x_values_plot = df_plot[x_col_name] # Use the specified X column

            try: # Attempt to treat X as datetime for better axis labels
                 x_dates = pd.to_datetime(x_values_plot)
                 ax.plot(x_dates, df_plot[y_col_name], marker='.', linestyle='-', linewidth=1.5)
                 fig.autofmt_xdate(rotation=30, ha='right') # Format dates on axis
                 print("Reporting Tool: Plotted using datetime X-axis.")
            except (ValueError, TypeError, pd.errors.ParserError): # If X is not datetime-like
                 print("Reporting Tool Warning: Could not parse X-axis as dates/times, plotting as categories.")
                 x_strings = x_values_plot.astype(str) # Convert X to string
                 ax.plot(x_strings, df_plot[y_col_name], marker='.', linestyle='-', linewidth=1.5)
                 # --- Tick Limiting Logic (Corrected Scope) ---
                 tick_limit = 15 # Define limit *only* when plotting categories
                 if len(x_strings) > tick_limit:
                      # Calculate step based on number of unique categories if possible
                      unique_x = x_strings.unique()
                      step = max(1, len(unique_x) // tick_limit)
                      # Get current ticks/locations; set new ticks/labels based on step
                      current_ticks = range(len(unique_x)) # Use index range for categorical ticks
                      ax.set_xticks(current_ticks[::step]) # Set ticks based on index range and step
                      ax.set_xticklabels(unique_x[::step]) # Set labels corresponding to the selected ticks
                      print(f"DEBUG [Chart]: Limiting X-axis category ticks (step={step}).")
                 plt.xticks(rotation=45, ha='right', fontsize=8) # Rotate labels
                 # --- End Tick Limiting ---

            # General Formatting using specified titles/labels
            ax.set_title(chart_title, fontsize=14, weight='bold') # Use chart_title from input
            ax.set_xlabel(x_col_name, fontsize=10)
            ax.set_ylabel(y_col_name, fontsize=10)
            ax.grid(True, which='major', linestyle='--', linewidth=0.5)
            ax.tick_params(axis='both', which='major', labelsize=8)
            plt.tight_layout()

            # Save chart to buffer
            img_buffer = io.BytesIO(); plt.savefig(img_buffer, format='png', dpi=150); img_buffer.seek(0); chart_generated = True; print("Reporting Tool: Chart generated.")

        except pd.errors.EmptyDataError: chart_error_msg = "CSV data string invalid/empty."
        except ValueError as ve: chart_error_msg = f"Data validation error: {str(ve)[:150]}"
        except Exception as chart_e: chart_error_msg = f"Unexpected chart error: {type(chart_e).__name__} - {str(chart_e)[:150]}"
        finally: plt.close('all') # Ensure plot figure is closed
        if chart_error_msg: print(f"Error (Chart Gen): {chart_error_msg}"); traceback.print_exc();
        if img_buffer and not chart_generated: img_buffer.close(); img_buffer = None # Clean buffer if chart failed

        # --- Build PDF Document ---
        if img_buffer is None and chart_generated is False: # Check if chart generation failed
             # Provide more specific error if chart was intended but failed
             error_suffix = f" Chart generation failed: {chart_error_msg}" if chart_error_msg else " Chart could not be generated."
             # Fallback to text only? Or return error? Let's try fallback with note.
             print(f"WARNING [PDF Build]: Chart generation failed. Building text-only PDF.")
             content += f"\n\n<i>Note: Chart could not be generated. {chart_error_msg if chart_error_msg else ''}</i>" # Append note to text
             # Call the basic text builder helper
             pdf_built = _create_text_only_pdf(target_path, title, content)
             if pdf_built:
                 relative_path_out = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else filename
                 return f"Successfully created PDF report (text only, chart failed) at {relative_path_out}."
             else:
                 return f"Error: Chart generation failed AND text-only PDF build also failed for '{filename}'."

        # Proceed to build with chart if buffer exists
        elif img_buffer and chart_generated:
            try:
                doc = SimpleDocTemplate(str(target_path), pagesize=letter); styles = getSampleStyleSheet(); story = []
                story.append(Paragraph(title, styles['h1'])); story.append(Spacer(1, 0.2*inch))
                if content: # Add text content if provided
                     for para_text in content.split('\n\n'): cleaned_para = para_text.strip();
                     if cleaned_para: story.append(Paragraph(cleaned_para, styles['Normal'])); story.append(Spacer(1, 0.1*inch))
                story.append(Spacer(1, 0.2*inch)); chart_image = Image(img_buffer, width=7*inch, height=3.5*inch); story.append(chart_image);
                doc.build(story); print(f"Reporting Tool: Created PDF with chart: {target_path}")
                relative_path_out = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else filename
                return f"Successfully created PDF report with chart at {relative_path_out}"
            except Exception as pdf_build_e: print(f"Error building PDF with chart: {pdf_build_e}"); traceback.print_exc(); return f"Error building PDF '{filename}' after chart gen: {str(pdf_build_e)}"
            finally: img_buffer.close() # Ensure buffer closed
        else:
             # Should not happen if logic above is correct, but safeguard
             return f"Error: Internal state error building PDF for '{filename}' (no chart buffer but no explicit failure)."


    except Exception as e: # Catch-all for outer errors
        print(f"Error outer scope chart PDF '{filename}': {e}"); traceback.print_exc(); plt.close('all');
        return f"Error generating PDF report '{filename}': {str(e)}"

# --- LangChain Tool Definitions ---
generate_basic_pdf_report_tool = Tool(
    name="Generate Basic PDF Report (Text Only)",
    func=create_basic_pdf_report,
    description="Generates a professional PDF report containing ONLY text (title, paragraphs). Input: 'filename.pdf|Title|Content'. Paragraphs separated by double newline (\\n\\n). Saves to 'outputs'. Use for text summaries when no chart is needed or possible."
)

generate_pdf_with_chart_tool = Tool(
    name="Generate PDF Report with Line Chart",
    func=create_pdf_with_chart, # Use the corrected function
    description=(
        "Use this tool ONLY to generate a PDF report that includes both text paragraphs AND a line chart based on provided CSV data using SPECIFIED COLUMNS. "
        "**Requires Matplotlib/Pandas libraries.** Checks for specified columns and numeric Y-values. "
        "The input MUST be structured as exactly 7 parts separated by the pipe '|' character: "
        "'filename.pdf|Report Title|Report text content|Chart Title|X_COLUMN_NAME|Y_COLUMN_NAME|CSV_DATA'\n"
        "1. filename.pdf: Desired output filename (e.g., 'stock_analysis.pdf'). Must end in .pdf.\n"
        "2. Report Title: The main title for the PDF document.\n"
        "3. Report text content: Text paragraphs to include before the chart (use double newlines \\n\\n for paragraphs). Can be empty.\n"
        "4. Chart Title: The title displayed directly above the chart image.\n"
        "5. X_COLUMN_NAME: The exact, case-sensitive header name from the CSV data for the X-axis (e.g., 'Date', 'Year').\n"
        "6. Y_COLUMN_NAME: The exact, case-sensitive header name from the CSV data for the Y-axis (e.g., 'Close', 'Value'). Must contain numeric data.\n"
        "7. CSV_DATA: The complete multi-line CSV data string, including the header row. IMPORTANT: Remove 'Success:' or 'CSV Data:' prefixes first!\n"
        "Example Correct Input: 'stock_report.pdf|Stock Analysis|Price trend below.|TSLA Price|Date|Close|Date,Close\\n2024-01-01,200.5\\n2024-01-02,205.1'\n"
        "Saves PDF to 'outputs'. Returns success message or error if chart/PDF generation fails."
    )
)