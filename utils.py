# utils.py

import os
import logging
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = "self_healing.log"

# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def get_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OpenAI API key is not set. Please add it to the .env file.")
        raise ValueError("OpenAI API key is missing.")
    return api_key

def log_info(message):
    logging.info(message)
    print(f"[INFO] {message}")

def log_warning(message):
    logging.warning(message)
    print(f"[WARNING] {message}")

def log_error(message):
    logging.error(message)
    print(f"[ERROR] {message}")
