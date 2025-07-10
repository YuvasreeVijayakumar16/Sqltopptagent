import os
import re
import json
import ast
import requests
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from agents.sql_agent import sql_agent
from entrypoint import extract_schema
from tools.sql_to_ppt_tool import execute_sql
from autogen import UserProxyAgent

load_dotenv()

app = FastAPI()

# === ✅ CORS Setup ===
origins = [
    "https://supplysense-test.azurewebsites.net",  # Azure UI
    "http://localhost:8080"                        # Local dev
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def ping():
    return {"message": "✅ SQL-to-PPT agent is running"}

def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")

@app.post("/generate-ppt")
async def generate_ppt(request: Request):
    try:
        data = await request.json()
        question = data.get("question", "")
        getencryptfilename = data.get("getencryptfilename")
        userprofilename = data.get("userprofilename")

        if not question or not getencryptfilename or not userprofilename:
            return JSONResponse(status_code=400, content={
                "error": "Missing one of: 'question', 'getencryptfilename', 'userprofilename'"
            })

        schema = extract_schema()
        if schema.startswith("❌"):
            return JSONResponse(status_code=500, content={"error": schema})

        system_prompt = f"""
You are a SQL expert working with the following SQL Server schema:
{schema}

Only use tables and columns that exist in this schema. 
Do not invent table or column names. Always validate joins based on shared keys.
Avoid using tables like 'MaterialDetails' or 'MaterialTransactions' unless they appear in the schema.

Now, generate a well-structured SQL SELECT query to answer:
\"{question}\"
"""
        sql_agent.register_for_llm(name="execute_sql")(execute_sql)

        user = UserProxyAgent(
            name="user",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=5,
            function_map={"execute_sql": execute_sql}
        )

        chat_result = user.initiate_chat(sql_agent, message=system_prompt)
        final_message = chat_result.chat_history[-1].get("content", "")
        print("Final message:\n", final_message)

        # === Extract Result + PPT Path ===
        match = re.search(r"'result':\s*\[(.*?)\],\s*'ppt':\s*'([^']+\.pptx)'", final_message, re.DOTALL)
        if not match:
            return JSONResponse(status_code=500, content={"error": "No PPT path or result returned.", "raw": final_message})

        raw_output = "{'result': [" + match.group(1) + f"], 'ppt': '{match.group(2)}'}}"

        # === Fix datetime.date(...) in the output ===
        cleaned_output = re.sub(r"datetime\.date\((\d+),\s*(\d+),\s*(\d+)\)", r"'\1-\2-\3'", raw_output)

        try:
            parsed = ast.literal_eval(cleaned_output)
        except Exception as eval_err:
            return JSONResponse(status_code=500, content={
                "error": f"Failed to parse GPT output: {str(eval_err)}",
                "raw_output": cleaned_output
            })

        ppt_path = parsed["ppt"]
        if not ppt_path or not os.path.exists(ppt_path):
            return JSONResponse(status_code=500, content={"error": "PPT file not found.", "ppt_path": ppt_path})

        # === Step 1: Save Metadata ===
        api_root = "https://supplysenseaiapi-aadngxggarc0g6hz.z01.azurefd.net/api/iSCM/"
        save_url = f"{api_root}PostSavePPTDetailsV2?FileName={getencryptfilename}&CreatedBy={userprofilename}&Date={get_current_date()}"
        save_response = requests.post(save_url)

        if save_response.status_code != 200:
            return JSONResponse(status_code=500, content={
                "error": "Failed to call PostSavePPTDetailsV2",
                "save_status": save_response.status_code,
                "save_response": save_response.text
            })

        # === Step 2: Upload PPT File ===
        filtered_obj = {
            "slide": 1,
            "title": "Auto-generated Slide",
            "data": question
        }
        formatdata = {"content": [filtered_obj]}

        with open(ppt_path, "rb") as ppt_file:
            files = {
                "file": (getencryptfilename, ppt_file, "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
                "content": (None, json.dumps(formatdata), "application/json")
            }
            upload_url = f"{api_root}UpdatePptFileV2?FileName={getencryptfilename}&CreatedBy={userprofilename}"
            upload_response = requests.post(upload_url, files=files)

        return {
            "message": "✅ PPT successfully created and sent",
            "ppt_path": ppt_path,
            "upload_status": upload_response.status_code,
            "upload_response": upload_response.text
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

