#!/usr/bin/env python3
"""
Integration test script for LM Studio interface with command examples.
Tests all command examples against the tool list and logs execution time and precision.
"""

import time
from typing import List, Dict, Any

from core.registry import ResolvedCommand
# Import required modules from context files
from state_machine import StateMachine
from command_examples import COMMAND_EXAMPLES, CommandExample, ToolInvocation
from llm.lmstudio_interface import LMStudioLLM


def calculate_precision(expected_tools: List[ToolInvocation], actual_tools: List[ToolInvocation]) -> float:
    """
    Calculates precision where order matters.
    A tool is 'correct' if the name matches and its parameters are a superset of the expected parameters.
    """
    if not actual_tools:
        # If we expected tools but got none, precision is 0.
        # If we expected none and got none, precision is 1.0.
        return 1.0 if not expected_tools else 0.0

    true_positives = 0

    # We iterate through the actual predictions to see how many are "correct"
    # relative to the expected sequence.
    for i, actual in enumerate(actual_tools):
        # If the actual list is longer than the expected list,
        # any extra tools are automatically 'False Positives'.
        if i >= len(expected_tools):
            break

        expected = expected_tools[i]

        # 1. Check if the tool name matches
        if actual.name != expected.name:
            continue

        # 2. Check if parameters are a superset (contains all expected keys/values)
        # All key-value pairs in 'expected' must exist in 'actual'
        match_params = all(
            key in actual.parameters and actual.parameters[key] == value
            for key, value in expected.parameters.items()
        )

        if match_params:
            true_positives += 1

    return true_positives / len(actual_tools)


def run_command_example_test(
        command_example: CommandExample,
        state_machine: StateMachine,
        llm_interface: LMStudioLLM
) -> Dict[str, Any]:
    """Test a single command example against the LM Studio interface."""

    # Create generator for available tools that updates as commands are executed
    def scope_info_generator():
        while True:
            next_state_tools = state_machine.get_scope_info()
            yield next_state_tools

    # Start timing
    start_time = time.time()
    resolved_commands: List[ResolvedCommand] = []

    try:
        # Process all tool invocations through LLM interface
        executed_tools = []

        # Use LM Studio interface to parse command
        try:
            response_generator = llm_interface.extract_intent(
                command_example.transcript,
                scope_info_generator()
            )

            # Process each resolved command in order
            for resolved_cmd in response_generator:
                resolved_commands.append(resolved_cmd)

                if resolved_cmd.intent != "do_nothing_and_finish":
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

    resolved_commands_as_invocations = [ToolInvocation(cmd.intent, cmd.parameters) for cmd in resolved_commands if cmd.intent != "do_nothing_and_finish"]

    precision = calculate_precision(command_example.tool_invocations, resolved_commands_as_invocations)

    return {
        'command': command_example.transcript,
        'expected_tools': [t.name for t in command_example.tool_invocations],
        'actual_tools':  resolved_commands,
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
            print(f"  Actual tools found: {[t.intent for t in result['actual_tools']]}")
            print(f"  Execution time: {result['execution_time']:.4f} seconds")
            print(f"  Precision: {result['precision']:.2%}")

            total_precision += result['precision']

        except Exception as e:
            print(f"Error in test case {i+1}: {e}")
            results.append({
                'command': example.transcript,
                'expected_tools': [t.name for t in example.tool_invocations],
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
        if result['precision'] < 1.0:
            print(f"\tExpected tools: {result['expected_tools']}")
            print(f"\tActual tools found:")
            actual_tools_list: List[ResolvedCommand] = result['actual_tools']
            for tool in actual_tools_list:
                print(f"\t\t{tool.intent}({tool.parameters}): {tool.reasoning} – {tool.confidence:.2%}")

if __name__ == "__main__":
    main()
