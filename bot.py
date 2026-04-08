import os
import re
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from googletrans import Translator

# ── Intents ────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# ── Bot & Translator setup ─────────────────────────────────────────────────────
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
translator = Translator()

# In-memory welcome messages: { guild_id: "message text" }
welcome_messages: dict[int, str] = {}


# ══════════════════════════════════════════════════════════════════════════════
#  EVENTS
# ══════════════════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Slash commands synced.")


# ── Welcome System ─────────────────────────────────────────────────────────────
@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild

    msg_template = welcome_messages.get(
        guild.id,
        "Welcome to **{guild}**, {mention}! We're glad to have you here. 🎉"
    )

    msg = (
        msg_template
        .replace("{mention}", member.mention)
        .replace("{user}", str(member))
        .replace("{guild}", guild.name)
    )

    channel = guild.system_channel
    if channel is None:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                channel = ch
                break

    if channel:
        await channel.send(msg)


# ── Mention-based Translation (completely separate from slash commands) ─────────
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if bot.user in message.mentions:
        text = re.sub(r"<@!?[0-9]+>", "", message.content).strip()

        if not text:
            await message.reply("Mention me with some text and I'll translate it to English!")
            return

        try:
            result = translator.translate(text, dest="en")
            translated = result.text
            src_lang = result.src

            if src_lang == "en":
                await message.reply(f"This is already in English:\n**{translated}**")
            else:
                await message.reply(f"**Translation ({src_lang} → en):**\n{translated}")

        except Exception as e:
            await message.reply(f"❌ Translation failed: {e}")

        return  # stop here — don't fall through to process_commands

    await bot.process_commands(message)


# ══════════════════════════════════════════════════════════════════════════════
#  SLASH COMMANDS — MODERATION
# ══════════════════════════════════════════════════════════════════════════════

# ── /kick ──────────────────────────────────────────────────────────────────────
@tree.command(name="kick", description="Kick a member from the server.")
@app_commands.describe(member="Member to kick", reason="Reason for kicking")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):
    if member == interaction.user:
        await interaction.response.send_message("You cannot kick yourself.", ephemeral=True)
        return
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message(
            "You cannot kick someone with an equal or higher role.", ephemeral=True
        )
        return
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"✅ **{member}** has been kicked. Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permission to kick that member.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ Failed to kick: {e}", ephemeral=True)

@kick.error
async def kick_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Kick Members** permission.", ephemeral=True)


# ── /ban ───────────────────────────────────────────────────────────────────────
@tree.command(name="ban", description="Ban a member from the server.")
@app_commands.describe(member="Member to ban", reason="Reason for banning", delete_days="Days of messages to delete (0–7)")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided",
    delete_days: int = 0
):
    if member == interaction.user:
        await interaction.response.send_message("You cannot ban yourself.", ephemeral=True)
        return
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message(
            "You cannot ban someone with an equal or higher role.", ephemeral=True
        )
        return
    delete_days = max(0, min(7, delete_days))
    try:
        await member.ban(reason=reason, delete_message_days=delete_days)
        await interaction.response.send_message(f"🔨 **{member}** has been banned. Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permission to ban that member.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ Failed to ban: {e}", ephemeral=True)

@ban.error
async def ban_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Ban Members** permission.", ephemeral=True)


# ── /timeout ───────────────────────────────────────────────────────────────────
@tree.command(name="timeout", description="Timeout (mute) a member for N minutes.")
@app_commands.describe(member="Member to timeout", minutes="Duration in minutes", reason="Reason for timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout_member(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: int,
    reason: str = "No reason provided"
):
    if member == interaction.user:
        await interaction.response.send_message("You cannot timeout yourself.", ephemeral=True)
        return
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message(
            "You cannot timeout someone with an equal or higher role.", ephemeral=True
        )
        return
    if minutes <= 0:
        await interaction.response.send_message("Duration must be greater than 0 minutes.", ephemeral=True)
        return
    try:
        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        await interaction.response.send_message(
            f"⏱️ **{member}** timed out for **{minutes} minute(s)**. Reason: {reason}"
        )
    except discord.Forbidden:
        await interaction.response.send_message("❌ I lack permission to timeout that member.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ Failed to timeout: {e}", ephemeral=True)

@timeout_member.error
async def timeout_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Moderate Members** permission.", ephemeral=True)


# ── /clear ─────────────────────────────────────────────────────────────────────
@tree.command(name="clear", description="Delete a number of messages from this channel.")
@app_commands.describe(amount="Number of messages to delete (1–100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    if not 1 <= amount <= 100:
        await interaction.response.send_message("Please provide a number between 1 and 100.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🗑️ Deleted **{len(deleted)}** message(s).", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ I lack permission to delete messages.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Failed to clear: {e}", ephemeral=True)

@clear.error
async def clear_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Manage Messages** permission.", ephemeral=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SLASH COMMANDS — WELCOME SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

@tree.command(name="setwelcome", description="Set a custom welcome message for this server.")
@app_commands.describe(message="Welcome message. Use {mention}, {user}, {guild} as placeholders.")
@app_commands.checks.has_permissions(administrator=True)
async def setwelcome(interaction: discord.Interaction, message: str):
    welcome_messages[interaction.guild_id] = message
    preview = (
        message
        .replace("{mention}", interaction.user.mention)
        .replace("{user}", str(interaction.user))
        .replace("{guild}", interaction.guild.name)
    )
    await interaction.response.send_message(
        f"✅ Welcome message updated!\n\n**Preview:**\n{preview}",
        ephemeral=True
    )

@setwelcome.error
async def setwelcome_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Administrator** permission.", ephemeral=True)


# ══════════════════════════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════════════════════════
bot.run(os.getenv("TOKEN"))
