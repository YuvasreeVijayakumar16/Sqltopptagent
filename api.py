
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request

# Load env before importing sql_agent
load_dotenv()

# Debug prints
print(f"DEBUG (api.py): OPENAI_API_KEY loaded? {'Yes' if os.environ.get('OPENAI_API_KEY') else 'No'}")

# Import the configured agent
from agents.sql_agent import sql_agent  

app = FastAPI()

@app.get("/")
def ping():
    return {"message": "SQL-to-PPT agent running"}

@app.post("/query")
async def query_agent(request: Request):
    data = await request.json()
    question = data.get("question", "")
    if not question:
        return {"error": "Missing 'question' in request body"}
    
    try:
        response = sql_agent.initiate_chat(question)
        return {"response": response}
    except Exception as e:
        return {"error": str(e)}
