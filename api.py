from fastapi import FastAPI, Request
from agents.sql_agent import sql_agent
from autogen import UserProxyAgent

app = FastAPI()

@app.get("/")
def ping():
    return {"message": "SQL-to-PPT agent running"}

@app.post("/query")
async def ask_sql_question(request: Request):
    data = await request.json()
    question = data.get("question", "")
    if not question:
        return {"error": "No question provided."}

    # Optional: Extract schema if your sql_agent needs it dynamically
    system_message = f"You are given a SQL database. Generate a SQL SELECT query to answer:\n{question}"

    user = UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        function_map={"execute_sql": sql_agent._tool_name_map["execute_sql"]},
    )

    chat_result = user.initiate_chat(sql_agent, message=system_message)
    return {"status": "success", "response": chat_result}
