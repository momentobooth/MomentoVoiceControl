from llm.lmstudio_interface import LMStudioLLM
from llm.prompts import SYSTEM_PROMPTS


class LMStudioSingleTurn(LMStudioLLM):
    def __init__(self, model_name: str = "qwen3.5-2b", system_prompt: str = "single_turn") -> None:
        super().__init__(model_name, use_analysis=False, max_tool_calls=1)
        self.system_prompt_name = system_prompt
        self.system_prompt = SYSTEM_PROMPTS[self.system_prompt_name]

