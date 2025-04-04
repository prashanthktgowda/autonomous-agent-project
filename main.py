# main.py (Revised Full Script with Enhanced Logging)

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.exceptions import OutputParserException
import traceback
import sys # For exiting on import error
from tools.delete_file_tool import perform_delete

# --- Define Output Directory ---
# Needs to be consistent with tools
try:
    OUTPUT_DIR = Path("outputs").resolve()
    print(f"DEBUG: Output directory set to: {OUTPUT_DIR}")
except Exception as e:
    print(f"CRITICAL ERROR setting OUTPUT_DIR: {e}")
    sys.exit(1)
# --- ---

# --- Load Environment Variables ---
print("DEBUG: Loading environment variables from .env file...")
dotenv_loaded = load_dotenv()
if not dotenv_loaded:
    print("DEBUG: .env file not found or failed to load.")
else:
    print("DEBUG: .env file loaded successfully.")
# --- ---

# --- Import Agent Logic AFTER loading .env ---
print("DEBUG: Attempting to import agent modules...")
try:
    from agent.planner import initialize_agent
    # --- Import the actual delete function (NOT the agent tool) ---
    from tools.delete_file_tool import perform_delete
    print("DEBUG: Agent modules imported successfully.")
except ImportError as e:
    print(f"\n--- Error Importing Modules ---")
    print(f"ERROR: {e}")
    print("Please ensure 'agent/planner.py' and 'tools/delete_file_tool.py' exist and that all dependencies from requirements.txt are installed in your virtual environment.")
    traceback.print_exc() # Print detailed traceback for import errors
    sys.exit(1) # Exit if essential modules can't be loaded
except Exception as e:
    print(f"\n--- Unexpected Error During Import ---")
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
# --- ---

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous AI Agent (Command Line Interface)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "instruction",
        type=str,
        help="Natural language instruction for the agent"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging from the agent's execution steps"
    )
    args = parser.parse_args()

    print(f"\n--- Instruction Received ---\n'{args.instruction}'\n")
    print(f"DEBUG: Verbose mode requested: {args.verbose}")

    # Ensure output directory exists
    print(f"DEBUG: Checking/creating output directory: {OUTPUT_DIR}")
    if not OUTPUT_DIR.exists():
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            print(f"DEBUG: Created output directory: {OUTPUT_DIR}")
        except OSError as e:
            print(f"ERROR: Could not create output directory {OUTPUT_DIR}: {e}")
            # Depending on the task, you might want to exit here
            # sys.exit(1)

    agent_executor = None # Initialize agent_executor to None
    try:
        print("\n--- Initializing Agent ---")
        # Initialize the LangChain agent executor
        # Pass verbose flag from CLI args to the initializer
        agent_executor = initialize_agent(verbose=args.verbose)
        if agent_executor:
             print("--- Agent Initialized Successfully ---")
        else:
             print("ERROR: Agent initialization returned None!")
             sys.exit(1) # Exit if initialization failed critically

        print("\n--- Starting Agent Execution... ---")
        # Run the agent with the user's instruction
        result = agent_executor.invoke({"input": args.instruction})
        print("--- Agent Execution Attempt Finished ---") # Mark when invoke returns

        if not result:
             print("ERROR: Agent invocation returned None or empty result.")
             # Decide how to proceed, maybe exit or just report
        else:
             print(f"DEBUG: Raw agent result type: {type(result)}")
             print(f"DEBUG: Raw agent result content: {result}")

             # Get the raw output from the agent - handle if result is not a dict
             raw_agent_output = ""
             if isinstance(result, dict):
                  raw_agent_output = result.get('output', '*Agent finished, but no specific "output" key found in result.*')
             elif isinstance(result, str): # Some agents might return a string directly
                  raw_agent_output = result
             else:
                  raw_agent_output = f"*Agent finished, unexpected result type: {type(result)}*"

             print(f"DEBUG: Extracted raw agent output: '{raw_agent_output}'")

             # --- Check for Delete Confirmation Request ---
             delete_prefix = "CONFIRM_DELETE|"
             print(f"DEBUG: Checking if output starts with '{delete_prefix}'")
             if raw_agent_output.startswith(delete_prefix):
                  print("DEBUG: Detected delete confirmation request.")
                  try:
                      relative_path_to_delete = raw_agent_output.split('|', 1)[1]
                      if not relative_path_to_delete:
                           raise ValueError("Extracted relative path is empty.")

                      # Construct full path carefully
                      full_path_to_delete = (OUTPUT_DIR / relative_path_to_delete).resolve()
                      print(f"DEBUG: Resolved full path for deletion: {full_path_to_delete}")

                      # Crucial final safety check: ensure it's still within OUTPUT_DIR after resolving
                      if not full_path_to_delete.is_relative_to(OUTPUT_DIR):
                           print(f"\n--- SECURITY ERROR ---")
                           print(f"ERROR: Agent requested deletion of path outside designated output directory!")
                           print(f"   Requested relative path: {relative_path_to_delete}")
                           print(f"   Resolved absolute path: {full_path_to_delete}")
                           print(f"   Allowed directory: {OUTPUT_DIR}")
                           print("--- Deletion Denied ---")

                      else:
                           # Path is safe, proceed with confirmation
                           print(f"\n!! AGENT REQUESTS DELETE CONFIRMATION !!")
                           print(f"   File: {relative_path_to_delete} (in '{OUTPUT_DIR.name}')")
                           print(f"   Full path: {full_path_to_delete}")

                           # Prompt user for confirmation via command line
                           user_confirmation = input("   Are you sure you want to delete this file? (yes/no): ").strip().lower()

                           if user_confirmation in ['yes', 'y']:
                               print(f"--- User confirmed deletion. Attempting to delete... ---")
                               # Call the *actual* delete function
                               success, message = perform_delete(str(full_path_to_delete))
                               if success:
                                   print(f"   SUCCESS: {message}")
                               else:
                                   print(f"   ERROR: {message}")
                           else:
                               print("--- Deletion cancelled by user. ---")

                  except IndexError:
                       print("\n--- Error Processing Agent Output ---")
                       print("Agent requested deletion but the output format was incorrect (missing '|' or path?).")
                       print(f"Raw Output: {raw_agent_output}")
                  except ValueError as ve:
                       print("\n--- Error Processing Agent Output ---")
                       print(f"Agent requested deletion but the path seems invalid: {ve}")
                       print(f"Raw Output: {raw_agent_output}")
                  except Exception as e:
                       print("\n--- Error During Confirmation/Deletion ---")
                       print(f"An unexpected error occurred: {e}")
                       traceback.print_exc()

             else:
                  # If not a delete confirmation, print the agent's final answer normally
                  print(f"\n--- Final Answer ---")
                  print(raw_agent_output)


    # --- Catch Specific Exceptions First ---
    except OutputParserException as e:
        print("\n--- Agent Execution Error ---")
        print(f"ERROR: The LLM failed to format its response correctly for the agent.")
        print(f"This often means it didn't follow the expected 'Action:', 'Action Input:' format.")
        print(f"Details: {e}")
    except ValueError as e:
         # Can be raised by API key checks, path issues etc.
         print("\n--- Configuration or Value Error ---")
         print(f"ERROR: {e}")
         print("Check API keys in .env, file paths, or input values.")
         traceback.print_exc() # Show where the ValueError originated
    except ImportError as e:
         # Should be caught earlier, but added as a safeguard
         print("\n--- Dependency Error ---")
         print(f"ERROR: Missing required library: {e}")
         print("Ensure all packages in requirements.txt are installed.")
         traceback.print_exc()
    except Exception as e:
        # Catch-all for any other unexpected errors during initialization or execution
        print("\n--- Unexpected Agent Execution Error ---")
        print(f"An unexpected error occurred: {type(e).__name__} - {e}")
        traceback.print_exc()

    finally:
        # This block always executes
        print("\n--- Task Execution Attempt Complete ---")
        print(f"Check the '{OUTPUT_DIR.name}' directory ({OUTPUT_DIR}) for any generated/modified files.")

if __name__ == "__main__":
    # Ensure the script entry point is clear
    print("DEBUG: Starting main execution block...")
    main()
    print("DEBUG: Finished main execution block.")