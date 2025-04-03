# autonomous-agent-project/tools/filesystem_tool.py

import os
from pathlib import Path
from langchain.tools import Tool
import shutil # Keep for potential future use (delete/move), though not used now.

# Define the designated output directory relative to the project root
# .resolve() makes it an absolute path for reliable comparison later.
OUTPUT_DIR = Path("outputs").resolve()

# Ensure the output directory exists when the script loads
try:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
except OSError as e:
    print(f"[CRITICAL] Could not create mandatory output directory {OUTPUT_DIR}. Error: {e}")
    # Depending on desired behavior, you might want to raise the error here
    # raise

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


def _resolve_safe_path(relative_path_str: str) -> Path | None:
    """
    Resolves a relative path string ensuring it stays within OUTPUT_DIR.
    Returns the resolved Path object or None if unsafe.
    """
    # Clean the input path string
    cleaned_path = relative_path_str.strip().replace("\\", "/").lstrip("/")

    # Prevent direct use of '..' for traversal attempts
    if ".." in cleaned_path.split("/"):
        print(f"Filesystem Tool Security Error: Path traversal ('..') detected in '{relative_path_str}'. Access denied.")
        return None

    # Combine with OUTPUT_DIR and resolve
    # This handles symlinks and makes the path absolute for comparison
    target_path = (OUTPUT_DIR / cleaned_path).resolve()

    # Verify the resolved path is truly inside OUTPUT_DIR
    if _is_path_within_output_dir(target_path):
         # Check one level up too, in case target_path doesn't exist yet but its parent does
         if target_path.parent.exists() and not _is_path_within_output_dir(target_path.parent):
              print(f"Filesystem Tool Security Error: Parent directory of resolved path '{target_path}' is outside the allowed directory '{OUTPUT_DIR}'.")
              return None
         return target_path
    else:
        print(f"Filesystem Tool Security Error: Resolved path '{target_path}' is outside the allowed directory '{OUTPUT_DIR}'. Input was '{relative_path_str}'.")
        return None


# --- Core Filesystem Functions ---

def read_file(file_path: str) -> str:
    """
    Reads the content of a file within the designated 'outputs' directory.
    Input: Relative path string within the 'outputs' directory.
    """
    print(f"Filesystem Tool: Attempting to read file: '{file_path}'")
    target_path = _resolve_safe_path(file_path)
    if not target_path:
        return f"Error: Invalid or disallowed file path '{file_path}' for reading."

    try:
        if not target_path.exists():
            return f"Error: File not found at calculated path: {target_path}"
        if not target_path.is_file():
             return f"Error: Path exists but is not a file: {target_path}"

        # Read the content
        content = target_path.read_text(encoding='utf-8', errors='ignore')
        print(f"Filesystem Tool: Read {len(content)} characters from {target_path}")

        # Limit output size to prevent overwhelming LLM context
        max_len = 4000 # Adjust as needed
        if len(content) > max_len:
            print(f"Filesystem Tool: Truncating content from {len(content)} to {max_len} chars.")
            truncated_content = content[:max_len] + "\n... (truncated)"
            return truncated_content
        return content

    except Exception as e:
        print(f"Filesystem Tool Error: Failed to read {target_path}. Error: {e}")
        # Provide a more informative error message back to the agent
        return f"Error: Could not read file '{file_path}'. Reason: {str(e)}"


def write_file(path_and_content: str) -> str:
    """
    Writes content to a file within the designated 'outputs' directory.
    Input format: 'relative/path/to/file.txt|Content to write'.
    Creates directories if they don't exist within 'outputs'. Overwrites existing files.
    """
    print(f"Filesystem Tool: Attempting to write file based on input: '{path_and_content[:100]}...'") # Log start of input
    try:
        # Safely split the input string
        if '|' not in path_and_content:
            return "Error: Input must be in the format 'filepath|content'. Pipe separator '|' is missing."
        file_path_str, content = path_and_content.split('|', 1)

        # Validate and resolve the path safely
        target_path = _resolve_safe_path(file_path_str)
        if not target_path:
            return f"Error: Invalid or disallowed file path '{file_path_str}' for writing."

        # Prevent writing directly to the output directory itself (treat as file)
        if target_path == OUTPUT_DIR:
            return f"Error: Cannot write directly to the root 'outputs' directory path. Please specify a filename."

        # Create parent directories if they don't exist (within the safe path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the content
        target_path.write_text(content, encoding='utf-8')
        print(f"Filesystem Tool: Successfully wrote {len(content)} characters to {target_path}")
        return f"Successfully wrote content to file: {target_path.relative_to(OUTPUT_DIR)}" # Return relative path

    except Exception as e:
        print(f"Filesystem Tool Error: Failed to write to path derived from '{file_path_str}'. Error: {e}")
        # Provide a more informative error message back to the agent
        return f"Error: Could not write file '{file_path_str}'. Reason: {str(e)}"


def list_directory(directory_path_str: str = ".") -> str:
    """
    Lists the contents of a directory within the designated 'outputs' directory.
    Input: Relative path string within 'outputs', or '.' for the root of 'outputs'.
    """
    print(f"Filesystem Tool: Attempting to list directory: '{directory_path_str}'")
    target_path = _resolve_safe_path(directory_path_str)
    if not target_path:
        return f"Error: Invalid or disallowed directory path '{directory_path_str}' for listing."

    try:
        if not target_path.exists():
            return f"Error: Directory not found: {target_path}"
        if not target_path.is_dir():
            return f"Error: Specified path is not a directory: {target_path}"

        items = []
        # Iterate and get names + type
        for item in sorted(target_path.iterdir()): # Sort for consistent order
            item_type = "DIR" if item.is_dir() else "FILE"
            items.append(f"{item.name} ({item_type})")

        print(f"Filesystem Tool: Found {len(items)} items in {target_path}")

        relative_display_path = target_path.relative_to(OUTPUT_DIR) if target_path != OUTPUT_DIR else '.'

        if not items:
             return f"Directory '{relative_display_path}' within 'outputs' is empty."
        else:
             # Limit number of items listed to avoid large output
             max_items = 50
             if len(items) > max_items:
                 items_list = "\n".join(items[:max_items]) + f"\n... (truncated, {len(items)-max_items} more items exist)"
             else:
                 items_list = "\n".join(items)
             return f"Contents of directory '{relative_display_path}' within 'outputs':\n{items_list}"

    except Exception as e:
        print(f"Filesystem Tool Error: Failed to list directory {target_path}. Error: {e}")
        # Provide a more informative error message back to the agent
        return f"Error: Could not list directory '{directory_path_str}'. Reason: {str(e)}"


# --- LangChain Tool Definitions ---
# These are the names imported by agent/planner.py

read_file_tool = Tool(
    name="Read File Content",
    func=read_file,
    description=(
        "Use this tool to read the text content of a specific file. "
        "The input MUST be the relative path to the file **inside the 'outputs' directory**. "
        "Example: 'results/data.txt' or 'summary.md'. "
        "Do NOT use absolute paths (like '/home/user/...') or path traversal ('..'). "
        "Output is the text content of the file or an error message if the file cannot be read."
    ),
)

write_file_tool = Tool(
    name="Write Text to File",
    func=write_file,
    description=(
        "Use this tool to write or overwrite text content to a specific file. "
        "The input MUST be the relative file path **inside the 'outputs' directory**, "
        "followed by a pipe separator '|', then the text content to write. "
        "Example: 'report.txt|This is the report content.' "
        "or 'data/log_entries.txt|Timestamp: ... Event: ...'. "
        "The file path must be relative to the 'outputs' directory. "
        "Do NOT use absolute paths or path traversal ('..'). "
        "Parent directories within 'outputs' will be created automatically if needed. "
        "This will overwrite the file if it already exists. "
        "Output confirms success or provides an error message."
    ),
)

list_directory_tool = Tool(
    name="List Directory Contents",
    func=list_directory,
    description=(
        "Use this tool to list files and subdirectories within a specific directory "
        "**inside the 'outputs' folder**. "
        "Input is the relative path to the target directory inside 'outputs'. "
        "Example: '.' lists the root of 'outputs', 'data_files' lists './outputs/data_files'. "
        "Do NOT use absolute paths or path traversal ('..'). "
        "Output is a list of item names with their type (FILE/DIR) or an error message."
    ),
)

# Optional: Add delete or move tools here if absolutely necessary for the assignment,
# but include EXTREME caution notes in their descriptions.
# Example (Use with extreme care):
# def delete_file_or_dir(path_str: str) -> str:
#     print(f"Filesystem Tool: Attempting to delete: '{path_str}'")
#     target_path = _resolve_safe_path(path_str)
#     if not target_path:
#         return f"Error: Invalid or disallowed path '{path_str}' for deletion."
#     if target_path == OUTPUT_DIR:
#          return "Error: Cannot delete the root 'outputs' directory itself."
#     try:
#         if target_path.is_file():
#             target_path.unlink()
#             print(f"Filesystem Tool: Deleted file: {target_path}")
#             return f"Successfully deleted file: {target_path.relative_to(OUTPUT_DIR)}"
#         elif target_path.is_dir():
#             shutil.rmtree(target_path) # DANGEROUS: Recursively deletes directory!
#             print(f"Filesystem Tool: Deleted directory recursively: {target_path}")
#             return f"Successfully deleted directory: {target_path.relative_to(OUTPUT_DIR)}"
#         else:
#             return f"Error: Path exists but is not a file or directory, cannot delete: {target_path}"
#     except Exception as e:
#         print(f"Filesystem Tool Error: Failed to delete {target_path}. Error: {e}")
#         return f"Error: Could not delete '{path_str}'. Reason: {str(e)}"

# delete_tool = Tool(
#     name="Delete File or Directory",
#     func=delete_file_or_dir,
#     description=(
#         "**USE WITH EXTREME CAUTION!** Use this tool to delete a file or an entire directory "
#         "(including its contents) **within the 'outputs' directory**. "
#         "Input is the relative path inside 'outputs'. Example: 'old_report.txt' or 'temporary_data_folder'. "
#         "Do NOT use absolute paths or '..'. Cannot delete the 'outputs' directory itself. "
#         "Deletion is permanent and cannot be undone easily. Double-check the path before using."
#     )
# )
# If you add delete_tool, remember to add it to the `tools` list in `agent/planner.py`.