from dotenv import load_dotenv
import os
load_dotenv()
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

print(f"API Key: {OPENROUTER_API_KEY}")
