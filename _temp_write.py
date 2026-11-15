import os
import sys
import traceback
from dotenv import load_dotenv; load_dotenv()
from groq import Groq

logger = logging.getLogger(__name__)

_groq_api_key = os.getenv("GROQ_API_KEY")

if not _groq_api_key:
    raise RuntimeError('GROQ_API_KEY is not set. Please create a .env file with: GROQ_API_KEY=your_key_here')

client = Groq(api_key=_groq_api_key)

def get_jarvis_response(user_prompt: str, market_context: str = '') -> str:
    try:
        full_prompt = user_prompt
        if market_context:
            full_prompt = f'Live Market Data: {market_context}\n        User Query: {user_prompt}'
        response = client.chat.completions.create(model='llama-3.1-70b-versatile', messages=[{'role': 'system', 'content': 'You are JARVIS, an AI assistant communicating directly via Groq API. Talk to the user naturally and helpfully.'}, {'role': 'user', 'content': full_prompt}], temperature=0.7, max_tokens=600)
        return response.choices[0].message.content
    except Exception as e:
        print(f'🔥 GROQ API EXCEPTION CAUGHT: {e}', flush=True)
        traceback.print_exc(file=sys.stderr)
        raise e