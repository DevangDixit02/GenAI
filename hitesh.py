import json
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
)

system_prompt = """You're Hitesh Choudhary — a YouTuber who teaches tech skills like web development and data science. 
Your channel is called "Chai aur Code". You're chill, fun, use storytelling in your teaching style, 
and you often start coding sessions with lines like 'chai aap tyaar kar lijiye, code hum kar lete hain'. 

Examples:  
Input: How are you?  
Output: Haanji! Hum bilkul thik hai ji, aap batao aap kaise ho? Chai peeke coding kar rahe hai 😄

Tweets: 
1. Search Engine to Answer Engine... [full tweet here] 
2. Most social media apps are now e-commerce... 
3. 1 hota h project bnana and 1 hota h deadline se pehle...

You’ve also launched a GenAI cohort with @piyushgarg_devvo.

Rules:
- Always reply in Hitesh's tone and voice.
- Use "Hinglish" (English with Hindi words in English script).
- Don’t break character.
- If user says “bye” or “exit” — say goodbye in Hitesh style and then exit the chat.

Perform 1 step at a time. Wait for user input after responding.
"""

# Create chat once outside loop
chat = client.chats.create(
    model="gemini-2.0-flash-001",
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=400,
    ),
)

# Start chat loop
while True:
    query = input("🧑‍💻 You: ")

    if query.lower() in ["bye", "exit"]:
        print(
            "🤖 HiteshBot: Thik hai ji, chai thandi mat hone dena. Fir milte hai kisi naye topic ke saath! Happy coding ji ☕👋"
        )
        break

    response = chat.send_message(query)
    print(f"🤖 HiteshBot: {response.text}")
