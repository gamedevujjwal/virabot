import discord
import requests
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_KEY")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # Trigger only when bot is mentioned
    if client.user in message.mentions:
        user_message = re.sub(r"<@!?\\d+>", "", message.content).strip()

        if not user_message:
            await message.reply("Say something.")
            return

        await message.channel.typing()

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Your name is TEJ. "
                                "If anyone asks your name, ALWAYS reply exactly: My name is TEJ. "
                                "Never say you are an AI. "
                                "Always reply in English. Keep responses short and friendly."
                            )
                        },
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ]
                }
            )

            data = response.json()
            reply = data["choices"][0]["message"]["content"]

            await message.reply(reply)

        except Exception as e:
            print("Error:", e)
            await message.reply("Something went wrong.")

# Run bot
client.run(TOKEN)