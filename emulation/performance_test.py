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
from llm.lmstudio_single_turn import LMStudioSingleTurn


def calculate_metrics(expected_tools: List[ToolInvocation], actual_tools: List[ToolInvocation]):
    if not expected_tools and not actual_tools:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    if not actual_tools or not expected_tools:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    true_positives = 0
    # Compare up to the shortest list length to avoid IndexErrors
    for i in range(min(len(actual_tools), len(expected_tools))):
        act = actual_tools[i]
        exp = expected_tools[i]

        # Name match + Superset parameter match
        if act.name == exp.name:
            if all(k in act.parameters and act.parameters[k] == v
                   for k, v in exp.parameters.items()):
                true_positives += 1

    precision = true_positives / len(actual_tools)
    recall = true_positives / len(expected_tools)

    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }


def run_command_example_test(
        command_example: CommandExample,
        state_machine: StateMachine,
        llm_interface: LMStudioLLM,
        max_tool_calls: int
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

    metrics = calculate_metrics(command_example.tool_invocations[:max_tool_calls], resolved_commands_as_invocations)

    return {
        'command': command_example.transcript,
        'expected_tools': [t.name for t in command_example.tool_invocations],
        'actual_tools':  resolved_commands,
        'executed_tools': executed_tools,
        'execution_time': execution_time,
        'precision': metrics['f1']
    }


def benchmark_interface_multi_turn(llm_interface: LMStudioLLM, max_tool_calls=3):
    results = []
    total_precision = 0.0

    print(f"Testing {len(COMMAND_EXAMPLES)} command examples...\n")

    for i, example in enumerate(COMMAND_EXAMPLES):
        print(f"\n--- Test Case {i + 1} ---")
        print(f"Scope: {example.scope.value}")
        print(f"Transcript: {example.transcript}")

        # Reset state machine to starting state
        state_machine = StateMachine(example.scope)

        try:
            result = run_command_example_test(example, state_machine, llm_interface, max_tool_calls)
            results.append(result)

            print(f"\nResults:")
            print(f"  Expected tools: {result['expected_tools']}")
            print(f"  Actual tools found: {[t.intent for t in result['actual_tools']]}")
            print(f"  Execution time: {result['execution_time']:.4f} seconds")
            print(f"  Precision: {result['precision']:.2%}")

            total_precision += result['precision']

        except Exception as e:
            print(f"Error in test case {i + 1}: {e}")
            results.append({
                'command': example.transcript,
                'expected_tools': [t.name for t in example.tool_invocations],
                'actual_tools': [],
                'executed_tools': [],
                'execution_time': 0.0,
                'precision': 0.0
            })

    # Summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)

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
        print(
            f"Test {i + 1}: '{result['command']}' -> Precision: {result['precision']:.2%}, Time: {result['execution_time']:.4f}s")
        if result['precision'] < 1.0:
            print(f"\tExpected tools: {result['expected_tools']}")
            print(f"\tActual tools found:")
            actual_tools_list: List[ResolvedCommand] = result['actual_tools']
            for tool in actual_tools_list:
                print(f"\t\t{tool.intent}({tool.parameters}): {tool.reasoning} – {tool.confidence:.2%}")


def main():
    """Main function to run all command example tests."""

    # Initialize state machine and LLM interface
    print("Initializing components...")
    # llm_interface = LMStudioLLM(model_name="qwen3.5-2b")
    # llm_interface = LMStudioLLM(model_name="qwen3.5-2b-qwen3.6-plus-distilled")
    # llm_interface = LMStudioLLM(model_name="google/gemma-4-e4b")
    # llm_interface = LMStudioLLM(model_name="google/gemma-4-e2b", use_analysis=False)
    #
    # benchmark_interface_multi_turn(llm_interface)

    # llm_single_turn_interface = LMStudioSingleTurn(model_name="google/gemma-4-e2b")
    llm_single_turn_interface = LMStudioSingleTurn(model_name="qwen3.5-2b")
    # llm_single_turn_interface = LMStudioSingleTurn(model_name="lfm2.5-1.2b-instruct")
    benchmark_interface_multi_turn(llm_single_turn_interface, max_tool_calls=1)


if __name__ == "__main__":
    main()
