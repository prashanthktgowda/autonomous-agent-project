import os
from pathlib import Path
from langchain.tools import Tool
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image # Added Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
# Import matplotlib only if generating charts - keep commented if not used initially
# import matplotlib.pyplot as plt
# import io # Needed for saving chart to buffer

# Define the designated output directory relative to the project root
OUTPUT_DIR = Path("outputs").resolve() # Use resolve to get absolute path

# Ensure the output directory exists when the script loads
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_pdf_path(filename: str) -> Path | None:
    """Helper to safely resolve PDF output paths relative to OUTPUT_DIR."""
    # Clean the input path string - ensure it ends with .pdf
    cleaned_filename = filename.strip().replace("\\", "/")
    if not cleaned_filename:
        print("Reporting Tool Error: PDF filename cannot be empty.")
        return None

    # Ensure filename doesn't contain directory traversal or start with /
    if "/" in cleaned_filename[:-4] or ".." in cleaned_filename: # Check path part if any
         print(f"Reporting Tool Security Error: Invalid characters or directory traversal in filename '{filename}'. Use simple filenames.")
         return None

    # Ensure it has a .pdf extension, add if missing
    if not cleaned_filename.lower().endswith('.pdf'):
        cleaned_filename += '.pdf'

    # Create the full path relative to the OUTPUT_DIR
    target_path = (OUTPUT_DIR / Path(cleaned_filename).name).resolve() # Use only filename part

    # Final check: ensure the resolved path is still within OUTPUT_DIR
    try:
        if not target_path.is_relative_to(OUTPUT_DIR):
            print(f"Reporting Tool Security Error: Resolved path '{target_path}' is outside the allowed directory '{OUTPUT_DIR}'.")
            return None
    except ValueError:
        print(f"Reporting Tool Security Error: Cannot compare path '{target_path}' with allowed directory '{OUTPUT_DIR}'. Access denied.")
        return None

    return target_path


def create_basic_pdf_report(input_str: str) -> str:
    """
    Generates a simple PDF report with a title and paragraphs of text.
    Input format: 'filename.pdf|Report Title|Report content with paragraphs separated by double newlines.'
    Saves the PDF inside the 'outputs' directory.
    """
    print(f"Reporting Tool: Received request for basic PDF: '{input_str[:100]}...'")
    try:
        parts = input_str.split('|', 2)
        if len(parts) != 3:
            return "Error: Input must be in the format: 'filename.pdf|Report Title|Report content'."
        filename, title, content = parts[0].strip(), parts[1].strip(), parts[2].strip()

        target_path = _resolve_pdf_path(filename)
        if not target_path:
             return f"Error: Invalid or disallowed PDF filename/path '{filename}'."

        print(f"Reporting Tool: Generating PDF report at: {target_path}")

        doc = SimpleDocTemplate(str(target_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Add Title
        story.append(Paragraph(title, styles['h1']))
        story.append(Spacer(1, 0.2*inch)) # Add space

        # Add Content (split into paragraphs by double newline)
        text_paragraphs = content.split('\n\n')
        for para_text in text_paragraphs:
             cleaned_para = para_text.strip()
             if cleaned_para:
                 story.append(Paragraph(cleaned_para, styles['Normal']))
                 story.append(Spacer(1, 0.1*inch)) # Space between paragraphs

        doc.build(story)
        print(f"Reporting Tool: Successfully created basic PDF report: {target_path}")
        return f"Successfully created PDF report at {target_path}"

    except Exception as e:
        print(f"Reporting Tool Error: Failed to generate PDF '{filename}'. Error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error generating PDF report '{filename}'. Details: {str(e)}"

# --- Placeholder for PDF with Chart (Advanced Test Case) ---
# def create_pdf_with_chart(input_str: str) -> str:
#     """
#     Generates a PDF report with text and a simple chart (e.g., bar chart).
#     Input format: 'filename.pdf|Report Title|Report text content|Chart Title|Label1,Label2|Value1,Value2'
#     """
#     print(f"Reporting Tool: Received request for PDF with chart: '{input_str[:100]}...'")
#     try:
#         parts = input_str.split('|', 5)
#         if len(parts) != 6:
#             return "Error: Input for chart PDF needs 6 parts: 'filename|title|content|chart_title|labels|values'"
#         filename, title, content, chart_title, labels_str, values_str = [p.strip() for p in parts]
#
#         target_path = _resolve_pdf_path(filename)
#         if not target_path:
#             return f"Error: Invalid or disallowed PDF filename/path '{filename}'."
#
#         print(f"Reporting Tool: Generating PDF with chart at: {target_path}")
#
#         # --- Matplotlib Chart Generation ---
#         try:
#             labels = labels_str.split(',')
#             values = [float(v) for v in values_str.split(',')]
#             if len(labels) != len(values):
#                 return "Error: Mismatch between number of chart labels and values."
#
#             fig, ax = plt.subplots()
#             ax.bar(labels, values)
#             ax.set_title(chart_title)
#             ax.set_ylabel('Values') # Customize as needed
#             plt.xticks(rotation=45, ha='right') # Improve label readability
#             plt.tight_layout() # Adjust layout
#
#             # Save chart to a BytesIO buffer
#             img_buffer = io.BytesIO()
#             plt.savefig(img_buffer, format='png', dpi=300)
#             img_buffer.seek(0)
#             plt.close(fig) # Close the plot to free memory
#             print("Reporting Tool: Chart generated successfully.")
#         except Exception as chart_e:
#             print(f"Reporting Tool Error: Failed to generate chart. Error: {chart_e}")
#             return f"Error generating chart: {str(chart_e)}"
#         # --- End Chart Generation ---
#
#         doc = SimpleDocTemplate(str(target_path), pagesize=letter)
#         styles = getSampleStyleSheet()
#         story = []
#
#         # Add Title
#         story.append(Paragraph(title, styles['h1']))
#         story.append(Spacer(1, 0.2*inch))
#
#         # Add Content
#         text_paragraphs = content.split('\n\n')
#         for para_text in text_paragraphs:
#              cleaned_para = para_text.strip()
#              if cleaned_para:
#                  story.append(Paragraph(cleaned_para, styles['Normal']))
#                  story.append(Spacer(1, 0.1*inch))
#
#         story.append(Spacer(1, 0.2*inch))
#
#         # Add Chart Image
#         chart_image = Image(img_buffer, width=5*inch, height=3*inch) # Adjust size as needed
#         story.append(chart_image)
#
#         doc.build(story)
#         print(f"Reporting Tool: Successfully created PDF with chart: {target_path}")
#         return f"Successfully created PDF report with chart at {target_path}"
#
#     except Exception as e:
#         print(f"Reporting Tool Error: Failed to generate PDF with chart '{filename}'. Error: {e}")
#         import traceback
#         traceback.print_exc()
#         return f"Error generating PDF report with chart '{filename}'. Details: {str(e)}"
# --- End Placeholder ---


# --- LangChain Tool Definition ---

generate_pdf_report_tool = Tool(
    name="Generate Basic PDF Report",
    func=create_basic_pdf_report,
    description="""
    Use this tool to generate a professional PDF report containing only text (title and paragraphs).
    Input MUST be the desired PDF filename (e.g., 'analysis_report.pdf'), a pipe '|', the report title, another pipe '|', and the main text content.
    Paragraphs in the content should be separated by a double newline (\n\n).
    Example: 'renewable_energy_trends.pdf|Renewable Energy Analysis|Here are the key findings...\n\nFurther analysis shows...'
    The file will be saved inside the 'outputs' directory. Use simple filenames without path traversal.
    Use this for the final step when a formatted document is required. Chart generation requires a different tool/function.
    """,
)

# --- Optional: Tool for PDF with Chart ---
# generate_pdf_with_chart_tool = Tool(
#     name="Generate PDF Report with Chart",
#     func=create_pdf_with_chart,
#     description="""
#     Use this tool to generate a PDF report containing text AND a simple bar chart.
#     Input MUST be 6 parts separated by pipes '|':
#     'filename.pdf|Report Title|Report text content|Chart Title|Label1,Label2,Label3|Value1,Value2,Value3'
#     Example: 'sales_report.pdf|Q3 Sales|Sales were strong...|Quarterly Sales|Q1,Q2,Q3|150,220,190'
#     Labels and Values for the chart must be comma-separated, with the same number of items.
#     The file will be saved inside the 'outputs' directory. Use simple filenames.
#     """,
# )
# Remember to add generate_pdf_with_chart_tool to the tools list in planner.py if you implement and uncomment it.
# Also, ensure matplotlib is installed (`pip install matplotlib`) and uncomment its imports above.