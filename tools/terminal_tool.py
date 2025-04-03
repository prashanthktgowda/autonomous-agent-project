import subprocess
import sys
import shlex # Use shlex for safer command splitting if needed
from langchain.tools import Tool

# --- Core Terminal Function ---

def run_terminal_command(command: str) -> str:
    """
    Executes a shell command in a subprocess and returns its stdout and stderr.

    !! EXTREME SECURITY WARNING !!
    Executing arbitrary commands received from an LLM is **HIGHLY DANGEROUS** and
    can compromise your system, delete files, or expose data.
    The safety checks below are **MINIMAL** and **NOT SUFFICIENT** for production use.
    For this educational project, ONLY run commands you understand and trust.
    Consider running this agent in a containerized or sandboxed environment.
    NEVER run this agent with elevated (root/admin) privileges.

    Current basic filter allows only specific commands. Avoid commands that modify files
    system-wide (rm, mv outside 'outputs'), download/execute remote scripts, or manage users/permissions.
    """
    trimmed_command = command.strip()
    print(f"Terminal Tool: Received command: '{trimmed_command}'")

    # --- !! VERY Basic Safety Filter (Improve or use Sandboxing) !! ---
    # Whitelist approach: only allow specific commands/patterns.
    # This is NOT foolproof against complex shell injection if shell=True is used.
    allowed_prefixes = ["ls", "pwd", "echo", "cat", "head", "tail", "grep", "python", "node"]
    # Example: Allow python scripts only within the project dir or outputs
    # Example: Disallow directory traversal '..' in paths

    # Split command safely if possible (less useful if shell=True is needed for pipes)
    try:
         # Use shlex if you plan to use shell=False later
         # args = shlex.split(trimmed_command)
         # command_executable = args[0]
         command_executable = trimmed_command.split()[0] # Basic split for prefix check
    except Exception:
         command_executable = "" # Handle empty or malformed commands

    if not any(trimmed_command.startswith(prefix) for prefix in allowed_prefixes):
         print(f"Terminal Tool Error: Command '{trimmed_command}' is not in the allowed list ({allowed_prefixes}).")
         return f"Error: Execution of command starting with '{command_executable}' is denied for security reasons. Allowed prefixes: {allowed_prefixes}"

    # Add more checks: block 'sudo', 'rm -rf /', 'mkfs', 'useradd', ';', '&&', '||', '`', '$(' etc.
    # This requires more sophisticated parsing or using shell=False whenever possible.
    if ";" in trimmed_command or "&&" in trimmed_command or "||" in trimmed_command or "`" in trimmed_command or "$(" in trimmed_command:
         print(f"Terminal Tool Error: Command '{trimmed_command}' contains potentially dangerous shell operators.")
         return f"Error: Execution of command denied due to potentially dangerous operators."
    if "sudo" in trimmed_command.split():
         print(f"Terminal Tool Error: Command '{trimmed_command}' contains 'sudo'.")
         return f"Error: Execution of 'sudo' commands is strictly prohibited."

    # --- End Safety Filter ---

    try:
        # Using shell=True is convenient for pipes/redirects but riskier.
        # If shell=False, command must be a list (e.g., shlex.split(command)) and shell features won't work directly.
        # Timeout is crucial.
        print(f"Terminal Tool: Executing filtered command: '{trimmed_command}'")
        result = subprocess.run(
            trimmed_command,
            shell=True, # VERY DANGEROUS - PROCEED WITH EXTREME CAUTION
            capture_output=True,
            text=True,
            timeout=45, # Increased timeout slightly
            check=False, # Handle non-zero exit codes manually
            cwd="." # Run in the project's root directory
        )

        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout.strip()}\n"
        if result.stderr:
            # Often, programs write informational messages to stderr, treat it carefully
            output += f"STDERR:\n{result.stderr.strip()}\n"

        output += f"Exit Code: {result.returncode}"

        if result.returncode != 0:
            print(f"Terminal Tool: Command failed. Exit code: {result.returncode}\nStderr: {result.stderr.strip()}")
            # Output already contains stdout/stderr/exit code
        else:
            print(f"Terminal Tool: Command executed successfully.")
            if not result.stdout.strip() and not result.stderr.strip():
                 output += "\n(No output produced on stdout/stderr)"


        # Limit output size
        max_len = 3000
        if len(output) > max_len:
            print(f"Terminal Tool: Truncating output from {len(output)} to {max_len} chars.")
            output = output[:max_len] + f"\n... (truncated)\nExit Code: {result.returncode}"

        return output

    except subprocess.TimeoutExpired:
        print(f"Terminal Tool Error: Command '{trimmed_command}' timed out.")
        return f"Error: Command '{trimmed_command}' timed out after 45 seconds."
    except FileNotFoundError:
         print(f"Terminal Tool Error: Command not found (executable missing?): '{command_executable}'")
         return f"Error: Command not found. Make sure '{command_executable}' is installed and in the PATH."
    except Exception as e:
        print(f"Terminal Tool Error: Failed to execute command '{trimmed_command}'. Error: {e}")
        return f"Error executing command '{trimmed_command}'. Details: {str(e)}"

# --- LangChain Tool Definition ---

terminal_tool = Tool(
    name="Terminal Executor",
    func=run_terminal_command,
    description="""
    Use this tool to execute shell commands in a terminal.
    Input should be a single, valid shell command string.
    Output contains the STDOUT, STDERR, and Exit Code from the command.
    **SECURITY WARNING**: Only execute commands from the allowed list (currently starts with: """ + ", ".join(["ls", "pwd", "echo", "cat", "head", "tail", "grep", "python", "node"]) + """).
    Avoid commands that modify the file system outside the './outputs' directory, download content, or manage system settings.
    Use 'ls ./outputs' to list files in the output directory.
    Use 'python your_script.py' to run python scripts (ensure scripts are safe).
    Use 'cat ./outputs/file.txt' to view file content.
    Do NOT use 'sudo', ';', '&&', '||', '`', '$()'.
    """,
)