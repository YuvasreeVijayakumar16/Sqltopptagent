import os
from autogen import ConversableAgent, UserProxyAgent
from tools.sql_to_ppt_tool import execute_sql # type: ignore
from dotenv import load_dotenv

llm_config = { 
    "model": "gpt-4o",
    "api_key": os.environ.get("OPENAI_API_KEY"),
    "temperature": 0.3,
}
# Optional: Add a check if the API key wasn't loaded
if llm_config["api_key"] is None:
    raise ValueError("OPENAI_API_KEY environment variable not found. Please set it in your .env file or system environment.")

sql_agent = ConversableAgent(
    name="sql_agent",
    llm_config=llm_config,
    system_message="Generate SQL SELECT queries based on schema + question. Respond ONLY with execute_sql().",
    is_termination_msg=lambda msg: "tool_responses" in msg,
     human_input_mode="NEVER",
    max_consecutive_auto_reply=5 
)

user = UserProxyAgent(
    name="user",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=5,
)

# Register tool
sql_agent.register_for_execution()(execute_sql)
user.register_for_execution()(execute_sql)
