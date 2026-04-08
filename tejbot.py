import discord
import requests
import re
import os

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

    print("MESSAGE:", message.content)

    # detect mention
    if f"<@{client.user.id}>" in message.content or f"<@!{client.user.id}>" in message.content:

        user_message = re.sub(r"<@!?\\d+>", "", message.content).strip()

        if not user_message:
            await message.reply("Say something.")
            return

        await message.channel.typing()

        try:
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": API_KEY
                },
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": "Your name is TEJ. Reply in English. " + user_message
                                }
                            ]
                        }
                    ]
                }
            )

            data = response.json()
            print("API RESPONSE:", data)

            # safe parsing
            reply = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")

            if not reply:
                reply = "API error 😅"

            await message.reply(reply)

        except Exception as e:
            print("ERROR:", e)
            await message.reply("Something broke 😅")

client.run(TOKEN)