import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from huawei_tools import huawei_tools
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable not set.")

client = OpenAI()




user_message = input("Enter your message: ")
response = client.responses.create(
    model="gpt-4.1",
    input=[{"role": "user", "content": user_message}],
    tools=huawei_tools
)



print('====================================type===============================================')
for item in response.output:
    print(item.type)
    if (item.type == "function_call"):
        print(item.arguments)
        print(item.name)
print('=============================response output======================================================')
print(response.output)

print('===================================================================================')
