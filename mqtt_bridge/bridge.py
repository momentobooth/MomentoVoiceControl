"""
mqtt/bridge.py — MQTT integration for command sourcing and execution.

Subscribes to two topics:
  momentobooth/current_actions   → updates the CommandRegistry when the UI
                                   publishes a new tool list
  momentobooth/do_action/result  → prints tool results to the console

Publishes to:
  momentobooth/do_action         → fires a tool invocation (fire-and-forget)

Threading model
---------------
Paho runs its own network thread (loop_start).  Registry updates are
delivered to the main thread via CommandRegistry.update_commands(), which
is safe to call from any thread.  No asyncio involved.

Environment variables
---------------------
  MQTT_BROKER    default: localhost
  MQTT_PORT      default: 1883
  MQTT_USERNAME  optional
  MQTT_PASSWORD  optional
"""
from __future__ import annotations

import json
import logging
import os
import uuid

from paho.mqtt import client as mqtt

from core.registry import CommandRegistry

log = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

MQTT_TOPIC_ACTIONS = "momentobooth/current_actions"
MQTT_TOPIC_EXECUTE = "momentobooth/do_action"


def _translate_tools(raw_tools: list[dict]) -> dict:
    """
    Translate the MCP tool schema into the registry's update_commands payload.

    MCP shape (incoming):
        [
          {
            "name": "go_back",
            "examples": ["go back", "back"],
            "inputSchema": {"properties": {"count": {...}}, ...}
          },
          ...
        ]

    Registry shape (outgoing):
        {
          "screen": "",          # MQTT carries no screen name; left blank
          "commands": [
            {
              "name": "go_back",
              "examples": ["go back", "back"],
              "parameters": ["count"]
            },
            ...
          ]
        }
    """
    commands = []
    type_map = {"integer": "number", "number": "number", "string": "string"}

    def remove_characters(s: str) -> str:
        to_remove = [",", ".", ";"]
        for rm in to_remove:
            s = s.replace(rm, "")
        return s

    for tool in raw_tools:
        # Extract parameter names from the JSON Schema properties dict, if present.
        input_schema = json.loads(tool.get("inputSchema", "{}"))
        properties = input_schema.get("properties", {})
        parameters = {}
        for key, value in properties.items():
            value_type = value.get("type")
            if value_type == "array":
                sub_type = value.get("items", {}).get("type")
                parameters[key] = {"type": type_map.get(sub_type), "is_array": True}
            else:
                parameters[key] = {"type": type_map.get(value_type), "is_array": False}

        # Ensure that there is no punctuation in our examples
        examples = [remove_characters(e) for e in tool.get("examples", [])]
        commands.append({
            "name": tool["name"],
            "examples": examples,
            "parameters": parameters,
        })

    return {"screen": "", "commands": commands}


class MQTTBridge:
    """
    Manages the MQTT connection, registry updates, and tool invocations.

    Usage:
        bridge = MQTTBridge(registry)
        bridge.start()
        ...
        bridge.invoke_tool("go_back", {})
        ...
        bridge.stop()
    """

    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        if MQTT_USERNAME:
            self._client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    # ── MQTT callbacks (paho network thread) ──────────────────────────────────

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT connection failed: %s", reason_code)
            return
        log.info("MQTT connected to %s:%s", MQTT_BROKER, MQTT_PORT)
        client.subscribe(MQTT_TOPIC_ACTIONS, qos=1)
        client.subscribe(MQTT_TOPIC_EXECUTE + "/result", qos=1)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        log.warning("MQTT disconnected: %s", reason_code)

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="replace")

        if topic == MQTT_TOPIC_ACTIONS:
            self._handle_actions(payload)
        elif topic == MQTT_TOPIC_EXECUTE + "/result":
            self._handle_result(payload)

    def _handle_actions(self, payload: str) -> None:
        try:
            raw_tools = json.loads(payload)
            if not isinstance(raw_tools, list):
                log.warning("Expected JSON array on %s, got %s", MQTT_TOPIC_ACTIONS, type(raw_tools))
                return
        except json.JSONDecodeError as exc:
            log.error("Failed to parse tool definitions: %s", exc)
            return

        registry_payload = _translate_tools(raw_tools)
        self._registry.update_commands(registry_payload)

    def _handle_result(self, payload: str) -> None:
        """Log the result to the console — fire-and-forget, no callers waiting."""
        try:
            data = json.loads(payload)
            pretty = json.dumps(data, indent=2)
        except json.JSONDecodeError:
            pretty = payload
        log.info("Tool result received:\n%s", pretty)
        print(f"[MQTT] Tool result:\n{pretty}\n")

    # ── Public API (main / pipeline thread) ───────────────────────────────────

    def start(self) -> None:
        self._client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def invoke_tool(self, name: str, arguments: dict) -> None:
        """
        Publish a fire-and-forget tool invocation.

        Published shape:
            {
                "tool": "<name>",
                "arguments": { ... },
                "correlation_id": "<uuid>"
            }

        The correlation_id is included so the server can echo it back in the
        result message, which we then log in _handle_result.
        """
        payload = json.dumps({
            "tool": name,
            "arguments": arguments,
            "correlation_id": str(uuid.uuid4()),
        })
        self._client.publish(MQTT_TOPIC_EXECUTE, payload, qos=1)
        log.info("Published tool invocation: tool=%s", name)
