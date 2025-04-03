import os
import argparse
from dotenv import load_dotenv
from langchain_core.exceptions import OutputParserException

# Ensure agent is imported after dotenv load if planner loads env vars too
# from agent.planner import initialize_agent # Moved after load_dotenv

# Load environment variables (API Keys like HUGGINGFACEHUB_API_TOKEN)
# Load early so planner.py can access them during import/initialization if needed
load_dotenv()

# Now import the agent initializer which might depend on loaded env vars
from agent.planner import initialize_agent

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous AI Agent using Hugging Face Models",
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
        help="Enable verbose logging to see agent's thought process"
        )
    args = parser.parse_args()

    print(f"\n--- Instruction Received ---\n{args.instruction}\n")
    print("--- Initializing Agent (using Hugging Face Hub LLM) ---")

    # Ensure output directory exists (belt and suspenders)
    output_dir = "outputs"
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        except OSError as e:
            print(f"Error creating output directory {output_dir}: {e}")
            # Decide if you want to exit or continue
            # return

    try:
        # Initialize the LangChain agent executor
        agent_executor = initialize_agent(verbose=args.verbose)

        print("\n--- Agent Initialized. Starting Execution... ---\n")

        # Run the agent with the user's instruction
        # The agent_executor handles the loop: Thought -> Action -> Observation -> Thought...
        result = agent_executor.invoke({"input": args.instruction})

        print("\n--- Agent Execution Finished ---")
        # The final result structure depends on the agent type (ReAct usually has 'output')
        final_output = result.get('output', 'No "output" key found in result.')
        print(f"Final Answer:\n{final_output}")

    except OutputParserException as e:
        print("\n--- Agent Execution Error ---")
        print(f"ERROR: The LLM failed to format its response correctly for the agent.")
        print(f"Details: {e}")
        print("This often happens if the LLM doesn't follow the required Action/Action Input format.")
        print("Try rephrasing the instruction, using a different model, or checking tool descriptions.")
    except ValueError as e:
         print("\n--- Configuration Error ---")
         print(f"ERROR: {e}")
         print("Please check your .env file and API keys.")
    except ImportError as e:
         print("\n--- Dependency Error ---")
         print(f"ERROR: Missing required library: {e}")
         print("Please ensure all packages in requirements.txt are installed (`pip install -r requirements.txt`).")
    except Exception as e:
        print("\n--- Unexpected Agent Execution Error ---")
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc() # Print detailed traceback for debugging

    print("\n--- Task Execution Attempt Complete ---")
    print(f"Please check the '{output_dir}' directory for any generated files.")

if __name__ == "__main__":
    main()