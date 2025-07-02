
import os
import pyodbc  
from autogen_sql_ppt_project.tools.sql_to_ppt_tool import execute_sql
print(f"execute_sql imported: {execute_sql}") # This should print something like <function execute_sql at 0x...>
from dotenv import load_dotenv # Import load_dotenv

# === Load Environment Variables from .env file ===
load_dotenv()

from autogen import ConversableAgent, UserProxyAgent
from typing import Annotated


# === ENVIRONMENT ===
os.environ["AUTOGEN_USE_DOCKER"] = "False"



# === SQL CONNECTION (for schema preview) ===
def get_connection():
    return pyodbc.connect(
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={os.environ.get('SQL_SERVER')};"
        f"Database={os.environ.get('SQL_DATABASE')};"
        f"UID={os.environ.get('SQL_UID')};"
        f"PWD={os.environ.get('SQL_PASSWORD')};"
    )

# --- You can now access your variables like this ---
openai_api_key = os.environ.get("OPENAI_API_KEY")
sql_password = os.environ.get("SQL_PASSWORD") # You generally won't need to access password directly like this after it's used in connection
sql_server = os.environ.get("SQL_SERVER")
sql_database = os.environ.get("SQL_DATABASE")
sql_uid = os.environ.get("SQL_UID")

def extract_schema():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """)
            rows = cursor.fetchall()
            table_columns = {}
            for table, column, dtype in rows:
                table_columns.setdefault(table, []).append(f"{column} ({dtype})")
            schema = ""
            for table, cols in table_columns.items():
                schema += f"Table: {table}\n" + "\n".join([f" - {col}" for col in cols]) + "\n\n"
            return schema
    except Exception as e:
        return f"❌ Failed to get schema: {e}"

# === LLM CONFIG ===
llm_config = {
    "model": "gpt-4o",
    "api_key": openai_api_key,
    "temperature": 0.3,
}

# === AGENT SETUP ===
sql_agent = ConversableAgent(
    name="sql_agent",
    llm_config=llm_config,
    system_message="Generate SQL SELECT queries based on schema + question. Respond ONLY with execute_sql().",
    is_termination_msg=lambda msg: "tool_responses" in msg
)
print("SQL Agent created.")


# ✅ TOOL REGISTRATION
sql_agent.register_for_llm(name="execute_sql")(execute_sql)
print("execute_sql function registered with sql_agent.")


user = UserProxyAgent(
    name="user",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=5,
     # Add this line:
    function_map={"execute_sql": execute_sql}

)

# === MAIN ===
def main():
    schema = extract_schema()
    if schema.startswith("❌"):
        print(schema)
        return
    question = input("❓ Enter your SQL question: ").strip()
    if not question:
        print("⚠️  Please enter a valid question.")
        return

    system_prompt = f"""You are given the schema of a SQL Server database:\n{schema}\n\nGenerate a SQL query to answer:\n{question}"""
    user.initiate_chat(sql_agent, message=system_prompt)

if __name__ == "__main__":
    main()