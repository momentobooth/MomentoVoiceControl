"""
core/executor.py — Command execution via MQTT.

Each resolved command is published to momentobooth/do_action as a
fire-and-forget invocation.  The bridge handles serialisation.
"""
from __future__ import annotations
import json

from core.registry import CommandResult
from mqtt_bridge.bridge import MQTTBridge


def execute(result: CommandResult, bridge: MQTTBridge) -> None:
    """
    Dispatch every command in the result through the MQTT bridge.

    Parameters
    ----------
    result : CommandResult
    bridge : MQTTBridge  (not type-hinted to avoid a circular import)
    """
    print("\n" + "─" * 60)
    print("🎙  COMMAND RECOGNISED")
    print(f"    transcript : {result.raw_transcript!r}")

    for cmd in result.commands:
        print(f"    intent     : {cmd.intent}")
        if cmd.parameters:
            print(f"    parameters : {json.dumps(cmd.parameters)}")
        print(f"    layer      : {cmd.layer}  confidence={cmd.confidence:.2f}")
        bridge.invoke_tool(cmd.intent, cmd.parameters)

    print("─" * 60 + "\n")
