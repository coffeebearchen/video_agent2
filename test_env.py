from dotenv import load_dotenv
import os

load_dotenv()

print("API KEY:", os.getenv("DEEPSEEK_API_KEY"))