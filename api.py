import os
from dotenv import load_dotenv

# --- IMPORTANT: load_dotenv() MUST be called BEFORE any imports
# that might depend on environment variables (like your agents or tools).
load_dotenv()

# --- Optional: Add debugging prints to confirm load_dotenv() worked ---
print(f"DEBUG (api.py): OPENAI_API_KEY loaded? {'Yes' if os.environ.get('OPENAI_API_KEY') else 'No'}")
print(f"DEBUG (api.py): OPENAI_API_KEY value (first 5 chars): {os.environ.get('OPENAI_API_KEY', '')[:5]}...")
# --- End Optional Debugging ---

from fastapi import FastAPI
from agents.sql_agent import sql_agent 
app = FastAPI()

@app.get("/")
def ping():
     return {"message": "SQL-to-PPT agent running"}