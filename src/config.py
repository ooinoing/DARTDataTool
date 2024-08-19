import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get DART API Key from environment variables
DART_API_KEY = os.getenv("DART_API_KEY")
DATA_PATH = "/Users/jiho/Projects/kubs/data"
