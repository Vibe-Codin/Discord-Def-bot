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

# Global dictionary to store the message object for updating
highscore_messages = {
    "main": None
}

async def fetch_clan_data():
    """Fetch clan hiscores data from Wise Old Man API"""
    print(f"Fetching clan data for clan ID: {CLAN_ID}")

    headers = {
        'Accept': 'application/json',
        'User-Agent': 'OSRS-Clan-Discord-Bot/1.0'
    }

    # Main endpoint to get hiscores data - adding 'overall' as the default metric
    hiscores_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/hiscores?metric=overall"

    try:
        print(f"Requesting hiscores from: {hiscores_url}")
        async with aiohttp.ClientSession() as session:
            # First get the members list from the group details
            group_details_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}"
            async with session.get(group_details_url, headers=headers) as group_response:
                if group_response.status != 200:
                    print(f"Failed to fetch group details: {group_response.status}")
                    print(await group_response.text())
                    return None

                group_data = await group_response.json()

                if 'memberships' not in group_data:
                    print("No memberships found in group data")
                    return None

                # Extract member usernames 
                member_usernames = [membership.get('player', {}).get('username') 
                                    for membership in group_data.get('memberships', [])
                                    if membership.get('player', {}).get('username')]

                print(f"Found {len(member_usernames)} members in the clan")

                # Fetch player details for each member
                player_data = []
                for username in member_usernames:
                    player_url = f"{WISE_OLD_MAN_BASE_URL}/players/{username}"
                    async with session.get(player_url, headers=headers) as player_response:
                        if player_response.status == 200:
                            player = await player_response.json()
                            player_data.append(player)
                        else:
                            print(f"Failed to fetch data for player {username}: {player_response.status}")

                print(f"Successfully fetched data for {len(player_data)} players")
                if len(player_data) > 0:
                    print(f"Sample player data: {json.dumps(player_data[0], indent=2)[:200]}...")
                return player_data
    except Exception as e:
        print(f"Error fetching clan data: {e}")

        # Fallback to requests if aiohttp fails
        try:
            print("Falling back to requests library")
            group_details_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}"
            group_response = requests.get(group_details_url, headers=headers, timeout=15)

            if group_response.status_code != 200:
                print(f"Fallback: Failed to fetch group details: {group_response.status_code}")
                return None

            group_data = group_response.json()

            if 'memberships' not in group_data:
                print("Fallback: No memberships found in group data")
                return None

            # Extract member usernames
            member_usernames = [membership.get('player', {}).get('username') 
                                for membership in group_data.get('memberships', [])
                                if membership.get('player', {}).get('username')]

            # Fetch player details for each member
            player_data = []
            for username in member_usernames:
                player_url = f"{WISE_OLD_MAN_BASE_URL}/players/{username}"
                player_response = requests.get(player_url, headers=headers, timeout=15)
                if player_response.status_code == 200:
                    player = player_response.json()
                    player_data.append(player)

            print(f"Fallback: Successfully fetched data for {len(player_data)} players")
            return player_data

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

class RefreshButton(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot = bot_instance

    @discord.ui.button(label="Refresh Highscores", style=discord.ButtonStyle.primary, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            clan_data = await fetch_clan_data()
            if not clan_data:
                await interaction.followup.send("Error fetching clan data. Please try again later.", ephemeral=True)
                return

            embed = create_highscores_embed(clan_data)
            
            # Update the message with new data
            message = highscore_messages.get("main")
            if message:
                await message.edit(embed=embed, view=RefreshButton(self.bot))
                await interaction.followup.send("Highscores refreshed!", ephemeral=True)
            else:
                await interaction.followup.send("Couldn't find the highscores message to update.", ephemeral=True)
        except Exception as e:
            print(f"Error refreshing highscores: {e}")
            await interaction.followup.send(f"An error occurred while refreshing highscores: {str(e)}", ephemeral=True)

def create_highscores_embed(clan_data):
    """Create a Discord embed with the clan highscores"""
    embed = discord.Embed(
        title="OSRS Defence Clan Highscores",
        description="Top players in OSRS Defence clan",
        color=discord.Color.blue()
    )
    
    # Add top 10 by total level
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
    
    # Add top 10 by total level field
    top_level_text = ""
    for index, player in enumerate(top_players, 1):
        username = player.get('username', 'Unknown')
        display_name = player.get('displayName', username)
        level, exp = get_total_level_and_exp(player)
        top_level_text += f"**{index}.** {display_name} | Lvl: {level} | XP: {exp:,}\n"
    
    embed.add_field(name="Top 10 by Total Level", value=top_level_text or "No data available", inline=False)
    
    # Add timestamp and footer
    embed.timestamp = discord.utils.utcnow()
    embed.set_footer(text="Last updated")
    
    return embed

@bot.tree.command(name="clanhighscores", description="Show clan highscores")
async def clanhighscores(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        clan_data = await fetch_clan_data()
        if not clan_data:
            await interaction.followup.send("Error fetching clan data. Please try again later.")
            return

        # Create an embed with the data
        embed = create_highscores_embed(clan_data)
        
        # Create the view with refresh button
        view = RefreshButton(bot)
        
        # Send the embed with the button
        message = await interaction.followup.send(embed=embed, view=view)
        highscore_messages["main"] = message
        
    except Exception as e:
        print(f"Error in clanhighscores command: {e}")
        await interaction.followup.send(f"An error occurred while updating highscores: {str(e)}")

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

        # Create embed with current data
        embed = create_highscores_embed(clan_data)
        
        # Create the view with refresh button
        view = RefreshButton(bot)

        # Send or update message
        if highscore_messages["main"] is None:
            highscore_messages["main"] = await channel.send(embed=embed, view=view)
        else:
            try:
                await highscore_messages["main"].edit(embed=embed, view=view)
            except Exception as e:
                print(f"Error editing message: {e}")
                # If editing fails, try sending a new message
                highscore_messages["main"] = await channel.send(embed=embed, view=view)
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