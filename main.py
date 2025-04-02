import discord
from discord.ext import commands, tasks
import aiohttp
import os
import json
import requests
from typing import Dict, List, Tuple, Optional, Any

# Set your Wise Old Man clan ID, channel ID, and base URL
CLAN_ID = "2763"  # OSRS Defence clan ID
WISE_OLD_MAN_BASE_URL = "https://api.wiseoldman.net/v2"  # Using v2 API
CHANNEL_ID = 969159797058437170  # OSRS Defence Discord channel
TOKEN = os.getenv('DISCORD_TOKEN', '')  # Get from environment variable

# Define skills list
SKILLS = [
    "overall", "attack", "defence", "strength", "hitpoints", "ranged", "prayer",
    "magic", "cooking", "woodcutting", "fletching", "fishing", "firemaking",
    "crafting", "smithing", "mining", "herblore", "agility", "thieving",
    "slayer", "farming", "runecraft", "hunter", "construction"
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents, activity=discord.Game(name="!clanhighscores"))

# Global dictionary to store the message objects for updating
highscore_messages = {
    "total": None,
    "skills": None,
    "bosses": None
}

async def fetch_clan_data():
    """Fetch clan hiscores data from Wise Old Man API"""
    print(f"Fetching clan data for clan ID: {CLAN_ID}")

    headers = {
        'Accept': 'application/json',
        'User-Agent': 'OSRS-Clan-Discord-Bot/1.0'
    }

    # Main endpoint to get hiscores data
    hiscores_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/hiscores"

    try:
        print(f"Requesting hiscores from: {hiscores_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(hiscores_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Successfully fetched hiscores data with {len(data)} entries")
                    if len(data) > 0:
                        print(f"Sample player data: {json.dumps(data[0], indent=2)[:200]}...")
                    return data
                else:
                    print(f"Failed to fetch clan data: {response.status}")
                    print(await response.text())
                    return None
    except Exception as e:
        print(f"Error fetching clan data: {e}")

        # Fallback to requests if aiohttp fails
        try:
            print("Falling back to requests library")
            response = requests.get(hiscores_url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                print(f"Successfully fetched hiscores data with {len(data)} entries")
                return data
            else:
                print(f"Fallback request failed: {response.status_code}")
                return None
        except Exception as e2:
            print(f"Fallback request also failed: {e2}")
            return None

def format_total_level_message(clan_data: List[Dict]) -> str:
    """Format the top 10 players by total level message"""
    if not clan_data:
        return "**Top 10 by Total Level:**\n*No data available*"

    # Sort players by total level (overall.level) and then by experience (overall.experience) if levels are the same
    def get_total_level_and_exp(player: Dict) -> Tuple[int, int]:
        if 'latestSnapshot' in player and player['latestSnapshot']:
            data = player['latestSnapshot'].get('data', {})
            skills = data.get('skills', {})
            overall = skills.get('overall', {})
            level = overall.get('level', 0)
            exp = overall.get('experience', 0)
            return (level, exp)
        return (0, 0)

    sorted_players = sorted(
        clan_data, 
        key=get_total_level_and_exp,
        reverse=True
    )

    top_players = sorted_players[:10]

    message = "**Top 10 by Total Level:**\n"
    for player in top_players:
        username = player.get('username', 'Unknown')
        display_name = player.get('displayName', username)

        # Get total level and exp
        level, exp = get_total_level_and_exp(player)

        message += f"- {display_name} | Level: {level} | XP: {exp:,}\n"

    return message

def format_skills_message(clan_data: List[Dict]) -> str:
    """Format the top 10 players per skill message"""
    if not clan_data:
        return "**Top 10 per Skill:**\n*No data available*"

    message = "**Top 10 per Skill:**\n"

    for skill in SKILLS:
        message += f"\n**{skill.title()}:**\n"

        # Define a function to get skill level and experience
        def get_skill_data(player: Dict) -> Tuple[int, int]:
            if 'latestSnapshot' in player and player['latestSnapshot']:
                data = player['latestSnapshot'].get('data', {})
                skills = data.get('skills', {})
                skill_data = skills.get(skill, {})
                level = skill_data.get('level', 0)
                exp = skill_data.get('experience', 0)
                return (level, exp)
            return (0, 0)

        # Sort players by skill level, then by experience
        sorted_players = sorted(
            clan_data,
            key=lambda p: (get_skill_data(p)[0], get_skill_data(p)[1]),
            reverse=True
        )

        top_players = sorted_players[:10]
        player_added = False

        for player in top_players:
            username = player.get('username', 'Unknown')
            display_name = player.get('displayName', username)
            level, exp = get_skill_data(player)

            if level > 0:
                message += f"- {display_name} | Level: {level} | XP: {exp:,}\n"
                player_added = True

        if not player_added:
            message += "*No data available*\n"

    return message

def format_bosses_message(clan_data: List[Dict]) -> str:
    """Format the top 10 players per boss message"""
    if not clan_data:
        return "**Top 10 per Boss KC:**\n*No data available*"

    # Collect all boss names from all players
    boss_names = set()
    for player in clan_data:
        if 'latestSnapshot' in player and player['latestSnapshot']:
            data = player['latestSnapshot'].get('data', {})
            bosses = data.get('bosses', {})
            for boss_name in bosses.keys():
                boss_names.add(boss_name)

    message = "**Top 10 per Boss KC:**\n"

    if not boss_names:
        message += "\n*No boss data available*"
        return message

    # Sort boss names alphabetically
    bosses_list = sorted(boss_names)

    for boss_name in bosses_list:
        message += f"\n**{boss_name.replace('_', ' ').title()}:**\n"

        # Define a function to get boss KC
        def get_boss_kc(player: Dict) -> int:
            if 'latestSnapshot' in player and player['latestSnapshot']:
                data = player['latestSnapshot'].get('data', {})
                bosses = data.get('bosses', {})
                return bosses.get(boss_name, 0)
            return 0

        # Sort players by boss KC
        sorted_players = sorted(
            clan_data,
            key=get_boss_kc,
            reverse=True
        )

        top_players = sorted_players[:10]
        player_added = False

        for player in top_players:
            username = player.get('username', 'Unknown')
            display_name = player.get('displayName', username)
            kc = get_boss_kc(player)

            if kc > 0:
                message += f"- {display_name} | KC: {kc}\n"
                player_added = True

        if not player_added:
            message += "*No data available*\n"

    return message

@bot.tree.command(name="clanhighscores", description="Show clan highscores")
async def clanhighscores(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        clan_data = await fetch_clan_data()
        if not clan_data:
            await interaction.followup.send("Error fetching clan data. Please try again later.")
            return

        # Format messages
        total_message = format_total_level_message(clan_data)
        skills_message = format_skills_message(clan_data)
        bosses_message = format_bosses_message(clan_data)

        # Send or update messages
        channel = interaction.channel
        if highscore_messages["total"] is None:
            highscore_messages["total"] = await channel.send(total_message)
            highscore_messages["skills"] = await channel.send(skills_message)
            highscore_messages["bosses"] = await channel.send(bosses_message)
        else:
            await highscore_messages["total"].edit(content=total_message)
            await highscore_messages["skills"].edit(content=skills_message)
            await highscore_messages["bosses"].edit(content=bosses_message)

        await interaction.followup.send("Highscores updated!")
    except Exception as e:
        print(f"Error in clanhighscores command: {e}")
        await interaction.followup.send("An error occurred while updating highscores.")

@tasks.loop(hours=24)
async def update_highscores_task():
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            print("Channel not found.")
            return

        clan_data = await fetch_clan_data()
        if not clan_data:
            print("Error fetching clan data in background task.")
            return

        # Format messages
        total_message = format_total_level_message(clan_data)
        skills_message = format_skills_message(clan_data)
        bosses_message = format_bosses_message(clan_data)

        # Send or update messages
        if highscore_messages["total"] is None:
            highscore_messages["total"] = await channel.send(total_message)
            highscore_messages["skills"] = await channel.send(skills_message)
            highscore_messages["bosses"] = await channel.send(bosses_message)
        else:
            try:
                await highscore_messages["total"].edit(content=total_message)
                await highscore_messages["skills"].edit(content=skills_message)
                await highscore_messages["bosses"].edit(content=bosses_message)
            except Exception as e:
                print(f"Error editing messages: {e}")
                # If editing fails, try sending new messages
                highscore_messages["total"] = await channel.send(total_message)
                highscore_messages["skills"] = await channel.send(skills_message)
                highscore_messages["bosses"] = await channel.send(bosses_message)
    except Exception as e:
        print(f"Error in update task: {e}")

@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! Bot latency: {round(bot.latency * 1000)}ms')

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    try:
        await bot.tree.sync()
        print("Successfully synced application commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    update_highscores_task.start()
    print("Bot is ready! Try !ping to test or /clanhighscores to view OSRS clan highscores")

if __name__ == "__main__":
    if not TOKEN:
        print("Please set the DISCORD_TOKEN environment variable")
        exit(1)
    if CHANNEL_ID == 0:
        print("Please set the CHANNEL_ID environment variable")
        exit(1)
    bot.run(TOKEN)