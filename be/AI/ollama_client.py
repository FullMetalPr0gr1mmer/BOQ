"""
Ollama client for LLM inference
"""
import json
import os
from typing import List, Dict, Any, Optional
import ollama
import logging

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Wrapper for Ollama API with environment-based model selection
    """

    @staticmethod
    def get_default_model() -> str:
        """
        Get the appropriate model based on environment

        Returns:
            Model name (gemma2:9b for production, llama3.2:1b for development)
        """
        environment = os.getenv("ENVIRONMENT", "development").lower()

        if environment == "production":
            model = os.getenv("OLLAMA_MODEL_PRODUCTION", "gemma2:9b")
            logger.info(f"Using PRODUCTION model: {model}")
        else:
            model = os.getenv("OLLAMA_MODEL_DEVELOPMENT", "llama3.2:1b")
            logger.info(f"Using DEVELOPMENT model: {model}")

        return model

    def __init__(self, host: str = None, model: str = None):
        """
        Initialize Ollama client

        Args:
            host: Ollama server URL (defaults to OLLAMA_HOST env var or localhost:11434)
            model: Model name to use (defaults to environment-based selection)
        """
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or self.get_default_model()
        self.client = ollama.Client(host=self.host)

        logger.info(f"Initialized OllamaClient with model: {self.model}, host: {self.host}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        json_mode: bool = False,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate completion for a prompt

        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature (0-1)
            json_mode: Force JSON output
            max_tokens: Max tokens to generate

        Returns:
            Generated text
        """
        options = {
            "temperature": temperature
        }

        if max_tokens:
            options["num_predict"] = max_tokens

        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options=options,
                format="json" if json_mode else None
            )

            return response['message']['content']

        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """
        Multi-turn chat conversation

        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            system_prompt: System instructions
            temperature: Sampling temperature
            stream: Enable streaming

        Returns:
            Assistant's response
        """
        # Prepend system message if provided
        chat_messages = []

        if system_prompt:
            chat_messages.append({
                "role": "system",
                "content": system_prompt
            })

        chat_messages.extend(messages)

        try:
            if stream:
                # TODO: Implement streaming
                pass
            else:
                response = self.client.chat(
                    model=self.model,
                    messages=chat_messages,
                    options={"temperature": temperature}
                )
                return response['message']['content']

        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    def function_call(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Function calling (tool use) with Ollama

        Args:
            prompt: User request
            functions: Available functions with schemas
            system_prompt: System instructions

        Returns:
            Function call or text response
        """
        # Build function calling prompt
        functions_desc = json.dumps(functions, indent=2)

        full_system_prompt = f"""{system_prompt or 'You are a helpful assistant.'}

IMPORTANT: You have access to these functions to query data and perform actions:
{functions_desc}

CRITICAL INSTRUCTIONS:
- When the user asks a question that requires data from the database, YOU MUST call the appropriate function
- Respond with ONLY valid JSON in this exact format (no markdown, no explanation):
{{
    "function": "function_name",
    "arguments": {{
        "arg1": "value1"
    }}
}}

- Do NOT explain what function to call - actually call it by returning the JSON
- Do NOT wrap JSON in markdown code blocks
- Do NOT add any text before or after the JSON
- Only respond without JSON if the question is a greeting or doesn't require data/action
"""

        response_text = self.generate(
            prompt=prompt,
            system_prompt=full_system_prompt,
            temperature=0.1  # Lower temperature for more consistent JSON
        )

        # Try to extract and parse JSON from response
        response_json = self.extract_json(response_text)

        if response_json and "function" in response_json and "arguments" in response_json:
            return {
                "type": "function_call",
                "function": response_json["function"],
                "arguments": response_json["arguments"]
            }

        # Not a function call, return as text
        return {
            "type": "text",
            "content": response_text
        }

    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from text that might contain markdown code blocks

        Args:
            text: Text potentially containing JSON

        Returns:
            Parsed JSON or None
        """
        import re

        # First, try direct parse (strip whitespace)
        text_stripped = text.strip()
        try:
            return json.loads(text_stripped)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block (```json or just ```)
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding any JSON object in the text
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        for potential_json in matches:
            try:
                parsed = json.loads(potential_json)
                # Check if it looks like a function call
                if "function" in parsed and "arguments" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

        return None

    def list_models(self) -> List[str]:
        """
        List available models in Ollama

        Returns:
            List of model names
        """
        try:
            models = self.client.list()
            return [model['name'] for model in models['models']]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama library

        Args:
            model_name: Model to pull (e.g., "llama3.1:8b")

        Returns:
            Success status
        """
        try:
            self.client.pull(model_name)
            logger.info(f"Successfully pulled model: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False


# Singleton instance
_ollama_client_instance: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create OllamaClient singleton"""
    global _ollama_client_instance
    if _ollama_client_instance is None:
        _ollama_client_instance = OllamaClient()
    return _ollama_client_instance
