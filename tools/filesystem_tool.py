# tools/filesystem_tool.py (Corrected Security Logic - Ensure this is saved!)

import os
from pathlib import Path
from langchain.tools import Tool
import traceback
import codecs # Ensure codecs is imported for write_file

# --- Define Output and Script Directories ---
try:
    PROJECT_ROOT = Path(__file__).parent.parent.resolve() # Get project root
    OUTPUT_DIR = PROJECT_ROOT / "outputs"
    SCRIPT_DIR = PROJECT_ROOT / "scripts" # Define the allowed script directory
    # Ensure directories exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True) # Create scripts dir if needed
    print(f"DEBUG [filesystem_tool.py]: OUTPUT_DIR: {OUTPUT_DIR}")
    print(f"DEBUG [filesystem_tool.py]: SCRIPT_DIR: {SCRIPT_DIR}")
except Exception as e:
    print(f"CRITICAL ERROR setting up directories: {e}")
    OUTPUT_DIR = Path("outputs"); SCRIPT_DIR = Path("scripts") # Fallbacks

# --- Helper Function for Safe Path Resolution (OUTPUTS ONLY) ---
def _resolve_outputs_path(input_path_str: str) -> Path | None:
    # ... (Implementation from previous correct version) ...
    if not isinstance(input_path_str, str): print(f"FS Path Err: Input not string"); return None
    cleaned_path = input_path_str.strip().replace("\\", "/")
    if not cleaned_path or cleaned_path == '.': return OUTPUT_DIR
    if Path(cleaned_path).is_absolute() or ".." in Path(cleaned_path).parts: print(f"FS Security Err: Absolute/'..' denied: '{input_path_str}'."); return None
    target_path = (OUTPUT_DIR / cleaned_path).resolve()
    try:
        if target_path == OUTPUT_DIR or target_path.is_relative_to(OUTPUT_DIR): return target_path
        else: print(f"FS Security Err: Resolved path '{target_path}' outside '{OUTPUT_DIR}'."); return None
    except ValueError: print(f"FS Security Err: Cannot compare path '{target_path}' with '{OUTPUT_DIR}'."); return None
    except Exception as e: print(f"FS Path Err: Validating '{target_path}': {e}"); traceback.print_exc(); return None

# --- Helper Function for Safe Path Resolution (SCRIPTS ONLY) ---
def _resolve_scripts_path(input_path_str: str) -> Path | None:
    # ... (Implementation from previous correct version) ...
    if not isinstance(input_path_str, str): print(f"Script Path Err: Input not string"); return None
    cleaned_path = input_path_str.strip().replace("\\", "/").lstrip("/")
    if not cleaned_path or not cleaned_path.lower().endswith(".py"): print(f"Script Path Err: Need non-empty .py path: '{input_path_str}'"); return None
    if ".." in Path(cleaned_path).parts: print(f"Script Security Err: '..' denied: '{input_path_str}'."); return None
    if Path(cleaned_path).is_absolute(): print(f"Script Security Err: Absolute paths denied: '{input_path_str}'."); return None
    target_path = (SCRIPT_DIR / cleaned_path).resolve()
    try:
        if target_path != SCRIPT_DIR and target_path.is_relative_to(SCRIPT_DIR): return target_path
        else: print(f"Script Security Err: Path '{target_path}' not within '{SCRIPT_DIR}'."); return None
    except ValueError: print(f"Script Security Err: Cannot compare '{target_path}' with '{SCRIPT_DIR}'."); return None
    except Exception as e: print(f"Script Path Err: Validating '{target_path}': {e}"); traceback.print_exc(); return None


# Define the designated output directory relative to the project root
try:
    OUTPUT_DIR = Path("outputs").resolve()
    # Ensure the output directory exists when the script loads
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"DEBUG [filesystem_tool.py]: OUTPUT_DIR resolved to: {OUTPUT_DIR}")
except Exception as e:
    print(f"CRITICAL ERROR in filesystem_tool.py: Failed to resolve or create OUTPUT_DIR. Error: {e}")
    # Fallback or raise error depending on desired behavior
    OUTPUT_DIR = Path("outputs") # Simple fallback


# --- Corrected Helper Function for Safe Path Resolution ---
def _resolve_path(input_path_str: str) -> Path | None:
    """
    Helper to safely resolve paths relative to OUTPUT_DIR.
    Handles '.', empty string, and relative paths.
    Returns the resolved absolute Path object or None if invalid/unsafe.
    """
    if not isinstance(input_path_str, str):
        print(f"Filesystem Path Error: Input path must be a string, got {type(input_path_str)}")
        return None

    cleaned_path = input_path_str.strip().replace("\\", "/")

    # Treat '.' or empty string as the root of the OUTPUT_DIR
    if not cleaned_path or cleaned_path == '.':
        print(f"DEBUG [_resolve_path]: Input '.' or empty resolved to OUTPUT_DIR root: {OUTPUT_DIR}")
        # Return the OUTPUT_DIR path itself when listing its root
        return OUTPUT_DIR

    # Prevent absolute paths and path traversal attempts
    # Check if it starts with '/' or contains '..' components
    if Path(cleaned_path).is_absolute() or ".." in Path(cleaned_path).parts:
        print(f"Filesystem Security Error: Absolute paths or '..' traversal denied for input '{input_path_str}'.")
        return None

    # Construct the potential absolute path by joining with OUTPUT_DIR
    target_path = (OUTPUT_DIR / cleaned_path).resolve()
    print(f"DEBUG [_resolve_path]: Input '{input_path_str}' resolved to potential target: {target_path}")

    # --- Revised Final Security Check ---
    # Ensure the resolved path is EQUAL to OUTPUT_DIR or is within it.
    try:
        # Check if target_path is OUTPUT_DIR itself OR a subdirectory/file within it
        if target_path == OUTPUT_DIR or target_path.is_relative_to(OUTPUT_DIR):
            print(f"DEBUG [_resolve_path]: Path {target_path} confirmed within allowed directory.")
            # Return the resolved path now
            return target_path
        else:
            # This path resolved outside the allowed directory
            print(f"Filesystem Security Error: Resolved path '{target_path}' is outside the allowed directory '{OUTPUT_DIR}'. Access denied.")
            return None
    except ValueError:
        # is_relative_to raises ValueError for unrelated paths (e.g., different drives on Windows)
        print(f"Filesystem Security Error: Cannot compare path '{target_path}' with allowed directory '{OUTPUT_DIR}' (unrelated paths?). Access denied.")
        return None
    except Exception as e:
        print(f"Filesystem Path Error: Unexpected error validating path '{target_path}'. Error: {e}")
        traceback.print_exc()
        return None


# --- Core Filesystem Functions ---

def read_file(file_path: str) -> str:
    """Reads the content of a file within the designated 'outputs' directory."""
    print(f"Filesystem Tool: Attempting to read file: '{file_path}'")
    target_path = _resolve_path(file_path) # Use the corrected helper
    if not target_path:
        # Error message generated by _resolve_path
        return f"Error: Invalid or disallowed file path '{file_path}'."

    try:
        if not target_path.exists():
            print(f"DEBUG [read_file]: File not found at {target_path}")
            # Try to show relative path in error if possible
            relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else file_path
            return f"Error: File not found at resolved path: {relative_err_path}"
        if not target_path.is_file():
             print(f"DEBUG [read_file]: Path is not a file: {target_path}")
             relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else file_path
             return f"Error: Path exists but is not a file: {relative_err_path}"

        # Proceed with reading
        content = target_path.read_text(encoding='utf-8', errors='ignore')
        print(f"Filesystem Tool: Read {len(content)} characters from {target_path}")
         # Limit output size
        max_len = 4000
        if len(content) > max_len:
            print(f"Filesystem Tool: Truncating content from {len(content)} to {max_len} chars.")
            content = content[:max_len] + "\n... (truncated)"
        return content
    except Exception as e:
        print(f"Filesystem Tool Error: Failed to read {target_path}. Error: {e}")
        traceback.print_exc()
        relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else file_path
        return f"Error reading file {relative_err_path}. Details: {str(e)}"


def write_file(path_and_content: str) -> str:
    """
    Writes content to a file within the designated 'outputs' directory.
    Input format: 'relative/path/to/file.txt|Content to write'.
    Creates directories if needed. Overwrites existing files. Decodes escapes.
    """
    print(f"Filesystem Tool: Attempting to write file based on input: '{path_and_content[:100]}...'")
    try:
        parts = path_and_content.split('|', 1)
        if len(parts) != 2:
            return "Error: Input must be in the format 'filepath|content'. Pipe separator '|' is missing."
        file_path_str, content_raw = parts[0].strip(), parts[1]

        # --- DECODE ESCAPE SEQUENCES ---
        try:
            # Decode standard Python string escapes like \n, \t, etc.
            content = codecs.decode(content_raw, 'unicode_escape')
        except Exception as decode_err:
            print(f"Filesystem Tool Warning: Could not unicode-escape decode content, writing raw content. Error: {decode_err}")
            content = content_raw # Fallback
        # --- END DECODE ESCAPE SEQUENCES ---


        target_path = _resolve_path(file_path_str) # Use the corrected helper
        if not target_path:
            return f"Error: Invalid or disallowed file path '{file_path_str}' for writing."

        # Prevent writing directly to the OUTPUT_DIR itself
        if target_path == OUTPUT_DIR:
             print(f"Filesystem Write Error: Cannot write directly to the outputs directory itself.")
             return f"Error: Cannot write directly to the outputs directory. Specify a filename."

        # Prevent writing if the target path resolves to an existing directory
        if target_path.exists() and target_path.is_dir():
             relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else file_path_str
             return f"Error: Cannot write file. Path '{relative_err_path}' exists and is a directory."

        # Create parent directories safely *before* writing
        parent_dir = target_path.parent
        # Double check parent safety (should be covered by _resolve_path check on target_path, but be paranoid)
        if not (parent_dir == OUTPUT_DIR or parent_dir.is_relative_to(OUTPUT_DIR)):
             relative_parent_err = parent_dir.relative_to(OUTPUT_DIR.parent) if parent_dir.is_absolute() else parent_dir
             return f"Error: Cannot create parent directory '{relative_parent_err}' as it resolves outside 'outputs'."
        parent_dir.mkdir(parents=True, exist_ok=True)

        # Proceed with writing
        target_path.write_text(content, encoding='utf-8')
        relative_path_out = target_path.relative_to(OUTPUT_DIR) if target_path.is_absolute() else file_path_str
        print(f"Filesystem Tool: Successfully wrote {len(content)} characters to {target_path}")
        return f"Successfully wrote content to file: outputs/{relative_path_out}"
    except Exception as e:
        print(f"Filesystem Tool Error: Failed to write to path derived from '{file_path_str}'. Error: {e}")
        traceback.print_exc()
        relative_display_path = Path(file_path_str).name
        return f"Error writing file '{relative_display_path}'. Details: {str(e)}"


def list_directory(directory_path_str: str = ".") -> str:
    """
    Lists the contents of a directory within the designated 'outputs' directory.
    Input is a relative path within 'outputs', or '.' (or empty) for the root of 'outputs'.
    """
    print(f"Filesystem Tool: Attempting to list directory: '{directory_path_str}'")
    # Use the corrected helper to get the resolved, validated absolute path
    target_path = _resolve_path(directory_path_str)
    if not target_path:
        # Error message generated by _resolve_path
        return f"Error: Invalid or disallowed directory path '{directory_path_str}'."

    try:
        # Check existence and type using the validated resolved path
        if not target_path.exists():
            print(f"DEBUG [list_directory]: Directory not found at {target_path}")
            relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else directory_path_str
            return f"Error: Directory not found: {relative_err_path}"
        if not target_path.is_dir():
            print(f"DEBUG [list_directory]: Path is not a directory: {target_path}")
            relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else directory_path_str
            return f"Error: Path is not a directory: {relative_err_path}"

        # Proceed with listing
        print(f"DEBUG [list_directory]: Listing contents of {target_path}")
        items = []
        for item in sorted(target_path.iterdir()): # Sort items alphabetically
            if item.name == '.gitkeep': continue # Skip gitkeep file
            # Basic check on item path resolution for safety (prevent listing if item symlinks out)
            try:
                 if not item.resolve().is_relative_to(OUTPUT_DIR):
                      print(f"Filesystem Tool Warning [list_directory]: Skipping item '{item.name}' as it resolves outside '{OUTPUT_DIR}'.")
                      continue
            except Exception: # Ignore resolution errors for individual items during listing
                 print(f"Filesystem Tool Warning [list_directory]: Could not resolve item '{item.name}', skipping.")
                 continue

            item_type = "DIR" if item.is_dir() else "FILE"
            items.append(f"{item.name} ({item_type})")

        print(f"Filesystem Tool: Found {len(items)} listable items in {target_path}")

        # Determine display path (relative to project root, e.g., 'outputs' or 'outputs/subdir')
        if target_path == OUTPUT_DIR:
             display_root = f"{OUTPUT_DIR.name}/"
        else:
             relative_display_path = target_path.relative_to(OUTPUT_DIR.parent)
             display_root = f"{relative_display_path}/"

        if not items:
             return f"Directory '{display_root}' is empty."
        else:
             # Limit number of items listed
             max_items = 50
             if len(items) > max_items:
                 items_list = "\n".join(items[:max_items]) + f"\n... (truncated, {len(items)-max_items} more items exist)"
             else:
                 items_list = "\n".join(items)
             return f"Contents of directory '{display_root}':\n{items_list}"

    except PermissionError as pe:
         print(f"Filesystem Tool Error [list_directory]: Permission denied for {target_path}. Error: {pe}")
         traceback.print_exc()
         relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else directory_path_str
         return f"Error listing directory {relative_err_path}: Permission denied."
    except Exception as e:
        print(f"Filesystem Tool Error [list_directory]: Failed to list directory {target_path}. Error: {e}")
        traceback.print_exc()
        relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else directory_path_str
        return f"Error listing directory {relative_err_path}. Details: {str(e)}"

# --- Add this function definition BEFORE the Tool definitions ---

def append_text_to_file(path_and_content: str) -> str:
    """
    Appends content to the end of a file within the designated 'outputs' directory.
    Input format: 'relative/path/to/file.txt|Content to append'.
    Creates the file (and directories) if it doesn't exist. Decodes escapes.
    """
    print(f"Filesystem Tool: Attempting to append: '{path_and_content[:100]}...'")
    try:
        parts = path_and_content.split('|', 1)
        if len(parts) != 2:
            return "Error: Input must be 'filepath|content'. Pipe separator '|' missing."
        file_path_str, content_raw = parts[0].strip(), parts[1]

        # Decode escapes like \n
        try:
            content_to_append = codecs.decode(content_raw, 'unicode_escape')
        except Exception as decode_err:
            print(f"Filesystem Tool Warning (Append): Could not decode content, appending raw. Error: {decode_err}")
            content_to_append = content_raw

        target_path = _resolve_path(file_path_str) # Use the validated helper
        if not target_path:
            return f"Error: Invalid or disallowed file path '{file_path_str}' for appending."

        # Prevent operating directly on the output directory itself
        if target_path == OUTPUT_DIR:
            return f"Error: Cannot append to the root 'outputs' directory. Specify a filename."

        # Prevent appending to an existing directory
        if target_path.exists() and target_path.is_dir():
             relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else file_path_str
             return f"Error: Cannot append. Path 'outputs/{relative_err_path}' exists and is a directory."

        # Create parent directories safely *before* opening file
        parent_dir = target_path.parent
        if not (parent_dir == OUTPUT_DIR or parent_dir.is_relative_to(OUTPUT_DIR)):
             relative_parent_err = parent_dir.relative_to(OUTPUT_DIR.parent) if parent_dir.is_absolute() else parent_dir
             return f"Error: Cannot create parent directory 'outputs/{relative_parent_err}' (resolves outside allowed area)."
        parent_dir.mkdir(parents=True, exist_ok=True)

        # Check if file existed and had content *before* opening in append mode
        file_existed_and_had_content = target_path.exists() and target_path.stat().st_size > 0

        # Open in append mode ('a')
        with open(target_path, 'a', encoding='utf-8') as f:
            # Add a newline before appending only if the file already existed and wasn't empty
            if file_existed_and_had_content:
                 f.write("\n") # Add separator
            f.write(content_to_append)

        print(f"Filesystem Tool: Successfully appended {len(content_to_append)} characters to {target_path}")
        relative_path_out = target_path.relative_to(OUTPUT_DIR) if target_path.is_absolute() else file_path_str
        return f"Successfully appended content to file: outputs/{relative_path_out}"

    except Exception as e:
        print(f"Filesystem Tool Error (Append): Failed for path '{file_path_str}'. Error: {e}")
        traceback.print_exc()
        relative_display_path = Path(file_path_str).name
        return f"Error appending to file '{relative_display_path}'. Details: {str(e)}"
    




# --- NEW FUNCTION: Replace Text in File ---
def replace_text_in_file(input_str: str) -> str:
    """
    Reads a file within 'outputs', replaces all occurrences of a specific text
    string with another string, and saves the modified content back to the same file.
    Input format: 'relative/path/to/file.txt|TEXT_TO_FIND|TEXT_TO_REPLACE_WITH'
    Uses case-sensitive replacement. Counts occurrences replaced.
    """
    print(f"Filesystem Tool: Attempting text replacement: '{input_str[:100]}...'")
    try:
        parts = input_str.split('|', 2)
        if len(parts) != 3:
            return ("Error: Input must be 'filepath|text_to_find|text_to_replace_with'. "
                    "Use pipe '|' as separator. Example: 'notes.txt|old_value|new_value'")

        file_path_str, text_to_find, text_to_replace_with = parts[0].strip(), parts[1], parts[2] # Keep original case for find/replace text

        if not text_to_find: # Prevent replacing nothing, could lead to large file growth if replacement is long
            return "Error: 'text_to_find' cannot be empty."

        target_path = _resolve_path(file_path_str) # Use the validated helper
        if not target_path:
            return f"Error: Invalid or disallowed file path '{file_path_str}' for modification."

        # Ensure file exists and is a file before trying to read/write
        if not target_path.exists():
             relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else file_path_str
             return f"Error: File not found at resolved path: {relative_err_path}"
        if not target_path.is_file():
             relative_err_path = target_path.relative_to(OUTPUT_DIR.parent) if target_path.is_absolute() else file_path_str
             return f"Error: Path exists but is not a file: {relative_err_path}"

        # Read the entire file content
        print(f"Filesystem Tool (Replace): Reading content from {target_path}")
        original_content = target_path.read_text(encoding='utf-8', errors='ignore')

        # Perform the replacement
        modified_content = original_content.replace(text_to_find, text_to_replace_with)
        replacement_count = original_content.count(text_to_find) # Count occurrences in original

        # Check if any changes were actually made
        if original_content == modified_content:
            print(f"Filesystem Tool (Replace): Text '{text_to_find}' not found in {target_path}. File unchanged.")
            return f"Success: Text '{text_to_find}' not found in file 'outputs/{target_path.relative_to(OUTPUT_DIR)}'. No changes made."
        else:
            # Write the modified content back, overwriting the original file
            print(f"Filesystem Tool (Replace): Writing modified content back to {target_path}")
            target_path.write_text(modified_content, encoding='utf-8')
            print(f"Filesystem Tool (Replace): Successfully replaced {replacement_count} occurrence(s).")
            return (f"Success: Replaced {replacement_count} occurrence(s) of '{text_to_find}' "
                    f"with '{text_to_replace_with}' in file 'outputs/{target_path.relative_to(OUTPUT_DIR)}'.")



    except Exception as e:
        print(f"Filesystem Tool Error (Replace): Failed for path '{file_path_str}'. Error: {e}")
        traceback.print_exc()
        relative_display_path = Path(file_path_str).name
        return f"Error replacing text in file '{relative_display_path}'. Details: {str(e)}"


# --- ADDED FUNCTION: Write Python Script (SCRIPTS DIR ONLY) ---
def write_python_script(path_and_code: str) -> str:
    """
    Writes Python code to a specified .py file within the designated 'scripts' directory.
    Input format: 'relative/path/to/script.py|Python code content'.
    Creates subdirectories within 'scripts' if needed. Overwrites existing files.
    Decodes standard Python escape sequences (like \\n) in the code content.
    """
    print(f"Filesystem Tool: Attempting write PYTHON SCRIPT: '{path_and_code[:100]}...'")
    try:
        parts = path_and_code.split('|', 1)
        if len(parts) != 2: return "Error: Input must be 'script_path.py|python_code'."
        script_path_str, code_raw = parts[0].strip(), parts[1]

        target_path = _resolve_scripts_path(script_path_str) # Use scripts helper
        if not target_path: return f"Error: Invalid/disallowed script path '{script_path_str}'. Must be relative .py in 'scripts/'."

        try: code_content = codecs.decode(code_raw, 'unicode_escape')
        except Exception as de: print(f"Warn (Script): Decode fail: {de}"); code_content = code_raw

        if target_path.exists() and target_path.is_dir(): return f"Error: Cannot write script. Path '{target_path.relative_to(PROJECT_ROOT)}' exists and is directory."

        parent_dir = target_path.parent
        if not (parent_dir == SCRIPT_DIR or parent_dir.is_relative_to(SCRIPT_DIR)): return f"Error: Cannot create parent dir '{parent_dir.relative_to(PROJECT_ROOT)}' outside 'scripts/'."
        parent_dir.mkdir(parents=True, exist_ok=True)

        target_path.write_text(code_content, encoding='utf-8')
        relative_path_out = target_path.relative_to(PROJECT_ROOT)
        print(f"Filesystem Tool: Wrote {len(code_content)} chars Python code to {target_path}")
        return f"Successfully wrote Python script to: {relative_path_out}"

    except Exception as e:
        print(f"FS Script Error '{script_path_str}': {e}"); traceback.print_exc()
        return f"Error writing Python script '{Path(script_path_str).name}': {str(e)}"
# --- END ADDED FUNCTION ---

# --- LangChain Tool Definitions ---

read_file_tool = Tool(
    name="Read File Content",
    func=read_file,
    description=(
        f"Use this tool to read the text content of a specific file located within the '{OUTPUT_DIR.name}' directory. "
        f"Input MUST be the relative path to the file inside '{OUTPUT_DIR.name}'. Example: 'results/data.txt' or 'summary.md'. "
        f"Do NOT use absolute paths or path traversal ('..'). The path must resolve to within '{OUTPUT_DIR.name}'. "
        "Output is the text content of the file (potentially truncated if very large) or an error message."
    ),
)

write_file_tool = Tool(
    name="Write Text to File",
    func=write_file,
    description=(
        f"Use this tool to write or overwrite text content to a specific file within the '{OUTPUT_DIR.name}' directory. "
        f"Input MUST be the relative file path inside '{OUTPUT_DIR.name}', followed by a pipe separator '|', then the text content. "
        f"Use standard newline characters (like \\n in the source text) for line breaks. "
        f"Example: 'report.txt|## Analysis\\n- Point 1'. "
        f"The file path must be relative to '{OUTPUT_DIR.name}' and include a filename. Do NOT use absolute paths or '..'. "
        f"Parent directories within '{OUTPUT_DIR.name}' will be created automatically. "
        f"**Important**: This tool OVERWRITES existing files without confirmation. "
        f"Output confirms success (including the relative path 'outputs/...') or provides an error message."
    ),
)

list_directory_tool = Tool(
    name="List Directory Contents",
    func=list_directory,
    description=(
        f"Use this tool to list files and subdirectories within a specific directory inside the '{OUTPUT_DIR.name}' folder. "
        f"Input is the relative path to the target directory inside '{OUTPUT_DIR.name}'. Example: '.' lists the root of '{OUTPUT_DIR.name}', 'data_files' lists 'outputs/data_files'. "
        f"Do NOT use absolute paths or path traversal ('..'). "
        f"Output is a list of item names with their type (FILE/DIR), showing the contents of the requested 'outputs/...' path, or an error message."
    ),
)
append_file_tool = Tool(
    name="Append Text to File",
    func=append_text_to_file, # Reference the function defined above
    description=(
        f"Use this tool to add text content to the END of an existing file within the '{OUTPUT_DIR.name}' directory, or create a new file if it doesn't exist. "
        f"Input MUST be the relative file path **inside the '{OUTPUT_DIR.name}' directory**, followed by a pipe separator '|', then the text content to append. "
        f"Example: 'logs/daily_log.txt|New log entry details.' "
        f"The file path must be relative to '{OUTPUT_DIR.name}'. Do NOT use absolute paths or '..'. "
        f"Parent directories within '{OUTPUT_DIR.name}' will be created if needed. "
        f"Use this for adding to logs, accumulating notes, etc. without overwriting existing content. A newline is often added before appending to existing content. "
        f"Output confirms success (including the relative path 'outputs/...') or provides an error message."
    ),
)
# --- NEW TOOL DEFINITION ---
replace_text_tool = Tool(
    name="Replace Text in File",
    func=replace_text_in_file,
    description=(
        f"Use this tool to find all occurrences of a specific text string within a file in the '{OUTPUT_DIR.name}' directory and replace them with another text string. "
        f"Input MUST be exactly three parts separated by pipes '|': 'relative/path/to/file.txt|TEXT_TO_FIND|TEXT_TO_REPLACE_WITH'. "
        f"Example: 'config.txt|localhost|production.server.com'. "
        f"The file path must be relative to '{OUTPUT_DIR.name}'. Do NOT use absolute paths or '..'. "
        f"The 'TEXT_TO_FIND' cannot be empty. The replacement is case-sensitive. "
        f"This tool reads the file, performs all replacements in memory, and then overwrites the original file with the modified content. "
        f"Use this for tasks like updating values, correcting typos, or changing specific terms within a text file. "
        f"Output confirms success (reporting number of replacements) or provides an error message."
    ),
)
# --- Definition for Writing Scripts ---
write_script_tool = Tool( name="Write Python Script", func=write_python_script, description=f"Writes Python code to '.py' file inside '{SCRIPT_DIR.name}/'. Input: 'relative/script.py|code'. Use '\\n'. OVERWRITES. Use this BEFORE executing with terminal tool.")