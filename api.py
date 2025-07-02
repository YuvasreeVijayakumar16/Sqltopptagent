import os
import uuid
import re
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
from agents.sql_agent import sql_agent
from entrypoint import extract_schema
from tools.sql_to_ppt_tool import execute_sql
from autogen import UserProxyAgent

load_dotenv()

app = FastAPI()

@app.get("/")
def ping():
    return {"message": "SQL-to-PPT agent running"}

@app.post("/generate-ppt")
async def generate_ppt(request: Request):
    try:
        data = await request.json()
        question = data.get("question", "")
        if not question:
            return JSONResponse(status_code=400, content={"error": "Missing 'question'"})

        schema = extract_schema()
        if schema.startswith("❌"):
            return JSONResponse(status_code=500, content={"error": schema})

        system_prompt = f"""You are given the schema of a SQL Server database:\n{schema}\n\nGenerate a SQL SELECT query to answer:\n{question}"""

        # Register tool
        sql_agent.register_for_llm(name="execute_sql")(execute_sql)

        user = UserProxyAgent(
            name="user",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=5,
            function_map={"execute_sql": execute_sql}
        )

        # Run the agent
        chat_result = user.initiate_chat(sql_agent, message=system_prompt)

        # Extract last message content
        final_message = chat_result.chat_history[-1].get("content", "")
        print("Final message content:\n", final_message)

        # Regex to extract .pptx path
        match = re.search(r"'ppt':\s*'([^']+\.pptx)'", final_message)
        if not match:
            return JSONResponse(status_code=500, content={"error": "Could not extract PPT path from response."})

        ppt_path = match.group(1)

        if not ppt_path or not os.path.exists(ppt_path):
            return JSONResponse(status_code=500, content={"error": "PPT file not found at expected location."})

        return FileResponse(
            path=ppt_path,
            filename="AutoGen_Report.pptx",
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
