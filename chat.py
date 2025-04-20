import json
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini client
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
)

# System prompt / instruction
system_prompt = """
You are an AI assistant who is expert in breaking down complex problems and then resolving the user query.

Follow these steps:
1. Analyse the user input.
2. Think step by step how you would solve it.
3. Think again from another perspective.
4. Output a possible solution.
5. Validate the solution.
6. Give the final result.

Respond only using the following JSON format:
{ "step": "string", "content": "string" }

Always perform one step at a time and wait for the next input.

Example:
User Input: What is 2 + 2?
Response 1: { "step": "analyse", "content": "Alright! The user is interested in a maths query and is asking a basic arithmetic operation" }
Response 2: { "step": "think", "content": "To perform the addition I must go from left to right and add all the operands" }
Response 3: { "step": "output", "content": "4" }
Response 4: { "step": "validate", "content": "Seems like 4 is the correct answer for 2 + 2" }
Response 5: { "step": "result", "content": "2 + 2 = 4 and that is calculated by adding all numbers" }
"""

# Get initial user input
query = input("> ")

# Initialize message history
messages = [
    types.Content(
        role="user",
        parts=[types.Part.from_text(text=f"{system_prompt}\nUser Input: {query}")],
    )
]

while True:
    # Send to Gemini
    response = client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=messages,
        config=types.GenerateContentConfig(
            max_output_tokens=200,
            response_mime_type="application/json",
        ),
    )

    parsed_response = json.loads(response.candidates[0].content.parts[0].text)

    step = parsed_response.get("step")
    content = parsed_response.get("content")

    if not step or not content:
        print("⚠️ Response missing 'step' or 'content'")
        break

    if step.lower() == "result":
        print(f"🎉 [{step.upper()}]: {content}")
        break
    else:
        print(f"🧠 [{step.upper()}]: {content}")
        messages.append(
            types.Content(
                role="model",
                parts=[types.Part.from_text(text=json.dumps(parsed_response))],
            )
        )
