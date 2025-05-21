# gemini_service.py
"""
Handles all interactions with the Google Generative AI (Gemini) API.
"""
import google.generativeai as genai
import logging
from typing import Optional, Union # <--- IMPORT Optional or Union

# Assuming config.py is in the parent directory or accessible via Python path
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    import config
except ImportError:
    # Define placeholders if config.py is missing, to allow basic loading
    # This is mainly for isolated testing; in a real run, config.py should exist.
    class ConfigPlaceholder:
        GEMINI_API_KEY = None
        GEMINI_MODEL_NAME = "gemini-1.5-flash-latest" # Default model
        GEMINI_MAX_OUTPUT_TOKENS = 2000
        GEMINI_TEMPERATURE = 0.7
        GEMINI_TOP_P = 1.0
        GEMINI_TOP_K = 1
    config = ConfigPlaceholder()
    print("WARNING: gemini_service.py could not import config.py. Using placeholder values.", file=sys.stderr)


# --- Logger Setup ---
logger = logging.getLogger(__name__)

class GeminiService:
    """
    A service class to interact with the Gemini API.
    """
    def __init__(self):
        """
        Initializes the GeminiService, configures the API key, and sets up the model.
        """
        if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
            logger.error("Gemini API Key is not configured in config.py. Gemini functionality will be disabled.")
            self.model = None
            return

        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.generation_config = genai.types.GenerationConfig(
                max_output_tokens=config.GEMINI_MAX_OUTPUT_TOKENS,
                temperature=config.GEMINI_TEMPERATURE,
                top_p=config.GEMINI_TOP_P,
                top_k=config.GEMINI_TOP_K,
            )
            self.model = genai.GenerativeModel(
                config.GEMINI_MODEL_NAME,
                generation_config=self.generation_config
            )
            logger.info(f"Gemini model '{config.GEMINI_MODEL_NAME}' initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}", exc_info=True)
            self.model = None

    async def generate_content(self, prompt: str) -> Optional[str]: # <--- CORRECTED TYPE HINT
        """
        Generates content using the Gemini model based on the provided prompt.

        Args:
            prompt: The input text prompt for the model.

        Returns:
            The generated text as a string, or None if an error occurs or the model is not initialized.
        """
        if not self.model:
            logger.warning("Gemini model is not initialized. Cannot generate content.")
            return None

        try:
            logger.debug(f"Sending prompt to Gemini (first 100 chars): '{prompt[:100]}...'")
            # Use generate_content_async for asynchronous operation
            response = await self.model.generate_content_async(prompt) 
            
            # Accessing response text safely
            # response.text might be the simplest way if only text is expected.
            # If parts are used, ensure they exist and have 'text' attribute.
            text_response = None
            if hasattr(response, 'text') and response.text:
                text_response = response.text
            elif hasattr(response, 'parts') and response.parts:
                text_response = "".join(part.text for part in response.parts if hasattr(part, 'text'))

            if text_response:
                logger.info(f"Successfully received response from Gemini. Length: {len(text_response)}")
                return text_response
            else:
                logger.warning("Gemini response was empty or did not contain usable text.")
                # Log prompt feedback if available, as it might indicate safety blocks etc.
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    logger.warning(f"Gemini prompt feedback: {response.prompt_feedback}")
                return None
        except Exception as e:
            logger.error(f"Error during Gemini content generation: {e}", exc_info=True)
            return None

# Example of how to instantiate and use the service (optional, for testing)
async def _test_gemini_service():
    """Internal test function for GeminiService."""
    # Ensure basic logging is configured for the test to see output
    logging.basicConfig(level=logging.INFO)
    
    if config.GEMINI_API_KEY and config.GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
        print("Testing Gemini Service...")
        service = GeminiService()
        if service.model:
            test_prompt = "Explain the concept of a Discord bot in simple terms."
            print(f"Sending test prompt: {test_prompt}")
            response_text = await service.generate_content(test_prompt)
            if response_text:
                print(f"Gemini Response:\n{response_text}")
            else:
                print("Failed to get a response from Gemini.")
        else:
            print("Gemini service could not be initialized for testing (model is None).")
    else:
        print("Skipping Gemini service test: API key not configured or is placeholder.")

if __name__ == "__main__":
    # This block allows you to test the gemini_service.py file directly.
    # Run with `python gemini_service.py`
    import asyncio
    asyncio.run(_test_gemini_service())
