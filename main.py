
import discord
from discord.ext import commands, tasks
import aiohttp
import os

# Set your Wise Old Man clan ID, channel ID, and base URL
CLAN_ID = "2763"  # OSRS Defence clan ID
WISE_OLD_MAN_BASE_URL = "https://api.wiseoldman.net/v3"  # Updated to v3
CHANNEL_ID = 969159797058437170  # OSRS Defence Discord channel
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
    try:
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Discord-Bot/1.0'
        }
        async with aiohttp.ClientSession() as session:
            url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}"  # First fetch group details
            print(f"Fetching group details from: {url}")
            async with session.get(url, headers=headers) as resp:
                if resp.status == 404:
                    print("Group not found. Please verify the group ID.")
                    return None
                if resp.status != 200:
                    print(f"Error status: {resp.status}")
                    error_text = await resp.text()
                    print(f"Error response: {error_text}")
                    return None
                
                # Now fetch the members stats
                url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/members"
                print(f"Fetching members data from: {url}")
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        print(f"Error status: {resp.status}")
                        error_text = await resp.text()
                        print(f"Error response: {error_text}")
                        return None
                    try:
                        content_type = resp.headers.get('Content-Type', '')
                        print(f"Response content type: {content_type}")
                        text_data = await resp.text()
                        print(f"Raw response: {text_data[:200]}...")  # Print first 200 chars
                        data = await resp.json()
                        if not data:
                            print("Empty data received from API")
                            return None
                        if 'players' not in data:
                            print(f"No players field in data. Keys: {data.keys()}")
                            return None
                        print(f"Successfully fetched data for {len(data['players'])} members")
                        return data['players']
                    except Exception as e:
                        print(f"Error parsing JSON response: {str(e)}")
                        return None
    except Exception as e:
        print(f"Error fetching clan data: {str(e)}")
        return None

def build_messages(clan_data):
    if not clan_data:
        print("No clan data received")
        return None, None, None
        
    # Filter out users with offensive combat stats > 2
    filtered = []
    for player in clan_data:
        if not isinstance(player, dict):
            print(f"Invalid player data format: {player}")
            continue
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
    try:
        clan_data = await fetch_clan_data()
        if clan_data is None:
            await interaction.followup.send("Error fetching clan data. Please try again later.")
            return
        msg1, msg2, msg3 = build_messages(clan_data)
        if msg1 is None or msg2 is None or msg3 is None:
            await interaction.followup.send("Error processing clan data. Please try again later.")
            return
        
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
    except Exception as e:
        print(f"Error in clanhighscores command: {e}")
        await interaction.followup.send("An error occurred while updating highscores.")
        return

@tasks.loop(hours=24)
async def update_highscores_task():
    try:
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
    except Exception as e:
        print(f"Error in update task: {e}")

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
