"""
services/llm_client.py
======================
Centralized wrapper for Ollama models via the OpenAI SDK.
Handles client initialization and forced JSON output.
"""

import logging
import os

from openai import OpenAI
from pydantic import BaseModel

import os
import logging
import json
from openai import OpenAI

# We still need to import this just for typing hints in the method signature
from google.genai import types

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, model: str | None = None, max_tokens: int = 1000):
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3-coder-next:cloud")
        self.max_tokens = max_tokens
        
        try:
            self.client = OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama" # required but ignored by Ollama
            )
        except Exception as exc:
            logger.warning("Failed to initialize OpenAI client for Ollama: %s", exc)
            self.client = None

    def extract_structured_data(
        self,
        system_instruction: str,
        user_prompt: str,
        tool: types.Tool,
        tool_name: str,
        temperature: float = 0.0,
    ) -> dict | None:
        """
        Force the LLM to output structured JSON matching the provided tool definition.
        """
        if not self.client:
            logger.error("LLMClient is not initialized. Cannot perform extraction.")
            return None
            
        try:
            # Convert GenAI Tool to OpenAI Tool Format
            fd = tool.function_declarations[0]
            openai_tool = {
                "type": "function",
                "function": {
                    "name": fd.name,
                    "description": fd.description,
                    "parameters": fd.parameters
                }
            }

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=self.max_tokens,
                tools=[openai_tool],
                tool_choice={"type": "function", "function": {"name": fd.name}}
            )
            
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                # Return the parsed JSON args of the forced function call
                return json.loads(tool_calls[0].function.arguments)
            
            logger.warning("LLM returned no function calls.")
            return None
                
        except Exception as e:
            logger.error("LLM call failed in extract_structured_data: %s", e)
            return None

default_llm_client = LLMClient()
