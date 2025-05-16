# gemini_service.py
"""
Handles all interactions with the Google Generative AI (Gemini) API.
"""
import google.generativeai as genai
import logging
from config import GEMINI_API_KEY, GEMINI_MODEL_NAME, GEMINI_MAX_OUTPUT_TOKENS, GEMINI_TEMPERATURE, GEMINI_TOP_P, GEMINI_TOP_K

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
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
            logger.error("Gemini API Key is not configured in config.py. Gemini functionality will be disabled.")
            self.model = None
            return

        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.generation_config = genai.types.GenerationConfig(
                max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                temperature=GEMINI_TEMPERATURE,
                top_p=GEMINI_TOP_P,
                top_k=GEMINI_TOP_K,
            )
            self.model = genai.GenerativeModel(
                GEMINI_MODEL_NAME,
                generation_config=self.generation_config
            )
            logger.info(f"Gemini model '{GEMINI_MODEL_NAME}' initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None

    async def generate_content(self, prompt: str) -> str | None:
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
            logger.debug(f"Sending prompt to Gemini: '{prompt[:100]}...'") # Log a snippet of the prompt
            response = await self.model.generate_content_async(prompt) # Use async version
            
            if response.parts:
                # Accessing text directly from response.text is simpler if only text is expected
                # If more complex parts are possible, iterate through response.parts
                text_response = "".join(part.text for part in response.parts if hasattr(part, 'text'))
                if text_response:
                    logger.info(f"Successfully received response from Gemini. Length: {len(text_response)}")
                    return text_response
                else:
                    logger.warning("Gemini response contained no text.")
                    return None
            elif response.text: # Fallback for simpler text-only responses
                 logger.info(f"Successfully received response from Gemini. Length: {len(response.text)}")
                 return response.text
            else:
                logger.warning("Gemini response was empty or did not contain usable parts.")
                # You might want to inspect response.prompt_feedback here for safety ratings etc.
                if response.prompt_feedback:
                    logger.warning(f"Prompt feedback: {response.prompt_feedback}")
                return None
        except Exception as e:
            logger.error(f"Error during Gemini content generation: {e}")
            return None

# Example of how to instantiate and use the service (optional, for testing)
async def _test_gemini_service():
    """Internal test function for GeminiService."""
    if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
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
            print("Gemini service could not be initialized for testing.")
    else:
        print("Skipping Gemini service test: API key not configured.")

if __name__ == "__main__":
    # This block allows you to test the gemini_service.py file directly.
    # You'll need to run it with `python -m asyncio gemini_service.py` if using Python 3.7+ for async
    # or just `python gemini_service.py` and it will use `asyncio.run` if available.
    import asyncio
    logging.basicConfig(level=logging.INFO) # Setup basic logging for the test
    asyncio.run(_test_gemini_service())
