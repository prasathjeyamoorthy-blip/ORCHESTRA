import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()



def llm_parse(user_msg, field):

    NIM_API_KEY = os.getenv("NVIDIA_API_KEY")

    URL = "https://integrate.api.nvidia.com/v1/chat/completions"

    system_prompt = f"""
        You are a data extraction bot. 
        Your goal is to extract the {field} from the user's message.

        Rules:
        1. If the user provides information that could be the {field}, extract it.
        2. Return ONLY the JSON object. 
        3. If you are unsure, make your best guess based on the message.

        Target Format: {{ "{field}": "extracted_value" }}
    """
    
    r = requests.post(
        URL,
        headers={
            "Authorization": f"Bearer {NIM_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta/llama-3.1-70b-instruct",
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ]
        }
        ,timeout=10
    )

    print(r.status_code)
    #print(r.json())

    try:
        content = r.json()["choices"][0]["message"]["content"]
        print("LLM RAW:", content)

        # safety: extract JSON only
        start = content.find("{")
        end = content.rfind("}") + 1

        #if start != -1 and end != -1:
        return json.loads(content[start:end])

        #return {}

    except Exception as e:
        print("LLM ERROR:", e)
        return {}
