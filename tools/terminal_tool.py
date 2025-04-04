# tools/terminal_tool.py (Enhanced for Script Execution & Error Handling)

import subprocess
import sys
import shlex # Use shlex for safer command splitting
from langchain.tools import Tool
from pathlib import Path
import traceback
import json # To return structured output

# --- Configuration ---
# Define allowed directories for script execution (relative to project root)
# IMPORTANT: Modify this list based on your project structure and security needs.
# Allowing '.' (project root) can be risky if unrelated scripts exist there.
# Using a dedicated 'scripts' directory is generally safer.
ALLOWED_SCRIPT_DIRS = [Path("."), Path("scripts")]

# Resolve allowed directories to absolute paths for reliable comparison
try:
    PROJECT_ROOT = Path(__file__).parent.parent.resolve() # Get project root directory (tools -> project)
    RESOLVED_ALLOWED_SCRIPT_DIRS = [(PROJECT_ROOT / d).resolve() for d in ALLOWED_SCRIPT_DIRS]
    print(f"DEBUG [terminal_tool.py]: Project Root: {PROJECT_ROOT}")
    print(f"DEBUG [terminal_tool.py]: Allowed Script Dirs (Resolved): {RESOLVED_ALLOWED_SCRIPT_DIRS}")
except Exception as e:
     print(f"CRITICAL ERROR in terminal_tool.py: Could not resolve project root or allowed dirs: {e}")
     # Fallback to prevent crashes, but script execution might fail safety checks
     PROJECT_ROOT = Path(".").resolve()
     RESOLVED_ALLOWED_SCRIPT_DIRS = [PROJECT_ROOT]


# Explicitly allowed basic commands (expand ONLY with extreme caution)
# Avoid commands that modify filesystem broadly (rm, mv), manage users, networking etc.
ALLOWED_COMMANDS = ["ls", "pwd", "echo", "cat", "head", "tail", "grep", "wc", "date"] # Added 'date', 'wc' as examples

# Timeout for commands in seconds
COMMAND_TIMEOUT = 60
# Max length for stdout/stderr to return to agent
MAX_OUTPUT_LENGTH = 3000
# --- End Configuration ---


def _is_script_path_safe(script_path_str: str) -> bool:
    """
    Checks if the script path provided resolves safely within the allowed directories
    and points to an existing file.
    Input: Path string relative to PROJECT_ROOT.
    """
    if not isinstance(script_path_str, str) or not script_path_str:
        print("Terminal Security Err: Script path invalid (not string or empty).")
        return False
    try:
        script_path = Path(script_path_str)
        # --- Security: Disallow absolute paths from agent input ---
        if script_path.is_absolute():
            print(f"Terminal Security Err: Absolute script paths denied: '{script_path_str}'")
            return False
        # --- Security: Disallow path traversal ---
        if ".." in script_path.parts:
            print(f"Terminal Security Err: Path traversal ('..') denied: '{script_path_str}'")
            return False

        # Construct full path relative to project root and resolve it safely
        full_script_path = (PROJECT_ROOT / script_path).resolve()
        print(f"DEBUG [Terminal Safety Check]: Resolving '{script_path_str}' to '{full_script_path}'")

        # Check if the resolved script path is within any of the allowed directories
        is_within_allowed = False
        for allowed_dir in RESOLVED_ALLOWED_SCRIPT_DIRS:
            try:
                 # Check if it's within or equal to the allowed directory
                if full_script_path.is_relative_to(allowed_dir):
                    is_within_allowed = True
                    break # Found a valid parent directory
            except ValueError: # Happens if paths are unrelated (e.g. different drives)
                 continue

        if not is_within_allowed:
            print(f"Terminal Security Err: Script '{script_path_str}' resolves to '{full_script_path}', which is outside allowed directories: {RESOLVED_ALLOWED_SCRIPT_DIRS}")
            return False

        # Final check: ensure the resolved path points to an actual file
        if not full_script_path.is_file():
             print(f"Terminal Security Err: Path resolves safely but is not a file (or doesn't exist): '{full_script_path}'")
             return False

        # If all checks pass
        print(f"DEBUG [Terminal Safety Check]: Script path '{full_script_path}' confirmed safe and exists.")
        return True

    except Exception as e:
        print(f"Terminal Security Err: Error checking script path safety for '{script_path_str}': {e}")
        traceback.print_exc() # Log the full error for debugging
        return False


def run_terminal_command_enhanced(command: str) -> str:
    """
    Executes allowed basic shell commands or designated safe python scripts.
    Returns a JSON string: {"stdout": "...", "stderr": "...", "exit_code": N}.

    !! SECURITY WARNING !! Critical. Execution restricted but risks remain.
    """
    # Prepare structured response dictionary
    response = {"stdout": "", "stderr": "", "exit_code": 1} # Default to error exit code

    trimmed_command = command.strip()
    print(f"DEBUG [Terminal Tool]: Received command: '{trimmed_command}'")
    if not trimmed_command:
        response["stderr"] = "Error: Empty command received."
        return json.dumps(response)

    # --- Command Parsing and Validation ---
    try:
        # Use shlex to handle arguments safely (deals with quotes etc.)
        args = shlex.split(trimmed_command)
        if not args: # Handle case where shlex returns empty list (e.g., input was just spaces/quotes)
             response["stderr"] = "Error: Command resulted in empty argument list after parsing."
             return json.dumps(response)
        executable = args[0]
        print(f"DEBUG [Terminal Tool]: Parsed args: {args}")
    except ValueError as e:
         print(f"Terminal Tool Error: Parsing failed for '{trimmed_command}'. Error: {e}")
         response["stderr"] = f"Error: Command parsing failed (check quotes/syntax). Details: {e}"
         return json.dumps(response)

    is_safe_to_execute = False
    execution_args = args # Default to using the parsed args list

    # 1. Check allowed basic commands
    if executable in ALLOWED_COMMANDS:
        is_safe_to_execute = True
        print(f"DEBUG [Terminal Tool]: Allowing basic command: '{executable}'")

    # 2. Check allowed python script execution
    elif executable == "python" and len(args) > 1:
        script_path_arg = args[1]
        if _is_script_path_safe(script_path_arg):
            is_safe_to_execute = True
            # IMPORTANT: Use the *original* args list from shlex for subprocess
            # This ensures arguments with spaces passed to the script are handled correctly
            print(f"DEBUG [Terminal Tool]: Allowing safe python script: '{script_path_arg}' with args: {args[2:]}")
        else:
            # Path is not safe or script doesn't exist
            response["stderr"] = (f"Error: Execution denied. Script path '{script_path_arg}' is not in allowed directories "
                                  f"{[str(d.relative_to(PROJECT_ROOT) if d.is_relative_to(PROJECT_ROOT) else d) for d in RESOLVED_ALLOWED_SCRIPT_DIRS]} "
                                  f"or does not exist as a file.")
            print(f"Terminal Tool Error: Unsafe/missing script path '{script_path_arg}'.")
            return json.dumps(response)
    # --- End Command Validation ---

    if not is_safe_to_execute:
        allowed_executables_str = ", ".join(ALLOWED_COMMANDS) + ", python (safe scripts only)"
        response["stderr"] = f"Error: Execution denied. Command starting with '{executable}' is not explicitly allowed. Allowed are: {allowed_executables_str}."
        print(f"Terminal Tool Error: Command blocked: '{executable}'")
        return json.dumps(response)

    # --- Execute the Allowed Command ---
    try:
        print(f"DEBUG [Terminal Tool]: Executing: {execution_args}")
        # Execute using subprocess.run with shell=False (using the args list)
        result = subprocess.run(
            execution_args,
            capture_output=True,
            text=True, # Decode stdout/stderr as text
            timeout=COMMAND_TIMEOUT,
            check=False, # Don't raise exception on non-zero exit code
            cwd=PROJECT_ROOT # Standardize execution directory to project root
        )

        # Store results
        response["stdout"] = result.stdout.strip()
        response["stderr"] = result.stderr.strip()
        response["exit_code"] = result.returncode

        print(f"DEBUG [Terminal Tool]: Command finished. Exit Code: {result.returncode}")
        # Log snippets of output
        if response["stdout"]: print(f"DEBUG [Terminal]: STDOUT (first 500 chars):\n{response['stdout'][:500]}...")
        if response["stderr"]: print(f"DEBUG [Terminal]: STDERR (first 500 chars):\n{response['stderr'][:500]}...")

        # --- Truncate long outputs before returning ---
        if len(response["stdout"]) > MAX_OUTPUT_LENGTH:
            print(f"DEBUG [Terminal]: Truncating stdout (was {len(response['stdout'])} chars).")
            response["stdout"] = response["stdout"][:MAX_OUTPUT_LENGTH] + "\n...(stdout truncated)"
        if len(response["stderr"]) > MAX_OUTPUT_LENGTH:
            print(f"DEBUG [Terminal]: Truncating stderr (was {len(response['stderr'])} chars).")
            response["stderr"] = response["stderr"][:MAX_OUTPUT_LENGTH] + "\n...(stderr truncated)"

    except FileNotFoundError:
         # This means the executable itself (e.g., 'python', 'ls', 'grep') wasn't found
         error_msg = f"Error: Command executable '{executable}' not found. Is it installed and in the system PATH?"
         print(f"Terminal Tool Error: {error_msg}")
         response["stderr"] = error_msg
         response["exit_code"] = 127 # Standard exit code for command not found
    except subprocess.TimeoutExpired:
        error_msg = f"Error: Command '{trimmed_command}' timed out after {COMMAND_TIMEOUT} seconds."
        print(f"Terminal Tool Error: Timeout expired.")
        response["stderr"] = error_msg
        response["exit_code"] = -9 # Or other indicator for timeout
    except Exception as e:
        error_msg = f"Error executing command '{trimmed_command}'. Details: {type(e).__name__} - {str(e)}"
        print(f"Terminal Tool Error: Unexpected execution failure: {e}")
        traceback.print_exc()
        response["stderr"] = error_msg
        response["exit_code"] = 1 # General error exit code

    # Return the structured JSON response
    try:
        json_output = json.dumps(response, indent=2)
        return json_output
    except Exception as json_e:
         print(f"Terminal Tool Error: Failed to serialize result to JSON: {json_e}")
         # Fallback: return a simple error string if JSON fails
         return f'{{"stdout": "", "stderr": "Error: Failed to format tool output as JSON.", "exit_code": 1}}'


# --- LangChain Tool Definition ---
terminal_tool_enhanced = Tool(
    name="Run Terminal Command or Safe Script",
    func=run_terminal_command_enhanced,
    description=(
        "Executes allowed shell commands or designated Python scripts for tasks like listing files (ls), checking paths (pwd), simple text processing (cat, head, tail, grep, wc), getting date, or running specific data processing scripts. "
        f"Allowed basic commands: {ALLOWED_COMMANDS}. "
        f"To run a Python script located in allowed project directories ({[str(d.relative_to(PROJECT_ROOT) if d.is_relative_to(PROJECT_ROOT) else d) for d in RESOLVED_ALLOWED_SCRIPT_DIRS]}): use 'python relative/path/script.py [arg1 ...]'. "
        "Example: 'python scripts/process_data.py outputs/input.csv outputs/result.txt'. "
        "Use quotes for arguments with spaces: `python scripts/proc.py \"an argument with spaces\"`. "
        "The script path must be relative to the project root. NO absolute paths or '..'. "
        f"Any other commands (like 'rm', 'mv', 'mkdir', 'sudo', 'pip', network commands) or scripts outside allowed areas ARE BLOCKED. "
        "Returns a JSON string containing 'stdout', 'stderr', and 'exit_code'. Check 'exit_code' (0 usually means success) and 'stderr' for errors."
    ),
    return_direct=False # Agent needs to interpret the JSON output
)

# Example Self-Test (optional)
if __name__ == '__main__':
    print("\n--- Terminal Tool Self-Test ---")
    # Test safe command
    print("\nTesting 'ls -l outputs':")
    print(run_terminal_command_enhanced("ls -l outputs"))
    # Test safe script (assuming scripts/process_data.py and outputs/test.csv exist)
    print("\nTesting 'python scripts/process_data.py outputs/test.csv':")
    # Create dummy file/dir if needed for test
    Path("./scripts").mkdir(exist_ok=True)
    Path("./scripts/process_data.py").touch() # Needs actual script content
    Path("./outputs/test.csv").write_text("Header1,Header2\n1,2\n3,4")
    print(run_terminal_command_enhanced("python scripts/process_data.py outputs/test.csv"))
    # Test unsafe command
    print("\nTesting 'rm outputs/test.csv':")
    print(run_terminal_command_enhanced("rm outputs/test.csv"))
    # Test unsafe script path
    print("\nTesting 'python /etc/passwd':")
    print(run_terminal_command_enhanced("python /etc/passwd"))
    # Test non-existent command
    print("\nTesting 'nonexistentcommand':")
    print(run_terminal_command_enhanced("nonexistentcommand"))
    print("--- End Test ---")