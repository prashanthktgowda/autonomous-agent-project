# autonomous-agent-project/tools/reporting_tool.py

import os
from pathlib import Path
from langchain.tools import Tool
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader # Useful for BytesIO images

# --- Matplotlib Imports ---
# Add error handling in case matplotlib is not installed correctly
try:
    import matplotlib
    matplotlib.use('Agg') # Use non-interactive backend suitable for scripts
    import matplotlib.pyplot as plt
    import io # Needed for saving chart to buffer
    MATPLOTLIB_AVAILABLE = True
    print("Reporting Tool: Matplotlib loaded successfully.")
except ImportError:
    print("Reporting Tool Warning: Matplotlib not found or failed to import. Chart generation will be disabled.")
    MATPLOTLIB_AVAILABLE = False
# --- End Matplotlib Imports ---


# Define the designated output directory relative to the project root
OUTPUT_DIR = Path("outputs").resolve() # Use resolve to get absolute path

# Ensure the output directory exists when the script loads
try:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
except OSError as e:
    print(f"[CRITICAL] Could not create mandatory output directory {OUTPUT_DIR}. Error: {e}")
    # Depending on desired behavior, you might want to raise the error here
    # raise


# --- Path Resolution Helper ---
def _is_path_within_output_dir(path_to_check: Path) -> bool:
    """Check if the resolved path is safely within the OUTPUT_DIR."""
    try:
        # Ensure the path exists or its parent exists before resolving fully
        # Resolving a non-existent path can sometimes behave unexpectedly
        base = path_to_check.parent if not path_to_check.exists() else path_to_check
        resolved_path = base.resolve()

        # The critical check: is the resolved path a subpath of OUTPUT_DIR?
        return resolved_path.is_relative_to(OUTPUT_DIR)
    except (ValueError, OSError, FileNotFoundError):
        # ValueError for different drives on Windows, OSError for permission issues,
        # FileNotFoundError could happen during resolution in edge cases
        return False

def _resolve_pdf_path(filename: str) -> Path | None:
    """Helper to safely resolve PDF output paths relative to OUTPUT_DIR."""
    # Clean the input path string - ensure it ends with .pdf
    cleaned_filename = filename.strip().replace("\\", "/").lstrip("/")
    if not cleaned_filename:
        print("Reporting Tool Error: PDF filename cannot be empty.")
        return None

    # Ensure filename doesn't contain directory traversal or start with /
    # Check path part if any (remove .pdf extension first for check)
    path_part = Path(cleaned_filename).stem
    if "/" in path_part or "\\" in path_part or ".." in path_part.split("/"):
         print(f"Reporting Tool Security Error: Invalid characters or directory traversal in filename '{filename}'. Use simple filenames.")
         return None

    # Ensure it has a .pdf extension, add if missing
    if not cleaned_filename.lower().endswith('.pdf'):
        cleaned_filename += '.pdf'

    # Create the full path relative to the OUTPUT_DIR, using only the safe filename part
    target_path = (OUTPUT_DIR / Path(cleaned_filename).name).resolve()

    # Final check: ensure the resolved path is still within OUTPUT_DIR
    if _is_path_within_output_dir(target_path):
         return target_path
    else:
        print(f"Reporting Tool Security Error: Resolved path '{target_path}' is outside the allowed directory '{OUTPUT_DIR}'. Input was '{filename}'.")
        return None


# --- Basic PDF Function ---
def create_basic_pdf_report(input_str: str) -> str:
    """
    Generates a simple PDF report containing only text (title and paragraphs).
    Input format: 'filename.pdf|Report Title|Report content'.
    Saves the PDF inside the 'outputs' directory.
    """
    print(f"Reporting Tool: Received request for basic PDF: '{input_str[:100]}...'")
    try:
        parts = input_str.split('|', 2)
        if len(parts) != 3:
            return "Error: Input must be in the format: 'filename.pdf|Report Title|Report content'."
        filename, title, content = parts[0].strip(), parts[1].strip(), parts[2].strip()

        if not filename or not title:
             return "Error: Filename and Report Title cannot be empty."

        target_path = _resolve_pdf_path(filename)
        if not target_path:
             return f"Error: Invalid or disallowed PDF filename/path '{filename}'."

        print(f"Reporting Tool: Generating basic PDF report at: {target_path}")
        doc = SimpleDocTemplate(str(target_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph(title, styles['h1']))
        story.append(Spacer(1, 0.2*inch))
        text_paragraphs = content.split('\n\n') # Split by double newline for paragraphs
        for para_text in text_paragraphs:
             cleaned_para = para_text.strip()
             if cleaned_para:
                 # Handle potential XML/HTML sensitive characters in ReportLab paragraphs
                 cleaned_para = cleaned_para.replace('&', '&').replace('<', '<').replace('>', '>')
                 story.append(Paragraph(cleaned_para, styles['Normal']))
                 story.append(Spacer(1, 0.1*inch))
        doc.build(story)
        print(f"Reporting Tool: Successfully created basic PDF report: {target_path}")
        return f"Successfully created basic PDF report at outputs/{target_path.name}" # Return relative path easier for agent
    except Exception as e:
        print(f"Reporting Tool Error: Failed to generate basic PDF '{filename}'. Error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error generating basic PDF report '{filename}'. Details: {str(e)}"


# --- IMPLEMENTED PDF with Chart Function ---
def create_pdf_with_chart(input_str: str) -> str:
    """
    Generates a PDF report with text and a simple bar chart using Matplotlib.
    Input format: 'filename.pdf|Report Title|Report text content|Chart Title|Comma,Separated,Labels|Comma,Separated,Values'
    Example: 'report.pdf|Sales|Sales grew.|Quarterly Sales|Q1,Q2,Q3|100,150,130'
    """
    if not MATPLOTLIB_AVAILABLE:
        return "Error: Matplotlib library is not available. Cannot generate chart."

    print(f"Reporting Tool: Received request for PDF with chart: '{input_str[:100]}...'")
    try:
        # --- Improved Input Validation ---
        parts = input_str.split('|')
        if len(parts) != 6:
            return (f"Error: Input validation failed. Expected exactly 6 parts separated by '|', but got {len(parts)}. "
                    "The required format is 'filename.pdf|Report Title|Report text content|Chart Title|Labels(comma-sep)|Values(comma-sep)'. "
                    f"Received input starting with: '{input_str[:150]}...'") # Show more of failing input

        filename, title, content, chart_title, labels_str, values_str = [p.strip() for p in parts]

        if not filename or not title or not chart_title:
             return "Error: Input validation failed. Filename, Report Title, and Chart Title cannot be empty."
        if not labels_str or not values_str:
             return "Error: Input validation failed. Chart labels and values strings cannot be empty. You must provide data for the chart."
        # --- End Improved Input Validation ---

        target_path = _resolve_pdf_path(filename)
        if not target_path:
            return f"Error: Invalid or disallowed PDF filename/path '{filename}'."

        print(f"Reporting Tool: Generating PDF with chart at: {target_path}")

        # --- Matplotlib Chart Generation (with value validation) ---
        img_buffer = None
        try:
            # Clean labels: remove empty strings that might result from trailing commas, etc.
            labels = [label.strip() for label in labels_str.split(',') if label.strip()]
            try:
                # Clean and convert values: remove empty strings, convert to float
                values = [float(v.strip()) for v in values_str.split(',') if v.strip()]
            except ValueError as ve:
                 print(f"Reporting Tool Error: Chart values could not be converted to numbers. Input values: '{values_str}'. Error: {ve}")
                 return f"Error: Chart values must be comma-separated numbers. Found non-numeric value in '{values_str}'."

            if not labels or not values:
                 return "Error: Chart labels and values cannot be empty after cleaning and validation."
            if len(labels) != len(values):
                return (f"Error: Input validation failed. Mismatch between number of chart labels ({len(labels)}: '{','.join(labels)}') "
                        f"and values ({len(values)}: '{','.join(map(str,values))}') after cleaning.")

            # --- Chart plotting code ---
            fig, ax = plt.subplots(figsize=(6, 4)) # Adjust figure size as needed
            bars = ax.bar(labels, values)
            ax.set_title(chart_title)
            ax.set_ylabel('Values') # Generic label, could be made part of input if needed
            # Add values on top of bars (optional, can clutter if many bars)
            # ax.bar_label(bars, fmt='{:,.0f}') # Format as integer with thousands separator
            plt.xticks(rotation=45, ha='right') # Rotate labels if long
            plt.tight_layout() # Adjust layout to prevent clipping

            # Save chart to a BytesIO buffer
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150) # Use PNG format, adjust DPI if needed
            img_buffer.seek(0)
            plt.close(fig) # Close the plot to free memory
            print("Reporting Tool: Chart generated successfully.")
            # --- End Chart plotting code ---

        except Exception as chart_e:
            print(f"Reporting Tool Error: Failed during chart generation phase. Error: {chart_e}")
            # Fallback: generate PDF without chart but include error message?
            # For now, just return the error.
            return f"Error: Failed during chart generation: {str(chart_e)}"
        # --- End Chart Generation ---

        # --- ReportLab PDF Generation ---
        doc = SimpleDocTemplate(str(target_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Add Title
        story.append(Paragraph(title, styles['h1']))
        story.append(Spacer(1, 0.2*inch))

        # Add Content
        text_paragraphs = content.split('\n\n')
        for para_text in text_paragraphs:
             cleaned_para = para_text.strip()
             if cleaned_para:
                 # Handle potential XML/HTML sensitive characters
                 cleaned_para = cleaned_para.replace('&', '&').replace('<', '<').replace('>', '>')
                 story.append(Paragraph(cleaned_para, styles['Normal']))
                 story.append(Spacer(1, 0.1*inch))

        story.append(Spacer(1, 0.2*inch))

        # Add Chart Image if generated
        if img_buffer:
             # Use ImageReader to handle BytesIO object
             chart_image = Image(img_buffer, width=6*inch, height=4*inch) # Adjust size as needed # Adjust size as needed
             chart_image.hAlign = 'CENTER'
             story.append(chart_image)
        else:
             # This case shouldn't happen now if chart generation errors are returned, but as fallback:
             story.append(Paragraph("Note: Chart data was provided, but chart image could not be generated.", styles['Italic']))

        doc.build(story)
        print(f"Reporting Tool: Successfully created PDF with chart (if generated): {target_path}")
        return f"Successfully created PDF report at outputs/{target_path.name}" # Return relative path
        # --- End ReportLab PDF Generation ---

    except Exception as e:
        print(f"Reporting Tool Error: Failed to generate PDF with chart '{filename}'. Error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error generating PDF report with chart '{filename}'. Details: {str(e)}"


# --- LangChain Tool Definitions (WITH UPDATED DESCRIPTIONS) ---

generate_basic_pdf_report_tool = Tool(
    name="Generate Basic PDF Report (Text Only)",
    func=create_basic_pdf_report,
    description=(
        "Use this tool ONLY when the request asks for a PDF report containing JUST TEXT (like summaries, analysis, or extracted information) and explicitly DOES NOT require any charts or visualizations. "
        "Input MUST be 3 parts separated by '|': 'filename.pdf|Report Title|Report text content'. "
        "Example: 'summary.pdf|Analysis Summary|The key findings indicate...'. "
        "Paragraphs in the content should be separated by a double newline (\\n\\n). "
        "The file will be saved inside the 'outputs' directory. "
        "DO NOT use this tool if a chart (bar chart, line chart, etc.) is needed in the PDF."
    ),
)

generate_pdf_with_chart_tool = Tool(
    name="Generate PDF Report with Bar Chart",
    func=create_pdf_with_chart,
    description=(
        "Use this tool ONLY when the request specifically asks for a PDF report that MUST include both text AND a simple bar chart visualization. "
        "Requires Matplotlib library. You MUST have ALREADY EXTRACTED the necessary data for the chart (labels and corresponding numerical values) from previous steps. "
        "The input MUST be formatted as **exactly 6 parts** separated by pipes '|': "
        "'filename.pdf|Report Title|Report text content|Chart Title|Comma,Separated,Labels|Comma,Separated,Values'. "
        "Example: 'sales_q1.pdf|Q1 Sales Report|Overall sales increased.|Sales by Month|Jan,Feb,Mar|50,65,80'. "
        "Labels and Values MUST be non-empty, comma-separated strings. Values must contain only numbers. There must be the same number of labels and values. "
        "The file will be saved inside the 'outputs' directory. Use simple filenames. "
        "If you do not have the specific label/value data for a chart, or if only a text PDF is needed, use the 'Generate Basic PDF Report (Text Only)' tool instead."
    ),
    # is_available=lambda: MATPLOTLIB_AVAILABLE # Optional check
)