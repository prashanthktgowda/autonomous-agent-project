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
st.set_page_config(page_title="Autonomous AI Agent", layout="wide", initial_sidebar_state="collapsed")

# --- Custom CSS Styling ---
st.markdown("""
<style>
    /* General UI improvements */
    .stTextArea [data-baseweb="textarea"] {
        min-height: 100px;
        font-size: 1.1em; /* Slightly larger text */
    }
    .stButton>button {
        border-radius: 5px; /* Rounded corners */
        padding: 8px 15px; /* More padding */
    }
    h1 {
        text-align: center;
        color: #2c3e50; /* Darker title color */
        margin-bottom: 0.5em;
    }
    .stCaption {
        text-align: center;
        color: #7f8c8d; /* Subdued caption color */
    }

    /* Specific Button Styling */
    /* Run Agent Button */
    .stButton button[kind="primary"] {
        /* Default Streamlit primary style is usually okay */
        /* background-color: #3498db; */
        /* border-color: #2980b9; */
    }
     /* Refresh Button */
    .stButton button[kind="secondary"] {
         /* Default Streamlit secondary style */
    }

    /* Download Button */
    div[data-testid="stDownloadButton"] > button {
        width: auto;
        height: auto;
        font-size: 14px;
        margin-top: 10px;
        border-radius: 5px;
        background-color: #1abc9c; /* Teal color */
        border-color: #16a085;
        color: white;
    }
     div[data-testid="stDownloadButton"] > button:hover {
         background-color: #16a085;
         border-color: #138d75;
     }

    /* Initial Delete Button (secondary style but red border) */
     /* Note: Targeting precisely might be tricky, use keys if needed */
     button[kind="secondary"]:has(span > svg[data-icon="trash"]) { /* Attempt to target button with trash icon */
        border: 1px solid #e74c3c !important; /* Red border */
        color: #e74c3c !important; /* Red text */
        margin-left: 10px; /* Add some space next to download */
     }
     button[kind="secondary"]:has(span > svg[data-icon="trash"]):hover {
        background-color: #fadbd8 !important; /* Light red background on hover */
     }


    /* YES, DELETE Confirmation Button */
    button[data-testid="baseButton-primary"]:not([kind="secondary"]):not([data-testid*="stDownloadButton"]) { /* Target primary confirmation button */
        background-color: #e74c3c !important; /* Red background */
        border-color: #c0392b !important; /* Darker red border */
        color: white !important;
    }
    button[data-testid="baseButton-primary"]:not([kind="secondary"]):not([data-testid*="stDownloadButton"]):hover {
         background-color: #c0392b !important;
         border-color: #a93226 !important;
    }


    /* Make code blocks readable */
    pre code {
        white-space: pre-wrap !important; /* Allow wrapping */
        word-wrap: break-word !important; /* Break long words */
        font-size: 0.95em;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Autonomous AI Agent")
st.caption("Interact with the AI agent to perform tasks across web, terminal, and file system.")
st.divider()
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
st.header("🤖 Agent Interaction")
col1, col2 = st.columns([3, 1])

with col1:
    instruction = st.text_area(
        "**Enter your instruction for the Agent:**",
        height=120,
        placeholder="e.g., Read the file 'outputs/some_data.txt' and summarize its content."
    )

with col2:
    st.markdown("**Options:**")
    show_verbose = st.checkbox("Show Agent's Thought Process", value=False, help="Displays the detailed steps (Thoughts, Actions, Observations) the agent takes.")
    st.markdown("---")
    submit_button = st.button("🚀 Run Agent", type="primary") # Make run button primary

st.divider()

# --- Agent Execution Logic ---
# Use session state to store the last result and logs
if 'last_final_output' not in st.session_state:
    st.session_state.last_final_output = None
if 'last_verbose_output' not in st.session_state:
    st.session_state.last_verbose_output = None

if submit_button and instruction:
    st.markdown("### Agent Execution Log")
    status_placeholder = st.empty()
    status_placeholder.info("Agent is processing your request... Please wait.", icon="⏳")
    stdout_capture = io.StringIO()
    st.session_state.last_final_output = None # Clear previous results
    st.session_state.last_verbose_output = None

    try:
        with st.spinner("Agent thinking and acting... 🤔"):
            capture_output = show_verbose
            if capture_output:
                 # Redirect stdout to capture verbose logs from LangChain/tools
                 with redirect_stdout(stdout_capture):
                    result = agent_executor.invoke({"input": instruction})
            else:
                 result = agent_executor.invoke({"input": instruction})

        status_placeholder.empty()
        final_output = result.get('output', '*Agent finished, but no specific "output" text was provided.*')
        st.session_state.last_final_output = final_output # Store result

        st.success("**Agent Run Complete!**", icon="✅")

        if capture_output:
            st.session_state.last_verbose_output = stdout_capture.getvalue() # Store logs

    except Exception as e:
        status_placeholder.empty()
        st.error(f"An error occurred during agent execution: {e}", icon="❌")
        st.error("Check instruction or agent configuration. See console for details.")
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
st.divider()
st.markdown(f"<p style='text-align: center; color: grey;'>Agent outputs are saved in the <code>{OUTPUT_DIR.name}/</code> directory ({OUTPUT_DIR})</p>", unsafe_allow_html=True)
# --- ---