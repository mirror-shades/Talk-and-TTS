import os
from dotenv import load_dotenv

def load_api_key():
    load_dotenv()
    return os.getenv('API_KEY')

def save_api_key(api_key):
    with open('.env', 'w') as f:
        f.write(f"API_KEY='{api_key}'")