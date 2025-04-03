# autonomous-agent-project/tools/filesystem_tool.py

import os
from pathlib import Path
from langchain.tools import Tool
import shutil # Keep for potential future use (delete/move), though not used now.
import codecs # IMPORT codecs for handling escape sequences

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

# --- Path Safety Helper Functions ---

def _is_path_within_output_dir(path_to_check: Path) -> bool:
    """Check if the resolved path is safely within the OUTPUT_DIR."""
    try:
        # Ensure the path exists or its parent exists before resolving fully
        # Resolving a non-existent path can sometimes behave unexpectedly
        base = path_to_check.parent if not path_to_check.exists() else path_to_check
        # Resolve potentially relative paths or symlinks to get the absolute path
        resolved_path = base.resolve(strict=False) # strict=False allows resolving non-existent paths

        # The critical check: is the resolved path a subpath of OUTPUT_DIR?
        # Use is_relative_to available in Python 3.9+
        return resolved_path.is_relative_to(OUTPUT_DIR)
    except (ValueError, OSError, FileNotFoundError):
        # ValueError for different drives on Windows, OSError for permission issues,
        # FileNotFoundError could happen during resolution in edge cases
        return False
    except Exception: # Catch other potential resolution errors
        return False

def _resolve_safe_path(relative_path_str: str) -> Path | None:
    """
    Resolves a relative path string ensuring it stays within OUTPUT_DIR.
    Returns the combined Path object (relative to cwd, but pointing inside outputs) or None if unsafe.
    """
    # Clean the input path string
    cleaned_path = relative_path_str.strip().replace("\\", "/").lstrip("/")

    # Prevent direct use of '..' for traversal attempts in the input string itself
    if ".." in cleaned_path.split("/"):
        print(f"Filesystem Tool Security Error: Path traversal ('..') detected in input string '{relative_path_str}'. Access denied.")
        return None

    # Combine with OUTPUT_DIR - this path object itself is what we'll operate on if checks pass
    target_path = OUTPUT_DIR / cleaned_path

    # Verify the potentially resolved path is truly inside OUTPUT_DIR using resolve()
    # This handles cases where parts of the path might be symlinks etc.
    try:
         # Resolve fully to check destination, even if path doesn't exist yet
         resolved_target = target_path.resolve(strict=False)
         if resolved_target.is_relative_to(OUTPUT_DIR):
              # Additional check for safety: If the immediate parent doesn't resolve within OUTPUT_DIR, deny.
              # This helps prevent certain symlink tricks if strict=False is used.
              # We need to check if the parent *exists* before resolving it strictly
              resolved_parent = resolved_target.parent
              if resolved_parent.exists() and not resolved_parent.resolve(strict=True).is_relative_to(OUTPUT_DIR):
                   print(f"Filesystem Tool Security Error: Parent directory of resolved path '{resolved_target}' resolves outside '{OUTPUT_DIR}'. Input '{relative_path_str}'.")
                   return None
              # If all checks pass, return the original, potentially non-resolved target path
              # This avoids issues if intermediate dirs need creation by write_text/mkdir
              return target_path
         else:
              print(f"Filesystem Tool Security Error: Resolved path '{resolved_target}' is outside the allowed directory '{OUTPUT_DIR}'. Input was '{relative_path_str}'.")
              return None
    except (ValueError, OSError, FileNotFoundError) as e:
        print(f"Filesystem Tool Security Error: Could not safely resolve path '{relative_path_str}' relative to '{OUTPUT_DIR}'. Error: {e}")
        return None
    except Exception as e: # Catch other unexpected errors during resolution
        print(f"Filesystem Tool Security Error: Unexpected error resolving path '{relative_path_str}'. Error: {e}")
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
        # Resolve strictly here to ensure the file actually exists before reading
        # and perform the final safety check on the resolved path
        resolved_target_for_read = target_path.resolve(strict=True)
        if not _is_path_within_output_dir(resolved_target_for_read):
             # Should be caught by _resolve_safe_path, but double check after strict resolution
             return f"Error: Resolved file path '{resolved_target_for_read}' is outside allowed directory."

        if not resolved_target_for_read.is_file():
             return f"Error: Path exists but is not a file: {resolved_target_for_read}"

        # Read the content
        content = resolved_target_for_read.read_text(encoding='utf-8', errors='ignore')
        print(f"Filesystem Tool: Read {len(content)} characters from {resolved_target_for_read}")

        # Limit output size to prevent overwhelming LLM context
        max_len = 4000 # Adjust as needed
        if len(content) > max_len:
            print(f"Filesystem Tool: Truncating content from {len(content)} to {max_len} chars.")
            truncated_content = content[:max_len] + "\n... (truncated)"
            return truncated_content
        return content

    except FileNotFoundError:
        # Give path relative to project root for clarity
        return f"Error: File not found at path: {target_path}"
    except IsADirectoryError:
         return f"Error: Specified path is a directory, not a file: {target_path}"
    except Exception as e:
        print(f"Filesystem Tool Error: Failed to read {target_path}. Error: {e}")
        return f"Error: Could not read file '{file_path}'. Reason: {str(e)}"


def write_file(path_and_content: str) -> str:
    """
    Writes content to a file within the designated 'outputs' directory.
    Input format: 'relative/path/to/file.txt|Content to write'.
    Creates directories if they don't exist within 'outputs'. Overwrites existing files.
    Interprets literal '\\n' in content as newline characters.
    """
    print(f"Filesystem Tool: Attempting to write file based on input: '{path_and_content[:100]}...'") # Log start of input
    try:
        # Safely split the input string
        if '|' not in path_and_content:
            return "Error: Input must be in the format 'filepath|content'. Pipe separator '|' is missing."
        # Split only once on the first pipe
        file_path_str, content_raw = path_and_content.split('|', 1)

        # --- DECODE ESCAPE SEQUENCES ---
        try:
            # Decode standard Python string escapes like \n, \t, etc.
            content = codecs.decode(content_raw, 'unicode_escape')
        except Exception as decode_err:
            print(f"Filesystem Tool Warning: Could not unicode-escape decode content, writing raw content. Error: {decode_err}")
            content = content_raw # Fallback to using the original raw content
        # --- END DECODE ESCAPE SEQUENCES ---

        # Validate and get the target path (doesn't need to exist yet)
        target_path = _resolve_safe_path(file_path_str)
        if not target_path:
            return f"Error: Invalid or disallowed file path '{file_path_str}' for writing."

        # Prevent writing directly to the output directory itself
        # Need to resolve first to compare accurately with resolved OUTPUT_DIR
        if target_path.resolve(strict=False) == OUTPUT_DIR:
            return f"Error: Cannot write directly to the root 'outputs' directory path. Please specify a filename."

        # Prevent writing if the target path resolves to an existing directory
        if target_path.exists() and target_path.is_dir():
             # Use relative path in error for user clarity
             relative_err_path = target_path.relative_to(OUTPUT_DIR) if _is_path_within_output_dir(target_path) else target_path
             return f"Error: Cannot write file. Path 'outputs/{relative_err_path}' already exists and is a directory."


        # Create parent directories safely *before* writing
        parent_dir = target_path.parent
        # Check parent safety again *before* creating
        if not _is_path_within_output_dir(parent_dir.resolve(strict=False)):
             # Use relative path in error
             relative_parent_err = parent_dir.relative_to(OUTPUT_DIR.parent) if parent_dir.is_absolute() else parent_dir
             return f"Error: Cannot create parent directory 'outputs/{relative_parent_err}' as it resolves outside the allowed 'outputs' directory."
        parent_dir.mkdir(parents=True, exist_ok=True)

        # Write the potentially decoded content
        target_path.write_text(content, encoding='utf-8') # Use the 'content' variable
        print(f"Filesystem Tool: Successfully wrote {len(content)} characters to {target_path}")

        # Return relative path from 'outputs' for clarity in agent observation
        relative_path_out = target_path.relative_to(OUTPUT_DIR)
        return f"Successfully wrote content to file: outputs/{relative_path_out}"

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
         # Resolve strictly here to ensure directory exists before listing
         # and perform the final safety check on the resolved path
         resolved_target_for_list = target_path.resolve(strict=True)
         if not _is_path_within_output_dir(resolved_target_for_list):
              # Should be caught by _resolve_safe_path, but double check
              return f"Error: Resolved directory path '{resolved_target_for_list}' is outside allowed directory."

         if not resolved_target_for_list.is_dir():
             # Use relative path in error
             relative_err_path = resolved_target_for_list.relative_to(OUTPUT_DIR) if _is_path_within_output_dir(resolved_target_for_list) else resolved_target_for_list
             return f"Error: Specified path 'outputs/{relative_err_path}' is not a directory."

         items = []
         # Iterate and get names + type
         for item in sorted(resolved_target_for_list.iterdir()): # Sort for consistent order
             # Check safety of each item's path before adding (e.g., against symlinks pointing outside)
             if not _is_path_within_output_dir(item.resolve(strict=False)):
                  print(f"Filesystem Tool Warning: Skipping item '{item.name}' as it resolves outside 'outputs'.")
                  continue
             item_type = "DIR" if item.is_dir() else "FILE"
             items.append(f"{item.name} ({item_type})")

         print(f"Filesystem Tool: Found {len(items)} listable items in {resolved_target_for_list}")

         # Use original target_path for relative display (might be '.')
         # Ensure it's displayed relative to outputs
         relative_display_path = target_path.relative_to(OUTPUT_DIR) if target_path.is_absolute() and _is_path_within_output_dir(target_path) and target_path != OUTPUT_DIR else Path(directory_path_str)
         # Special case for root
         if str(relative_display_path) == '.':
             display_root = 'outputs/'
         else:
             display_root = f'outputs/{relative_display_path}/'


         if not items:
              return f"Directory '{display_root}' is empty."
         else:
              # Limit number of items listed to avoid large output
              max_items = 50
              if len(items) > max_items:
                  items_list = "\n".join(items[:max_items]) + f"\n... (truncated, {len(items)-max_items} more items exist)"
              else:
                  items_list = "\n".join(items)
              return f"Contents of directory '{display_root}':\n{items_list}"

    except FileNotFoundError:
         # Use relative path in error
         relative_err_path = target_path.relative_to(OUTPUT_DIR) if _is_path_within_output_dir(target_path) else target_path
         return f"Error: Directory not found at path: 'outputs/{relative_err_path}'"
    except NotADirectoryError:
          # Use relative path in error
          relative_err_path = target_path.relative_to(OUTPUT_DIR) if _is_path_within_output_dir(target_path) else target_path
          return f"Error: Specified path 'outputs/{relative_err_path}' is a file, not a directory."
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
        "**Before calling this tool, ensure the text content you provide is well-organized and clearly formatted** using headings, bullet points, or numbered lists where appropriate, based on the user's request or the nature of the data. Use standard newline characters (like \\n in the source text) for line breaks. " # Updated hint
        "Example: 'report.txt|## Analysis\\n\\n- Point 1\\n- Point 2\\n\\n## Conclusion\\n...' "
        "or 'data/log_entries.txt|Timestamp: ... Event: ...\\nTimestamp: ... Event: ...'. "
        "The file path must be relative to the 'outputs' directory. Do NOT use absolute paths or '..'. "
        "Parent directories within 'outputs' will be created automatically if needed. "
        "This will overwrite the file if it already exists. "
        "Output confirms success (including the relative path 'outputs/...') or provides an error message."
    ),
)

list_directory_tool = Tool(
    name="List Directory Contents",
    func=list_directory,
    description=(
        "Use this tool to list files and subdirectories within a specific directory "
        "**inside the 'outputs' folder**. "
        "Input is the relative path to the target directory inside 'outputs'. "
        "Example: '.' lists the root of 'outputs', 'data_files' lists 'outputs/data_files'. "
        "Do NOT use absolute paths or path traversal ('..'). "
        "Output is a list of item names with their type (FILE/DIR) or an error message. The listed path will start with 'outputs/'."
    ),
)

# Optional: Add delete or move tools here if absolutely necessary for the assignment,
# but include EXTREME caution notes in their descriptions. Remember to add to planner.py if used.
# def delete_file_or_dir(path_str: str) -> str:
#     # ... (Implementation with strict safety checks using _resolve_safe_path) ...
# delete_tool = Tool( name="Delete File or Directory", func=delete_file_or_dir, description="**USE WITH EXTREME CAUTION!** ...")