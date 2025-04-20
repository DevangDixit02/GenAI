import json
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import requests

load_dotenv()

client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
)


def get_weather(city: str):
    # TODO!: Do an actual API Call
    print("🔨 Tool Called: get_weather", city)

    url = f"https://wttr.in/{city}?format=%C+%t"
    response = requests.get(url)

    if response.status_code == 200:
        return f"The weather in {city} is {response.text}."
    return "Something went wrong"


def run_command(command):
    result = os.system(command=command)
    return result


avaiable_tools = {
    "get_weather": {
        "fn": get_weather,
        "description": "Takes a city name as an input and returns the current weather for the city",
    },
    "run_command": {
        "fn": run_command,
        "description": "Takes a command as input to execute on system and returns ouput",
    },
}

system_prompt = """
You are an AI assistant who is expert in breaking down complex problems and then resolving the user query.You work on start, plan, action, observe mode.
For the given user query and available tools, plan the step by step execution, based on the planning,
select the relevant tool from the available tool. and based on the tool selection you perform an action to call the tool.
Wait for the observation and based on the observation from the tool call resolve the user query.

Rules:
- Follow the Output JSON Format.
- Always perform one step at a time and wait for next input
- Carefully analyse the user query

Output JSON Format:
{{
    "step": "string",
    "content": "string",
    "function": "The name of function if the step is action",
    "input": "The input parameter for the function"
}}

Available Tools:
- get_weather: Takes a city name as an input and returns the current weather for the city
- run_command: Takes a command as input to execute on system and returns ouput


Example:
User Query: What is the weather of new york?
Output: {{ "step": "plan", "content": "The user is interested in weather data of new york" }}
Output: {{ "step": "plan", "content": "From the available tools I should call get_weather" }}
Output: {{ "step": "action", "function": "get_weather", "input": "new york" }}
Output: {{ "step": "observe", "output": "12 Degree Cel" }}
Output: {{ "step": "output", "content": "The weather for new york seems to be 12 degrees." }}
"""

messages = [
    types.Content(
        role="user",
        parts=[types.Part.from_text(text=f"{system_prompt}")],
    )
]

while True:
    userQuery = input("> ")
    messages.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"{userQuery}")],
        )
    )
    while True:
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=messages,
            config=types.GenerateContentConfig(
                max_output_tokens=400,
                response_mime_type="application/json",
            ),
        )
        parsedResponse = json.loads(response.candidates[0].content.parts[0].text)

        messages.append(
            types.Content(
                role="assistant",
                parts=[types.Part.from_text(text=json.dumps(parsedResponse))],
            )
        )

        if parsedResponse["step"].lower() == "plan":
            print(f"🧠 [{parsedResponse['step'].upper()}]: {parsedResponse['content']}")
            continue

        if parsedResponse["step"].lower() == "action":
            toolName = parsedResponse["function"]
            toolInput = parsedResponse["input"]

            if avaiable_tools.get(toolName, False):
                output = avaiable_tools[toolName].get("fn")(toolInput)
                messages.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=json.dumps({"step": "observe", "output": output}))
                        ],
                    )
                )
                continue

        if parsedResponse.get("step").lower() == "output":
            print(f"🤖: {parsedResponse.get('content')}")
            break
