
import discord
from discord.ext import commands, tasks
import aiohttp
import os

# Set your Wise Old Man clan ID, channel ID, and base URL
CLAN_ID = "2763"  # OSRS Defence clan ID
WISE_OLD_MAN_BASE_URL = "https://api.wiseoldman.net/v2"
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))  # Get from environment variable
TOKEN = os.getenv('DISCORD_TOKEN', '')  # Get from environment variable

# Define skills list in lowercase
skills_list = [
    "attack", "defence", "strength", "hitpoints", "ranged", "prayer",
    "magic", "cooking", "woodcutting", "fletching", "fishing", "firemaking",
    "crafting", "smithing", "mining", "herblore", "agility", "thieving",
    "slayer", "farming", "runecraft", "hunter", "construction"
]

# Offensive skills for filtering, in lowercase
offensive_skills = ["attack", "strength", "ranged", "magic"]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global dictionary to store the message objects for updating
highscore_messages = {
    "msg1": None,
    "msg2": None,
    "msg3": None
}

async def fetch_clan_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{WISE_OLD_MAN_BASE_URL}/clan/{CLAN_ID}/members") as resp:
            if resp.status != 200:
                return None
            return await resp.json()

def build_messages(clan_data):
    # Filter out users with offensive combat stats > 2
    filtered = []
    for player in clan_data:
        valid = True
        for skill in offensive_skills:
            level = player.get("skills", {}).get(skill, {}).get("level", 0)
            if level > 2:
                valid = False
                break
        if valid:
            filtered.append(player)
    
    # First message: Top 10 players by Total Level
    sorted_total = sorted(filtered, key=lambda x: (x.get("totalLevel", 0), x.get("totalXp", 0)), reverse=True)
    top_total = sorted_total[:10]
    msg1 = "**Top 10 by Total Level:**\n"
    for player in top_total:
        msg1 += f"- {player['username']} | Level: {player.get('totalLevel', 0)} | XP: {player.get('totalXp', 0)}\n"
    
    # Second message: Top 10 per Skill
    msg2 = "**Top 10 per Skill:**\n"
    for skill in skills_list:
        msg2 += f"\n**{skill.title()}:**\n"
        sorted_skill = sorted(
            filtered,
            key=lambda x: x.get("skills", {}).get(skill, {}).get("xp", 0),
            reverse=True
        )
        top_skill = sorted_skill[:10]
        for player in top_skill:
            skill_data = player.get("skills", {}).get(skill, {"level": 0, "xp": 0})
            msg2 += f"- {player['username']} | Level: {skill_data.get('level', 0)} | XP: {skill_data.get('xp', 0)}\n"
    
    # Third message: Top 10 per Boss KC
    boss_set = set()
    for player in filtered:
        boss_data = player.get("bosses", {})
        for boss in boss_data.keys():
            boss_set.add(boss)
    bosses_list = sorted(boss_set)
    
    msg3 = "**Top 10 per Boss KC:**\n"
    for boss in bosses_list:
        msg3 += f"\n**{boss.title()}:**\n"
        sorted_boss = sorted(
            filtered,
            key=lambda x: x.get("bosses", {}).get(boss, 0),
            reverse=True
        )
        top_boss = sorted_boss[:10]
        for player in top_boss:
            kc = player.get("bosses", {}).get(boss, 0)
            msg3 += f"- {player['username']} | KC: {kc}\n"
    
    return msg1, msg2, msg3

@bot.tree.command(name="clanhighscores", description="Show clan highscores")
async def clanhighscores(interaction: discord.Interaction):
    await interaction.response.defer()
    clan_data = await fetch_clan_data()
    if clan_data is None:
        await interaction.followup.send("Error fetching clan data.")
        return
    msg1, msg2, msg3 = build_messages(clan_data)
    channel = interaction.channel
    if highscore_messages["msg1"] is None:
        highscore_messages["msg1"] = await channel.send(msg1)
        highscore_messages["msg2"] = await channel.send(msg2)
        highscore_messages["msg3"] = await channel.send(msg3)
    else:
        await highscore_messages["msg1"].edit(content=msg1)
        await highscore_messages["msg2"].edit(content=msg2)
        await highscore_messages["msg3"].edit(content=msg3)
    await interaction.followup.send("Highscores updated!")

@tasks.loop(hours=24)
async def update_highscores_task():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("Channel not found.")
        return
    clan_data = await fetch_clan_data()
    if clan_data is None:
        print("Error fetching clan data in background task.")
        return
    msg1, msg2, msg3 = build_messages(clan_data)
    if highscore_messages["msg1"] is None:
        highscore_messages["msg1"] = await channel.send(msg1)
        highscore_messages["msg2"] = await channel.send(msg2)
        highscore_messages["msg3"] = await channel.send(msg3)
    else:
        try:
            await highscore_messages["msg1"].edit(content=msg1)
            await highscore_messages["msg2"].edit(content=msg2)
            await highscore_messages["msg3"].edit(content=msg3)
        except Exception as e:
            print("Error editing messages: ", e)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    await bot.tree.sync()
    update_highscores_task.start()

if __name__ == "__main__":
    if not TOKEN:
        print("Please set the DISCORD_TOKEN environment variable")
        exit(1)
    if CHANNEL_ID == 0:
        print("Please set the CHANNEL_ID environment variable")
        exit(1)
    bot.run(TOKEN)
