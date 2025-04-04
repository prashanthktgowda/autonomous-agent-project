# tools/delete_file_tool.py
import os
from pathlib import Path
from langchain.tools import Tool
import traceback # For detailed error logging

# --- Define Output Directory ---
# Ensure this is consistent with other tool files and resolved correctly
try:
    # Assuming the script is run from the project root where 'outputs' exists
    # Or that OUTPUT_DIR is reliably set elsewhere if imported differently
    OUTPUT_DIR = Path("outputs").resolve()
    # Ensure the base output directory exists (optional here, but good practice)
    # OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"CRITICAL ERROR in delete_file_tool.py: Failed to resolve OUTPUT_DIR. Error: {e}")
    # Fallback or raise error depending on desired behavior
    OUTPUT_DIR = Path("outputs") # Simple fallback

print(f"DEBUG [delete_file_tool.py]: OUTPUT_DIR resolved to: {OUTPUT_DIR}")


# --- Helper Function for Safe Path Resolution ---
def _resolve_path_for_delete(file_path: str) -> Path | None:
    """
    Helper to safely resolve paths relative to OUTPUT_DIR for deletion requests.
    Returns the resolved Path object or None if invalid/unsafe.
    """
    if not isinstance(file_path, str):
        print(f"Delete Tool Path Error: Input path must be a string, got {type(file_path)}")
        return None

    cleaned_path = file_path.strip().replace("\\", "/")
    if not cleaned_path:
         print("Delete Tool Path Error: Input path string is empty.")
         return None

    # Prevent accessing parent directories or absolute paths outside OUTPUT_DIR
    if cleaned_path.startswith("/") or ".." in cleaned_path.split("/"):
        print(f"Delete Tool Security Error: Access denied to path '{file_path}'. Only paths relative to the '{OUTPUT_DIR.name}' directory are allowed.")
        return None

    # Create the full path relative to the OUTPUT_DIR
    target_path = (OUTPUT_DIR / cleaned_path).resolve()

    # Final check: ensure the resolved path is still within OUTPUT_DIR
    try:
        # is_relative_to checks if target_path is OUTPUT_DIR or a subdirectory of it
        if not target_path.is_relative_to(OUTPUT_DIR):
            print(f"Delete Tool Security Error: Resolved path '{target_path}' is outside the allowed directory '{OUTPUT_DIR}'. Deletion denied.")
            return None
    except ValueError: # is_relative_to raises ValueError if paths are on different drives (Windows) or unrelated
        print(f"Delete Tool Security Error: Cannot compare path '{target_path}' with allowed directory '{OUTPUT_DIR}' (unrelated paths?). Deletion denied.")
        return None
    except Exception as e: # Catch any other resolution errors
        print(f"Delete Tool Path Error: Unexpected error resolving path '{target_path}'. Error: {e}")
        return None

    return target_path

# --- LangChain Tool Function (Requests Confirmation - DOES NOT DELETE) ---
def request_delete_confirmation(file_path: str) -> str:
    """
    Identifies a file for potential deletion based on user request to the agent.
    Verifies the path and file existence within the allowed 'outputs' directory.
    Returns a special string ('CONFIRM_DELETE|relative_path') indicating confirmation
    is needed from the user via the UI/CLI, or an error message for the agent.
    Input should be the relative path inside the 'outputs' directory.
    """
    print(f"DEBUG [delete_file_tool.py]: Agent requested delete confirmation for raw path: '{file_path}'")
    resolved_target_path = _resolve_path_for_delete(file_path)

    if not resolved_target_path:
        # Inform the agent the path is invalid/disallowed
        # The error reason is printed by _resolve_path_for_delete
        return f"Error: Invalid or disallowed file path '{file_path}' provided for deletion request."

    print(f"DEBUG [delete_file_tool.py]: Resolved path for delete request: {resolved_target_path}")

    # Check existence and type *after* resolving the path
    if not resolved_target_path.exists():
        print(f"DEBUG [delete_file_tool.py]: File not found at {resolved_target_path}")
        # Inform the agent the file doesn't exist
        return f"Error: File '{file_path}' not found at resolved path {resolved_target_path}, cannot request deletion."

    if not resolved_target_path.is_file():
         print(f"DEBUG [delete_file_tool.py]: Path {resolved_target_path} is not a file.")
         # Inform the agent it's not a file
         try:
             return f"Error: Path '{file_path}' (resolved to {resolved_target_path}) is not a file, cannot request deletion."
         except Exception as e:
             print(f"Unexpected error while processing non-file path: {e}")
             traceback.print_exc()
             return f"Error: Internal error occurred while handling path '{file_path}'."

    # If path is valid, exists, and is a file, return confirmation request string
    try:
        # Get the path relative to OUTPUT_DIR for use in the confirmation message
        relative_path_str = str(resolved_target_path.relative_to(OUTPUT_DIR))
        confirmation_string = f"CONFIRM_DELETE|{relative_path_str}"
        print(f"DEBUG [delete_file_tool.py]: Returning confirmation request string: {confirmation_string}")
        return confirmation_string
    except ValueError as e:
         # This should theoretically not happen if _resolve_path_for_delete worked, but handle defensively
         print(f"Delete Tool Error: Could not get relative path for {resolved_target_path} relative to {OUTPUT_DIR}. Error: {e}")
         return f"Error: Internal issue resolving relative path for deletion request of '{file_path}'."
    except Exception as e:
         print(f"Delete Tool Error: Unexpected error formatting confirmation string for {resolved_target_path}. Error: {e}")
         traceback.print_exc()
         return f"Error: Internal error processing deletion request for '{file_path}'."


# --- LangChain Tool Definition ---
delete_confirmation_tool = Tool(
    name="Request File Deletion Confirmation",
    func=request_delete_confirmation,
    description=f"""
    Use this tool ONLY when the user explicitly asks the agent to delete a specific file within the designated '{OUTPUT_DIR.name}' directory.
    Input MUST be the relative path of the file inside the '{OUTPUT_DIR.name}' directory that the user wants deleted. Examples: 'report.txt', 'data/archive.zip', 'images/old_logo.png'.
    This tool DOES NOT delete the file directly. It first validates the path and checks if the file exists.
    If valid, it returns a special confirmation request string ('CONFIRM_DELETE|filepath') which requires the user to approve the deletion via the application interface (UI or Command Line). **This tool's output should be treated as the final step for this specific request.**
    If the path is invalid, unsafe, or the file doesn't exist, it returns an error message explaining the problem.
    Do NOT use this tool for listing, reading, or writing files - use other filesystem tools for those tasks.
    Do NOT make up file paths; only use paths mentioned by the user or found using the listing tool.
    """,
    return_direct=True # <--- ADD THIS LINE
)


# --- Function to ACTUALLY Delete File (Called ONLY by app.py or main.py AFTER confirmation) ---
# This function is intentionally NOT exposed as a tool to the LLM agent for safety.
def perform_delete(full_path_str: str) -> tuple[bool, str]:
    """
    Deletes the file at the given absolute path string AFTER user confirmation in the UI/CLI.
    Performs final safety checks to ensure path is within the allowed directory.
    Returns a tuple: (success_boolean, message_string).
    """
    print(f"--- Attempting to perform confirmed deletion for: {full_path_str} ---")
    if not isinstance(full_path_str, str) or not full_path_str:
         print(f"Perform Delete Error: Invalid input path string.")
         return False, "Error: Invalid path provided for deletion."

    try:
        # Resolve the path again to handle any symbolic links etc. consistently
        target_path = Path(full_path_str).resolve()
        print(f"DEBUG [perform_delete]: Resolved target path: {target_path}")

        # --- CRITICAL FINAL SAFETY CHECK ---
        # Ensure the resolved path is definitely within the designated OUTPUT_DIR.
        if not target_path.is_relative_to(OUTPUT_DIR):
             print(f"CRITICAL SECURITY ERROR: Attempt to delete file outside designated directory detected in perform_delete!")
             print(f"   Target Path: {target_path}")
             print(f"   Allowed Dir: {OUTPUT_DIR}")
             # Do NOT proceed with deletion.
             return False, f"Security Error: Deletion denied. Path '{target_path.name}' is outside the allowed '{OUTPUT_DIR.name}' directory."

        # Check existence and type again right before deletion
        if target_path.exists():
            if target_path.is_file():
                # --- Perform the actual deletion ---
                target_path.unlink()
                print(f"--- Successfully deleted file: {target_path} ---")
                # Return the base filename in the success message for clarity
                return True, f"File '{target_path.name}' deleted successfully."
            else:
                # Path exists but is not a file (e.g., a directory)
                print(f"--- Deletion failed: Path exists but is not a file: {target_path} ---")
                return False, f"Error: Cannot delete - path '{target_path.name}' is not a file."
        else:
            # File doesn't exist (might have been deleted between confirmation and this call)
             print(f"--- Deletion failed: File not found at {target_path} (already deleted?) ---")
             return False, f"Error: File '{target_path.name}' not found (maybe it was already deleted?)."

    # --- Specific Exception Handling ---
    except PermissionError as pe:
        print(f"--- Deletion Error (Permission Denied): {pe} ---")
        traceback.print_exc()
        # Extract filename for user-friendly message
        file_name = Path(full_path_str).name
        return False, f"Error: Permission denied when trying to delete '{file_name}'."
    except OSError as oe:
        # Catch other OS-level errors (e.g., file in use on Windows)
        print(f"--- Deletion Error (OS Error): {oe} ---")
        traceback.print_exc()
        file_name = Path(full_path_str).name
        return False, f"Error: Operating system error occurred while deleting '{file_name}': {oe}"
    except Exception as e:
        # Catch any other unexpected errors during deletion
        print(f"--- Deletion Error (Unexpected): {type(e).__name__} - {e} ---")
        traceback.print_exc()
        file_name = Path(full_path_str).name
        return False, f"An unexpected error occurred while deleting '{file_name}': {e}"