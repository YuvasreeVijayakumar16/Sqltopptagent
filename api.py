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
    "https://supplysense-test.azurewebsites.net",  # ✅ Azure UI
    "http://localhost:3000"                        # ✅ Local dev
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

        # === Extract Schema ===
        schema = extract_schema()
        if schema.startswith("❌"):
            return JSONResponse(status_code=500, content={"error": schema})

        # === Generate SQL with GPT ===
        system_prompt = f"""You are given the schema of a SQL Server database:\n{schema}\n\nGenerate a SQL SELECT query to answer:\n{question}"""
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

        # === Extract Result and PPT Path ===
        match = re.search(r"'result':\s*\[(.*?)\],\s*'ppt':\s*'([^']+\.pptx)'", final_message, re.DOTALL)
        if not match:
            return JSONResponse(status_code=500, content={"error": "No PPT path or result returned.", "raw": final_message})

        raw_output = "{'result': [" + match.group(1) + f"], 'ppt': '{match.group(2)}'}}"

        try:
            parsed = ast.literal_eval(raw_output)
        except Exception:
            try:
                cleaned = raw_output.replace("'", '"')
                cleaned = re.sub(r'(?<!")(\b\w+\b)(?=\s*:)', r'"\1"', cleaned)
                parsed = json.loads(cleaned)
            except Exception as json_err:
                return JSONResponse(status_code=500, content={
                    "error": f"Failed to parse GPT output: {str(json_err)}",
                    "raw_output": raw_output
                })

        ppt_path = parsed["ppt"]
        if not ppt_path or not os.path.exists(ppt_path):
            return JSONResponse(status_code=500, content={"error": "PPT file not found.", "ppt_path": ppt_path})

        # === Call External APIs ===
        api_root = "https://supplysenseaiapi-aadngxggarc0g6hz.z01.azurefd.net/api/iSCM/"

        # Step 1: Metadata Save
        save_url = f"{api_root}PostSavePPTDetailsV2?FileName={getencryptfilename}&CreatedBy={userprofilename}&Date={get_current_date()}"
        save_response = requests.post(save_url)

        if save_response.status_code != 200:
            return JSONResponse(status_code=500, content={
                "error": "Failed to call PostSavePPTDetailsV2",
                "save_status": save_response.status_code,
                "save_response": save_response.text
            })

        # Step 2: Upload File with Content
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
