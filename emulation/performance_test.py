#!/usr/bin/env python3
"""
Integration test script for LM Studio interface with command examples.
Tests all command examples against the tool list and logs execution time and precision.
"""

import time
from typing import List, Dict, Any

# Import required modules from context files
from state_machine import StateMachine
from scope_states import ScopeNames
from command_examples import COMMAND_EXAMPLES, CommandExample, ToolInvocation
from llm.lmstudio_interface import LMStudioLLM

def calculate_precision(expected_tools: List[str], actual_tools: List[str]) -> float:
    """Calculate precision as the ratio of correctly predicted tools to total predictions."""
    if not expected_tools and not actual_tools:
        return 1.0
    if not expected_tools or not actual_tools:
        return 0.0

    # Calculate intersection of tools
    expected_set = set(expected_tools)
    actual_set = set(actual_tools)

    # Precision is number of correctly predicted tools divided by total predictions
    if len(actual_set) == 0:
        return 0.0

    correct_predictions = len(expected_set.intersection(actual_set))
    return correct_predictions / len(actual_set)


def run_command_example_test(
        command_example: CommandExample,
        state_machine: StateMachine,
        llm_interface: LMStudioLLM
) -> Dict[str, Any]:
    """Test a single command example against the LM Studio interface."""

    # Get initial available tools from current state
    initial_scope_info = state_machine.get_scope_info()

    # Create generator for available tools that updates as commands are executed
    def scope_info_generator():
        yield initial_scope_info
        while True:
            next_state_tools = state_machine.get_scope_info()
            yield next_state_tools

    # Start timing
    start_time = time.time()
    resolved_commands = []

    try:
        # Process all tool invocations through LLM interface
        executed_tools = []
        actual_tools_found = []

        # for i, tool_invocation in enumerate(command_example.tool_invocations):

            # # Get available tools for this step
            # current_tools = next(tools_gen)
            # tool_names = [t['name'] for t in current_tools]
            #
            # # Actually use the LLM interface to extract intent
            # print(f"  Available tools: {tool_names}")

        # Use LM Studio interface to parse command
        try:
            response_generator = llm_interface.extract_intent(
                command_example.transcript,
                scope_info_generator()
            )

            # Process each resolved command in order
            for resolved_cmd in response_generator:
                if resolved_cmd.intent != "do_nothing_and_finish":
                    resolved_commands.append(resolved_cmd)
                    actual_tools_found.append(resolved_cmd.intent)

                    print(f"  LLM detected: {resolved_cmd.intent}")

                    # Execute the tool through state machine to update available tools
                    try:
                        state_machine.execute(resolved_cmd.intent, resolved_cmd.parameters)
                        executed_tools.append(resolved_cmd.intent)
                        print(f"  Executed tool: {resolved_cmd.intent}")
                    except Exception as e:
                        print(f"  Failed to execute tool {resolved_cmd.intent}: {e}")

        except Exception as e:
            print(f"  Error in LLM processing: {e}")

        end_time = time.time()
        execution_time = end_time - start_time

    except Exception as e:
        print(f"Error processing command example: {e}")
        execution_time = 0.0
        executed_tools = []
        actual_tools_found = []

    # Calculate precision (we'll use the expected tools from the command example)
    expected_tool_names = [tool.name for tool in command_example.tool_invocations if
                           tool.name != "do_nothing_and_finish"]

    precision = calculate_precision(expected_tool_names, actual_tools_found)

    return {
        'command': command_example.transcript,
        'expected_tools': expected_tool_names,
        'actual_tools': actual_tools_found,
        'executed_tools': executed_tools,
        'execution_time': execution_time,
        'precision': precision
    }

def main():
    """Main function to run all command example tests."""

    # Initialize state machine and LLM interface
    print("Initializing components...")
    state_machine = StateMachine()
    llm_interface = LMStudioLLM(model_name="qwen3.5-2b")

    results = []
    total_precision = 0.0

    print(f"Testing {len(COMMAND_EXAMPLES)} command examples...\n")

    for i, example in enumerate(COMMAND_EXAMPLES):
        print(f"\n--- Test Case {i+1} ---")
        print(f"Scope: {example.scope.value}")
        print(f"Transcript: {example.transcript}")

        # Reset state machine to starting state
        state_machine = StateMachine(example.scope)

        try:
            result = run_command_example_test(example, state_machine, llm_interface)
            results.append(result)

            print(f"\nResults:")
            print(f"  Expected tools: {result['expected_tools']}")
            print(f"  Actual tools found: {result['actual_tools']}")
            print(f"  Execution time: {result['execution_time']:.4f} seconds")
            print(f"  Precision: {result['precision']:.2%}")

            total_precision += result['precision']

        except Exception as e:
            print(f"Error in test case {i+1}: {e}")
            results.append({
                'command': example.transcript,
                'expected_tools': [tool.name for tool in example.tool_invocations if tool.name != "do_nothing_and_finish"],
                'actual_tools': [],
                'executed_tools': [],
                'execution_time': 0.0,
                'precision': 0.0
            })

    # Summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)

    total_tests = len(results)
    avg_precision = total_precision / total_tests if total_tests > 0 else 0.0

    total_time = sum(r['execution_time'] for r in results)
    avg_time = total_time / total_tests if total_tests > 0 else 0.0

    print(f"Total tests: {total_tests}")
    print(f"Average execution time: {avg_time:.4f} seconds")
    print(f"Average precision: {avg_precision:.2%}")

    # Show individual results for debugging
    print("\nDetailed Results:")
    for i, result in enumerate(results):
        print(f"Test {i+1}: '{result['command']}' -> Precision: {result['precision']:.2%}, Time: {result['execution_time']:.4f}s")
        print(f"\tExpected tools: {result['expected_tools']}, Actual tools found: {result['actual_tools']}")

if __name__ == "__main__":
    main()
