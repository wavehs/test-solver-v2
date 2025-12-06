import os
import google.generativeai as genai
from dotenv import load_dotenv
from config_manager import load_config

load_dotenv()

config = load_config()
api_key = config.get("gemini_api_key")

if not api_key:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in config or .env")

genai.configure(api_key=api_key)

# Configuration for the model
generation_config = {
  "temperature": 0.1,
  "top_p": 1,
  "top_k": 1,
}

model_name = config.get("gemini_model", "gemini-2.5-pro")
model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)

SYSTEM_PROMPT = """
Analyze the screenshot. Identify ALL multiple choice questions visible.
For each question, determine the correct option.
Output rules:
1. List the correct option for each question found.
2. Use the format: "Q[Number]: [Option]" (e.g., "Q12: B").
3. If numbers are not visible, just list the answers separated by " | ".
4. Keep it concise.
5. Do not use markdown.
"""

import logging

logger = logging.getLogger(__name__)

def get_answer(image_bytes):
    """
    Sends the image to Gemini and returns the text response.
    """
    try:
        # Image bytes need to be in a format Gemini accepts. 
        # The library supports PIL images directly or bytes.
        # We passed BytesIO, so we can get bytes from it.
        image_data = {
            "mime_type": "image/png",
            "data": image_bytes.getvalue()
        }

        logger.debug(f"Sending request to model: {model.model_name}")
        response = model.generate_content([SYSTEM_PROMPT, image_data])
        
        logger.debug("Response received from Gemini.")
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return "Err"
