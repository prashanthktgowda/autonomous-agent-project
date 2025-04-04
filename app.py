# app.py (Complete Script with UI Delete Button)

import streamlit as st
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import io
from contextlib import redirect_stdout
import traceback
import time # Import time for delay after deletion/refresh
from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile

# --- Add project root to Python path ---
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
# --- ---

# --- Load Environment Variables ---
load_dotenv()
# --- ---

# --- Define Output Directory ---
OUTPUT_DIR = Path("outputs").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# --- ---

# --- Import Agent Logic ---
try:
    # Ensure your planner uses the correct LLM initialization based on your .env
    from agent.planner import initialize_agent
except ImportError as e:
    st.error(f"Error importing agent logic: {e}. Make sure 'agent/planner.py' exists and dependencies are installed.", icon="🚨")
    traceback.print_exc() # Print detailed traceback to console
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during agent import: {e}", icon="🚨")
    traceback.print_exc()
    st.stop()
# --- ---

# --- Page Configuration ---
st.set_page_config(page_title="Autonomous AI Agent", layout="centered", initial_sidebar_state="collapsed")

# --- Custom CSS Styling ---
st.markdown("""
<style>
    /* General dark theme styling */
    body {
        background-color: #121212; /* Dark background */
        color: #ffffff; /* White text */
    }
    h1 {
        text-align: center;
        color: #ffffff; /* White title color */
        font-size: 2.5em;
        margin-top: 20px;
    }
    .stCaption {
        text-align: center;
        color: #b0b0b0; /* Light gray caption color */
        font-size: 1.2em;
    }
    .stTextArea [data-baseweb="textarea"] {
        margin: 0 auto;
        width: 80%;
        min-height: 100px;
        font-size: 1.1em;
        background-color: #1e1e1e; /* Darker text area background */
        color: #ffffff; /* White text */
        border: 1px solid #333333; /* Subtle border */
        border-radius: 5px;
    }
    .stButton>button {
        margin: 0 auto;
        display: block;
        border-radius: 5px;
        padding: 10px 20px;
        background-color: #4CAF50; /* Green button */
        color: white;
        font-size: 16px;
    }
    .stButton>button:hover {
        background-color: #45a049; /* Darker green on hover */
    }
    .stDownloadButton>button {
        background-color: #1abc9c; /* Teal button */
        color: white;
        border-radius: 5px;
    }
    .stDownloadButton>button:hover {
        background-color: #16a085; /* Darker teal on hover */
    }
    .stCheckbox {
        margin: 0 auto;
        display: block;
        text-align: center;
    }
    .stTextArea {
        margin: 0 auto;
    }
    .stExpander {
        background-color: #1e1e1e; /* Darker background for expanders */
        color: #ffffff;
    }
    .stSelectbox {
        margin: 0 auto;
        width: 80%;
    }
</style>
""", unsafe_allow_html=True)

st.title("What can I help with?")
st.caption("Interact with the AI agent to perform tasks effortlessly.")
# --- ---

# --- Check for Necessary API Key ---
# Adapt this check based on the LLM you are using in planner.py
llm_provider = "API"
api_key_needed = None
# Basic check based on function code content (adjust if needed)
try:
    planner_code = initialize_agent.__code__.co_code
    if b'Google' in planner_code or b'gemini' in planner_code:
        api_key_needed = "GOOGLE_API_KEY"
        llm_provider = "Google Gemini"
    elif b'HuggingFace' in planner_code or b'hf_' in planner_code:
        api_key_needed = "HUGGINGFACEHUB_API_TOKEN"
        llm_provider = "Hugging Face"
    elif b'OpenAI' in planner_code or b'sk-' in planner_code:
        api_key_needed = "OPENAI_API_KEY"
        llm_provider = "OpenAI"
except Exception:
    pass # Ignore errors during introspection

if api_key_needed and not os.getenv(api_key_needed):
    st.error(f"{llm_provider} API key not found! Please ensure `{api_key_needed}` is set in your `.env` file.", icon="🚨")
    st.stop()
# --- ---

# --- Agent Initialization (Cached) ---
@st.cache_resource(show_spinner="Initializing AI Agent...")
def load_agent_executor():
    print("--- Attempting to initialize agent executor (cached) ---")
    try:
        # Initialize non-verbosely for caching; verbose output capture happens during invoke
        agent_exec = initialize_agent(verbose=False)
        print("--- Agent executor initialized successfully ---")
        return agent_exec
    except Exception as e:
        st.error(f"Fatal Error: Failed to initialize the AI agent. Check console logs. Error: {e}", icon="💥")
        print("--- Agent Initialization Error ---")
        traceback.print_exc()
        print("--- End Agent Initialization Error ---")
        return None

agent_executor = load_agent_executor()

if not agent_executor:
    st.warning("Agent could not be loaded. The application cannot proceed.")
    st.stop()
# --- ---


# --- UI Elements for Agent Interaction ---
instruction = st.text_area(
    "Ask anything:",
    height=120,
    placeholder="e.g., Summarize the content of 'outputs/some_data.txt'."
)

submit_button = st.button("Run Agent")

# --- Agent Execution Logic ---
# Use session state to store the last result and logs
if 'last_final_output' not in st.session_state:
    st.session_state.last_final_output = None
if 'last_verbose_output' not in st.session_state:
    st.session_state.last_verbose_output = None

if submit_button and instruction:
    st.info("Processing your request... Please wait.")
    stdout_capture = io.StringIO()
    st.session_state.last_final_output = None # Clear previous results
    st.session_state.last_verbose_output = None

    try:
        with st.spinner("Agent thinking and acting... 🤔"):
            capture_output = False
            if capture_output:
                 # Redirect stdout to capture verbose logs from LangChain/tools
                 with redirect_stdout(stdout_capture):
                    result = agent_executor.invoke({"input": instruction})
            else:
                 result = agent_executor.invoke({"input": instruction})

        final_output = result.get('output', '*Agent finished, but no specific "output" text was provided.*')
        st.session_state.last_final_output = final_output # Store result

        st.success("Agent execution completed successfully!")

    except Exception as e:
        st.error(f"An error occurred: {e}")
        print("\n--- Agent Execution Error in Streamlit App ---")
        traceback.print_exc()
        print("--- End Agent Execution Error ---\n")
        # Store any logs captured before the error
        if 'capture_output' in locals() and capture_output:
             st.session_state.last_verbose_output = stdout_capture.getvalue()

elif submit_button and not instruction:
    st.warning("Please enter an instruction before clicking 'Run Agent'.", icon="⚠️")

# --- Display Previous Run Results (if any) ---
if st.session_state.last_final_output:
    st.markdown("---")
    st.markdown("**Last Final Answer:**")
    # Display as a code block for potentially long/formatted output
    st.code(st.session_state.last_final_output, language=None)

if st.session_state.last_verbose_output:
     with st.expander("Last Agent Thought Process (Verbose Output)", expanded=False):
        st.text_area("Logs:", value=st.session_state.last_verbose_output, height=400, disabled=True, key="verbose_log_area_display")


# --- PDF Generation Function ---
def generate_pdf_with_charts(output_text, chart_data, output_file):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Add Title
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt="Generated Report", ln=True, align="C")
    pdf.ln(10)

    # Add Text Content
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=output_text)
    pdf.ln(10)

    # Add Charts
    for idx, data in enumerate(chart_data):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_chart:
            plt.figure(figsize=(6, 4))
            plt.plot(data["x"], data["y"], label=data.get("label", "Data"))
            plt.title(data.get("title", "Chart"))
            plt.xlabel(data.get("xlabel", "X-axis"))
            plt.ylabel(data.get("ylabel", "Y-axis"))
            plt.legend()
            plt.savefig(temp_chart.name)
            plt.close()

            pdf.add_page()
            pdf.image(temp_chart.name, x=10, y=30, w=180)
            os.unlink(temp_chart.name)  # Clean up temporary file

    # Save PDF
    pdf.output(output_file)
    return output_file

# --- UI Elements for PDF Generation ---
if st.button("Generate PDF Report"):
    if st.session_state.last_final_output:
        try:
            # Example chart data (replace with actual data)
            chart_data = [
                {"x": [2019, 2020, 2021, 2022], "y": [100, 200, 300, 400], "label": "Trend A", "title": "Example Chart A"},
                {"x": [2019, 2020, 2021, 2022], "y": [400, 300, 200, 100], "label": "Trend B", "title": "Example Chart B"},
            ]
            output_pdf_path = OUTPUT_DIR / "generated_report.pdf"
            generate_pdf_with_charts(st.session_state.last_final_output, chart_data, str(output_pdf_path))
            st.success(f"PDF report generated: {output_pdf_path}")
            with open(output_pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_file,
                    file_name="generated_report.pdf",
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Failed to generate PDF: {e}")
    else:
        st.warning("No output available to generate a PDF report.")

# --- Output Files Browser Section ---
st.divider()
st.header("📂 Output Files Browser")
st.caption(f"Browsing files inside the `{OUTPUT_DIR.name}` directory.")

# --- Refresh Button ---
if st.button("🔄 Refresh File List", type="secondary", key="refresh_files"):
    st.cache_data.clear() # Clear file list cache
    # Clear selection state if needed? Generally handled by checking existence later
    st.rerun()

# --- Function to get files ---
@st.cache_data(ttl=None) # Cache disabled for now, refresh button needed
def get_files_in_outputs(base_dir):
    print(f"--- Scanning directory: {base_dir} ---")
    files_info = []
    try:
        if not base_dir.exists() or not base_dir.is_dir():
            return [], f"Output directory '{base_dir.name}' not found or is not a directory."

        all_items = sorted([item for item in base_dir.rglob('*') if item.is_file() and item.name != '.gitkeep'], key=os.path.getmtime, reverse=True) # Sort by modified time, newest first

        for item in all_items:
            try:
                relative_path = item.relative_to(base_dir)
                file_size = item.stat().st_size
                files_info.append({
                    "display_path": str(relative_path),
                    "full_path": item,
                    "size": file_size
                })
            except Exception as stat_err:
                 print(f"Could not stat file {item}: {stat_err}")

        if not files_info:
            return [], "Output directory is empty."
        return files_info, None
    except PermissionError:
        return [], f"Error: Permission denied when scanning {base_dir}."
    except Exception as e:
        traceback.print_exc()
        return [], f"Error scanning output directory: {e}"

# --- Display File List ---
output_files, error_msg = get_files_in_outputs(OUTPUT_DIR)

if error_msg:
    st.warning(error_msg, icon="⚠️")
elif not output_files:
    st.info("Output directory is empty. Run the agent to generate some files!", icon="📄")
else:
    # Format options for selectbox
    file_options = {
        f"{info['display_path']} ({info['size']/1024:.1f} KB)": info['full_path']
        for info in output_files
    }
    # Add placeholder
    display_list = ["-- Select a file --"] + list(file_options.keys())

    # --- Session state for remembering selection ---
    if 'selected_file_display' not in st.session_state:
         st.session_state.selected_file_display = display_list[0]

    # Check if the selected file still exists in the current list
    if st.session_state.selected_file_display != display_list[0] and st.session_state.selected_file_display not in display_list:
         st.info(f"Previously selected file '{st.session_state.selected_file_display}' seems to be gone. Resetting selection.", icon="❓")
         st.session_state.selected_file_display = display_list[0] # Reset to placeholder

    # --- Selectbox ---
    selected_display_option = st.selectbox(
        "**Select Output File:**",
        options=display_list,
        key='file_selector',
        index=display_list.index(st.session_state.selected_file_display) # Use state for index
    )
    # Update session state on change
    st.session_state.selected_file_display = selected_display_option

    # --- Display Selected File Content and Action Buttons ---
    if selected_display_option != "-- Select a file --":
        selected_full_path = file_options.get(selected_display_option)

        if selected_full_path and selected_full_path.exists(): # Double check existence
            file_size = selected_full_path.stat().st_size
            display_name = selected_full_path.relative_to(OUTPUT_DIR)

            st.markdown(f"---")
            st.markdown(f"##### Details for: `{display_name}`")

            # --- Action Buttons Row ---
            col_dl, col_del, col_spacer = st.columns([1, 1, 4]) # Adjust spacing

            # Download Button
            with col_dl:
                 try:
                     with open(selected_full_path, "rb") as fp:
                         st.download_button(
                             label="⬇️ Download", # Simpler label
                             data=fp,
                             file_name=selected_full_path.name,
                             mime="application/octet-stream",
                             key=f"dl_{selected_display_option}"
                         )
                 except Exception as e:
                     st.error(f"Download Error: {e}", icon="❌")

            # --- Delete Button and Confirmation ---
            with col_del:
                delete_key = f"del_{selected_display_option}"
                confirm_key = f"confirm_{delete_key}"

                # Initialize confirmation state if not present
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                # Show initial delete button OR confirmation dialog
                if not st.session_state[confirm_key]:
                    # Show the initial "Delete" button
                    if st.button("🗑️ Delete", key=delete_key, type="secondary", help="Delete this file"):
                        # Set confirmation flag to True and rerun to show confirmation
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    # Show confirmation message and buttons
                    st.warning(f"**Delete `{display_name}`?** This cannot be undone.", icon="⚠️")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("YES, DELETE", key=f"confirm_yes_{delete_key}", type="primary", help="Confirm Deletion"):
                            try:
                                print(f"--- Deleting file: {selected_full_path} ---")
                                selected_full_path.unlink() # Perform deletion
                                st.success(f"Deleted `{display_name}`!", icon="✅")
                                # Reset state, clear cache, and refresh UI
                                st.session_state[confirm_key] = False
                                st.session_state.selected_file_display = display_list[0]
                                st.cache_data.clear()
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting `{display_name}`: {e}", icon="❌")
                                print(f"--- Deletion Error: {e} ---")
                                traceback.print_exc()
                                st.session_state[confirm_key] = False # Reset confirmation on error
                                st.rerun() # Rerun to hide buttons after error msg
                    with col_cancel:
                         if st.button("Cancel", key=f"confirm_no_{delete_key}", type="secondary"):
                              st.session_state[confirm_key] = False # Clear confirmation flag
                              st.rerun() # Rerun to hide confirmation


            # --- Content Preview ---
            st.markdown("**Content Preview:**") # Add header for preview section
            text_extensions = ['.txt', '.md', '.log', '.csv', '.json', '.py', '.yaml', '.yml', '.html', '.css', '.js', '.sh']
            file_ext = selected_full_path.suffix.lower()
            max_preview_size = 1 * 1024 * 1024 # 1 MB

            if file_ext in text_extensions:
                if file_size == 0:
                     st.info("File is empty.", icon="📄")
                elif file_size > max_preview_size:
                    st.info(f"File is large ({file_size/1024/1024:.1f} MB). Preview might be truncated. Use download.", icon="💾")
                    # Still try to show preview if large but within limits for reading
                    try:
                         with open(selected_full_path, "r", encoding="utf-8", errors="ignore") as f:
                             content = f.read(max_preview_size + 1)
                         truncated = len(content) > max_preview_size
                         content_to_display = content[:max_preview_size]
                         lang_map = {'.py':'python', '.js':'javascript', '.html':'html', '.css':'css', '.sh':'bash', '.json':'json', '.yaml':'yaml', '.yml':'yaml'}
                         st.code(content_to_display, language=lang_map.get(file_ext, None))
                         if truncated: st.warning("Preview truncated (1MB limit).", icon="✂️")
                    except Exception as e:
                        st.error(f"Error reading large file for preview: {e}", icon="❌")

                else: # File is text and within size limits
                    try:
                        with open(selected_full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content_to_display = f.read()

                        if file_ext == '.md':
                            st.markdown("---")
                            st.markdown(content_to_display, unsafe_allow_html=False)
                            st.markdown("---")
                        else:
                            lang_map = {'.py':'python', '.js':'javascript', '.html':'html', '.css':'css', '.sh':'bash', '.json':'json', '.yaml':'yaml', '.yml':'yaml'}
                            st.code(content_to_display, language=lang_map.get(file_ext, None))
                    except Exception as e:
                        st.error(f"Error reading/displaying file content: {e}", icon="❌")
            else: # Non-text file
                st.info(f"Preview not available for file type ({file_ext}). Use download.", icon="📄")
        elif selected_display_option != "-- Select a file --":
             # This case handles if the selected file disappeared between list generation and selection processing
             st.error("Selected file not found. It might have been deleted. Refreshing...", icon="❓")
             st.cache_data.clear()
             time.sleep(1)
             st.rerun()


# --- Footer Info ---
st.markdown("<p style='text-align: center; color: grey;'>Outputs are saved in the <code>outputs/</code> directory.</p>", unsafe_allow_html=True)
# --- ---