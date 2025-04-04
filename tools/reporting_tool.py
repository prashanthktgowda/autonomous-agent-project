import os
from pathlib import Path
from langchain.tools import Tool
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import traceback
import io

# --- Matplotlib Import and Check ---
MATPLOTLIB_AVAILABLE = False
try:
    import matplotlib.pyplot as plt
    import pandas as pd
    from io import StringIO
    import dateutil.parser
    MATPLOTLIB_AVAILABLE = True
    print("DEBUG [reporting_tool.py]: Matplotlib, Pandas, dateutil loaded for charting.")
except ImportError as import_err:
    print(f"WARNING [reporting_tool.py]: Import Error - {import_err}. PDF chart generation disabled.")
except Exception as e:
    print(f"WARNING [reporting_tool.py]: Error importing charting libs: {e}")
    traceback.print_exc()
# --- ---

# --- Define Output Directory & Path Resolver ---
try:
    OUTPUT_DIR = Path("outputs").resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"DEBUG [reporting_tool.py]: OUTPUT_DIR: {OUTPUT_DIR}")
except Exception as e:
    print(f"CRITICAL ERROR setting OUTPUT_DIR: {e}")
    OUTPUT_DIR = Path("outputs")

def _resolve_pdf_path(filename: str) -> Path | None:
    cleaned_filename = filename.strip().replace("\\", "/")
    if not cleaned_filename:
        return None
    if "/" in Path(cleaned_filename).stem or "\\" in Path(cleaned_filename).stem:
        return None
    if ".." in cleaned_filename.split("/"):
        return None
    if not cleaned_filename.lower().endswith('.pdf'):
        cleaned_filename += '.pdf'
    target_path = (OUTPUT_DIR / Path(cleaned_filename).name).resolve()
    try:
        if not target_path.is_relative_to(OUTPUT_DIR):
            return None
    except:
        return None
    return target_path

# --- Basic Text PDF Report Function ---
def create_basic_pdf_report(input_str: str) -> str:
    print(f"DEBUG [create_basic_pdf_report]: Request: '{input_str[:100]}...'")
    if not isinstance(input_str, str):
        return "Error: Input must be string."
    try:
        parts = input_str.split('|', 2)
        if len(parts) != 3:
            return "Error: Input needs 'filename.pdf|Title|Content'."
        filename, title, content = [p.strip() for p in parts]
        if not filename or not title:
            return "Error: Filename/Title required."
        target_path = _resolve_pdf_path(filename)
        if not target_path:
            return f"Error: Invalid path '{filename}'."
        doc = SimpleDocTemplate(str(target_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph(title, styles['h1']))
        story.append(Spacer(1, 0.2 * inch))
        for para_text in content.split('\n\n'):
            cleaned_para = para_text.strip()
            if cleaned_para:
                story.append(Paragraph(cleaned_para, styles['Normal']))
                story.append(Spacer(1, 0.1 * inch))
        doc.build(story)
        print(f"Reporting: Created basic PDF: {target_path}")
        relative_path_out = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else filename
        return f"Successfully created PDF report at {relative_path_out}"
    except Exception as e:
        print(f"Error basic PDF '{filename}': {e}")
        traceback.print_exc()
        return f"Error basic PDF '{filename}': {str(e)}"

# --- NEW Unified Charting Function ---
def generate_pdf_report_with_auto_chart(input_str: str) -> str:
    if not MATPLOTLIB_AVAILABLE:
        print("WARNING [Auto Chart]: Charting libs missing. Falling back to text-only PDF.")
        parts_fallback = input_str.split('|', 2)
        if len(parts_fallback) >= 3:
            basic_input = '|'.join(parts_fallback[:3])
            return create_basic_pdf_report(basic_input) + " (Note: Charting libraries unavailable, chart omitted)"
        else:
            return "Error: Charting libraries unavailable AND input format invalid for basic text report."

    print(f"DEBUG [Auto Chart]: Received request: '{input_str[:100]}...'")
    if not isinstance(input_str, str):
        return "Error: Input must be string."

    img_buffer = None
    chart_title = "Data Visualization"
    chart_generated = False
    filename = "[unknown]"

    try:
        parts = input_str.split('|', 3)
        num_parts = len(parts)

        if num_parts < 3:
            return "Error: Input needs at least 3 parts: 'filename.pdf|Report Title|Report text content'"

        filename, title, content = [p.strip() for p in parts[:3]]
        csv_data_str = parts[3].strip() if num_parts == 4 else None

        if not filename or not title:
            return "Error: Filename and Report Title required."

        target_path = _resolve_pdf_path(filename)
        if not target_path:
            return f"Error: Invalid/disallowed PDF path '{filename}'."

        print(f"Reporting Tool: Generating Auto-Chart PDF: {target_path}")

        if csv_data_str:
            print("DEBUG [Auto Chart]: CSV data provided, attempting chart generation.")
            if csv_data_str.startswith("CSV Data:"):
                csv_data_str = csv_data_str.split("\n", 1)[1]
            if csv_data_str.startswith("Success:"):
                csv_data_str = csv_data_str.split("\n", 1)[1]
            csv_data_str = csv_data_str.strip()

            if not csv_data_str:
                print("DEBUG [Auto Chart]: CSV data was empty after cleaning.")
                content += "\n\n(Note: Provided CSV data was empty, chart omitted.)"
            else:
                try:
                    csv_file_like = StringIO(csv_data_str)
                    df = pd.read_csv(csv_file_like)
                    if df.empty or len(df.columns) < 2:
                        raise ValueError("Parsed CSV empty or has less than 2 columns.")

                    x_col = None
                    y_col = None
                    chart_type = 'line'

                    date_like_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['date', 'year', 'time', 'period'])]
                    numeric_cols = df.select_dtypes(include='number').columns

                    if date_like_cols:
                        x_col = date_like_cols[0]
                        y_col_candidates = [c for c in numeric_cols if c != x_col]
                        if y_col_candidates:
                            y_col = y_col_candidates[0]
                            chart_type = 'line'
                            chart_title = f"{y_col} over {x_col}"
                            print(f"DEBUG [Auto Chart]: Inferred LINE chart: X='{x_col}', Y='{y_col}'")
                        else:
                            print("DEBUG [Auto Chart]: Found date column but no suitable numeric Y column.")
                    else:
                        string_cols = df.select_dtypes(include=['object', 'string', 'category']).columns
                        if string_cols.any() and numeric_cols.any():
                            x_col = string_cols[0]
                            y_col = numeric_cols[0]
                            chart_type = 'bar'
                            chart_title = f"{y_col} by {x_col}"
                            print(f"DEBUG [Auto Chart]: Inferred BAR chart: Category='{x_col}', Value='{y_col}'")
                        else:
                            print("DEBUG [Auto Chart]: Could not infer suitable columns for line or bar chart.")

                    if x_col and y_col:
                        df_plot = df[[x_col, y_col]].copy()
                        df_plot[y_col] = pd.to_numeric(df_plot[y_col], errors='coerce')
                        original_rows = len(df_plot)
                        df_plot.dropna(subset=[y_col], inplace=True)
                        dropped = original_rows - len(df_plot)
                        if dropped > 0:
                            print(f"Warning: Dropped {dropped} non-numeric rows for Y-axis ('{y_col}').")
                        if df_plot.empty:
                            raise ValueError(f"No numeric data remaining in inferred Y-column '{y_col}'.")

                        print(f"DEBUG [Auto Chart]: Plotting {chart_type} chart with {len(df_plot)} data points.")
                        plt.style.use('seaborn-v0_8-darkgrid')
                        fig, ax = plt.subplots(figsize=(8, 4))

                        if chart_type == 'line':
                            x_values_for_plot = df_plot[x_col]
                            try:
                                x_dates = pd.to_datetime(x_values_for_plot)
                                ax.plot(x_dates, df_plot[y_col], marker='.', linestyle='-')
                                fig.autofmt_xdate(rotation=30, ha='right')
                            except:
                                print("Warning: Plotting X as categories for line chart.")
                                ax.plot(x_values_for_plot.astype(str), df_plot[y_col], marker='.', linestyle='-')
                                tick_limit = 15
                                if len(x_values_for_plot) > tick_limit:
                                    step = max(1, len(x_values_for_plot) // tick_limit)
                                    ax.set_xticks(ax.get_xticks()[::step])
                                plt.xticks(rotation=45, ha='right', fontsize=8)
                            ax.set_ylabel(y_col, fontsize=10)

                        elif chart_type == 'bar':
                            df_plot.sort_values(by=y_col, ascending=True, inplace=True)
                            bar_limit = 20
                            if len(df_plot) > bar_limit:
                                print(f"Warning: Too many categories ({len(df_plot)}), showing top {bar_limit} by value.")
                                df_plot = df_plot.tail(bar_limit)
                            fig_height = max(4, len(df_plot) * 0.35 + 1.0)
                            plt.close(fig)
                            fig, ax = plt.subplots(figsize=(8, fig_height))
                            categories = df_plot[x_col].astype(str)
                            values = df_plot[y_col]
                            ax.barh(categories, values, color='skyblue', height=0.7)
                            ax.set_xlabel(y_col, fontsize=10)
                            ax.grid(True, axis='x', linestyle='--', linewidth=0.5)

                        ax.set_title(chart_title, fontsize=14, weight='bold')
                        ax.set_xlabel(x_col, fontsize=10)
                        ax.tick_params(labelsize=8)
                        plt.tight_layout()

                        img_buffer = io.BytesIO()
                        plt.savefig(img_buffer, format='png', dpi=150)
                        img_buffer.seek(0)
                        plt.close(fig)
                        chart_generated = True
                        print(f"Reporting Tool: Auto-generated {chart_type} chart successfully.")

                    else:
                        print("Reporting Tool Warning: Could not automatically determine columns/type for charting from CSV data.")
                        content += "\n\n(Note: CSV data provided, but could not automatically determine how to generate a chart.)"

                except Exception as chart_e:
                    print(f"Reporting Tool Error: Failed during auto-chart generation: {chart_e}")
                    traceback.print_exc()
                    if img_buffer:
                        img_buffer.close()
                    plt.close('all')
                    content += f"\n\n(Note: Error encountered while attempting to generate chart from data: {str(chart_e)[:100]})"
        else:
            print("DEBUG [Auto Chart]: No CSV data provided in input.")

        try:
            doc = SimpleDocTemplate(str(target_path), pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            story.append(Paragraph(title, styles['h1']))
            story.append(Spacer(1, 0.2 * inch))
            for para_text in content.split('\n\n'):
                cleaned_para = para_text.strip()
                if cleaned_para:
                    story.append(Paragraph(cleaned_para, styles['Normal']))
                    story.append(Spacer(1, 0.1 * inch))
            if chart_generated and img_buffer:
                story.append(Spacer(1, 0.2 * inch))
                chart_image = Image(img_buffer, width=7 * inch, height=3.5 * inch)
                story.append(chart_image)
            doc.build(story)
            status = "with auto-chart" if chart_generated else "text-only (charting failed or no data)"
            print(f"Reporting Tool: Successfully created PDF ({status}): {target_path}")
            relative_path_out = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else filename
            return f"Successfully created PDF report '{relative_path_out}' ({status})."
        except Exception as pdf_build_e:
            print(f"Reporting Tool Error: Failed during PDF build phase: {pdf_build_e}")
            traceback.print_exc()
            return f"Error building PDF document '{filename}': {str(pdf_build_e)}"
        finally:
            if img_buffer:
                img_buffer.close()

    except Exception as e:
        print(f"Reporting Tool Error: Unexpected failure in generate_pdf_report_with_auto_chart for '{filename}': {e}")
        traceback.print_exc()
        plt.close('all')
        return f"Error generating PDF report '{filename}': {str(e)}"

# --- LangChain Tool Definitions ---
generate_basic_pdf_report_tool = Tool(
    name="Generate Basic PDF Report (Text Only)",
    func=create_basic_pdf_report,
    description=(
        "Use this tool ONLY when the request explicitly asks for a TEXT-ONLY PDF report, or as a fallback if charting fails. "
        "Input MUST be 3 parts separated by pipes '|': 'filename.pdf|Report Title|Report text content'. "
        "Example: 'summary.pdf|Report Summary|This is the content.' Saves to 'outputs'."
    )
)

generate_pdf_auto_chart_tool = Tool(
    name="Generate PDF Report with Optional Auto-Chart",
    func=generate_pdf_report_with_auto_chart,
    description=(
        "Use this tool to generate a PDF report that includes text content and attempts to AUTOMATICALLY generate ONE relevant chart (line or bar) if suitable CSV data is provided. "
        "Input MUST be 4 parts separated by pipes '|': 'filename.pdf|Report Title|Report text content|OPTIONAL_CSV_DATA'. "
        "- OPTIONAL_CSV_DATA: If you have relevant CSV data (e.g., from web table extraction or stock tool), include it here. MUST have headers. Remove 'Success:/CSV Data:' prefixes. If no suitable data is found or needed, leave this part empty or provide only the first 3 parts. "
        "The tool will try to infer if a line chart (for date-like data) or bar chart (for categorical data) is appropriate and select the columns automatically based on common patterns (e.g., 'Date', 'Year', first numeric column, first string column). "
        "If charting succeeds, the chart is added after the text. If CSV data is missing, empty, invalid, or charting fails, a text-only PDF is generated with a note. "
        "Example with data: 'trends.pdf|Energy Trends|Solar is growing.|Solar Growth|Year,Solar GW\\n2020,100\\n2021,150' "
        "Example without data: 'trends.pdf|Energy Trends|Solar is growing rapidly.|' "
        "Saves file to 'outputs'. Returns success/error message, indicating if chart was included."
    )
)
