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
    """Fetch clan hiscores data from Wise Old Man API with rate limit handling"""
    print(f"Fetching clan data for clan ID: {CLAN_ID}")

    headers = {
        'Accept': 'application/json',
        'User-Agent': 'OSRS-Clan-Discord-Bot/1.0'
    }

    try:
        async with aiohttp.ClientSession() as session:
            # First try to get hiscores data directly (most efficient)
            hiscores_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/hiscores?metric=overall&limit=100"
            try:
                async with session.get(hiscores_url, headers=headers) as hiscores_response:
                    if hiscores_response.status == 200:
                        hiscores_data = await hiscores_response.json()

                        # Extract player data from hiscores
                        player_data = []
                        player_ids = []
                        for entry in hiscores_data:
                            if 'player' in entry:
                                player_data.append(entry['player'])
                                # Track player IDs for deduplication later
                                if 'id' in entry['player']:
                                    player_ids.append(entry['player']['id'])

                        if len(player_data) > 0:
                            print(f"Successfully fetched hiscores data for {len(player_data)} players")

                            # Now fetch detailed data for top 20 players
                            detailed_players = []
                            top_players = sorted(player_data, key=lambda p: p.get('exp', 0) if isinstance(p.get('exp'), (int, float)) else 0, reverse=True)[:20]

                            for player in top_players:
                                username = player.get('username')
                                if not username:
                                    continue

                                # Add slight delay to avoid rate limiting
                                await asyncio.sleep(0.2)
                                player_details_url = f"{WISE_OLD_MAN_BASE_URL}/players/{username}"

                                try:
                                    async with session.get(player_details_url, headers=headers) as player_response:
                                        if player_response.status == 200:
                                            player_details = await player_response.json()
                                            if player_details:
                                                detailed_players.append(player_details)
                                except Exception as player_error:
                                    print(f"Error fetching detailed data for {username}: {player_error}")

                            # Add boss hiscores data separately to ensure we get boss KC
                            for boss in ["zulrah", "vorkath", "chambers_of_xeric", "tombs_of_amascut"]:
                                boss_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/hiscores?metric={boss}&limit=10"
                                try:
                                    async with session.get(boss_url, headers=headers) as boss_response:
                                        if boss_response.status == 200:
                                            boss_data = await boss_response.json()
                                            for entry in boss_data:
                                                if 'player' in entry and entry['player'].get('id') not in player_ids:
                                                    player_data.append(entry['player'])
                                                    player_ids.append(entry['player'].get('id'))
                                except Exception as boss_error:
                                    print(f"Error fetching {boss} data: {boss_error}")

                            # Combine detailed players with the regular data
                            combined_data = []

                            # First add all detailed players
                            for detailed_player in detailed_players:
                                player_id = detailed_player.get('id')
                                if player_id:
                                    combined_data.append(detailed_player)
                                    player_ids.remove(player_id) if player_id in player_ids else None

                            # Then add remaining players that weren't part of the detailed fetch
                            for player in player_data:
                                player_id = player.get('id')
                                if player_id in player_ids:
                                    combined_data.append(player)

                            return combined_data
                    else:
                        print(f"Failed to fetch hiscores data: {hiscores_response.status}")
            except Exception as hiscores_error:
                print(f"Error fetching hiscores: {hiscores_error}")

            # Fallback to getting group details and then individual player data
            group_details_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}"
            async with session.get(group_details_url, headers=headers) as group_response:
                if group_response.status != 200:
                    print(f"Failed to fetch group details: {group_response.status}")
                    print(await group_response.text())
                    # Last resort, try to get top players for each skill
                    try:
                        player_data = []
                        # Try to get top players for a few important skills
                        for skill in ["overall", "attack", "strength", "defence", "hitpoints"]:
                            skill_url = f"{WISE_OLD_MAN_BASE_URL}/hiscores?metric={skill}&limit=20&type=regular"
                            async with session.get(skill_url, headers=headers) as skill_response:
                                if skill_response.status == 200:
                                    skill_data = await skill_response.json()
                                    # Get players
                                    for entry in skill_data:
                                        if 'player' in entry:
                                            # Check if we already have this player
                                            if not any(p.get('id') == entry['player'].get('id') for p in player_data):
                                                player_data.append(entry['player'])

                        if len(player_data) > 0:
                            print(f"Successfully fetched {len(player_data)} players from general hiscores")
                            return player_data
                        return None
                    except Exception as e:
                        print(f"Failed to fetch general hiscores: {e}")
                        return None

                group_data = await group_response.json()

                if 'memberships' not in group_data:
                    print("No memberships found in group data")
                    return None

                # Get players directly from memberships
                player_data = []
                for membership in group_data.get('memberships', []):
                    if 'player' in membership and membership['player']:
                        player_data.append(membership['player'])

                if len(player_data) > 0:
                    print(f"Retrieved {len(player_data)} players from group memberships")

                    # Try to get more detailed data for the top 10 players
                    import asyncio
                    detailed_players = []

                    # Only fetch the first 10 players to avoid rate limits
                    top_players = sorted(player_data, key=lambda p: p.get('exp', 0), reverse=True)[:10]
                    for player in top_players:
                        username = player.get('username')
                        if not username:
                            continue

                        # Add delay between requests to avoid rate limiting
                        await asyncio.sleep(0.3)

                        player_url = f"{WISE_OLD_MAN_BASE_URL}/players/{username}"
                        try:
                            async with session.get(player_url, headers=headers) as player_response:
                                if player_response.status == 200:
                                    detailed_player = await player_response.json()
                                    detailed_players.append(detailed_player)
                                else:
                                    # If we can't get detailed data, use what we have
                                    detailed_players.append(player)
                        except Exception:
                            # If error, just use what we have
                            detailed_players.append(player)

                    # Combine detailed players with the rest
                    for detailed_player in detailed_players:
                        # Remove original player
                        player_data = [p for p in player_data if p.get('id') != detailed_player.get('id')]
                        # Add detailed player
                        player_data.append(detailed_player)

                    return player_data

                # If we couldn't get any players from memberships, try individual player fetching
                member_usernames = [membership.get('player', {}).get('username') 
                                  for membership in group_data.get('memberships', [])
                                  if membership.get('player', {}).get('username')]

                print(f"Found {len(member_usernames)} members in the clan")

                import asyncio
                # Only fetch the first 20 players to avoid rate limits
                limited_members = member_usernames[:20]
                player_data = []

                for username in limited_members:
                    # Add delay between requests to avoid rate limiting
                    await asyncio.sleep(0.3)

                    player_url = f"{WISE_OLD_MAN_BASE_URL}/players/{username}"
                    try:
                        async with session.get(player_url, headers=headers) as player_response:
                            if player_response.status == 200:
                                player = await player_response.json()
                                player_data.append(player)
                            else:
                                print(f"Failed to fetch data for player {username}: {player_response.status}")
                    except Exception as player_error:
                        print(f"Error fetching player {username}: {player_error}")

                print(f"Successfully fetched data for {len(player_data)} players")
                return player_data if player_data else None

    except Exception as e:
        print(f"Error fetching clan data: {e}")

        # Fallback to requests if aiohttp fails
        try:
            print("Falling back to requests library")
            # Try to get hiscores directly first
            hiscores_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/hiscores?metric=overall&limit=100"
            hiscores_response = requests.get(hiscores_url, headers=headers, timeout=15)

            if hiscores_response.status_code == 200:
                hiscores_data = hiscores_response.json()
                player_data = []

                # Extract player data from hiscores
                for entry in hiscores_data:
                    if 'player' in entry:
                        player_data.append(entry['player'])

                if len(player_data) > 0:
                    print(f"Fallback: Successfully fetched hiscores data for {len(player_data)} players")
                    return player_data

            # If direct hiscores didn't work, try the group members approach
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

            # Fetch a limited number of player details to avoid rate limits
            player_data = []
            import time

            # Only fetch the first 30 players to avoid rate limits
            limited_members = member_usernames[:30]
            for username in limited_members:
                # Add delay between requests
                time.sleep(0.5)

                player_url = f"{WISE_OLD_MAN_BASE_URL}/players/{username}"
                player_response = requests.get(player_url, headers=headers, timeout=15)
                if player_response.status_code == 200:
                    player = player_response.json()
                    player_data.append(player)
                elif player_response.status_code == 429:  # Rate limited
                    # If we're rate limited, just use what we have
                    break

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
        # Also try direct access to stats for hiscores entries
        elif 'stats' in player:
            stats = player.get('stats', {})
            if 'overall' in stats:
                overall = stats.get('overall', {})
                level = overall.get('level', 0)
                exp = overall.get('experience', 0)
                return (level, exp)
        # Debug what kind of data structure we're receiving
        print(f"Player data structure example: {str(player)[:300]}...")
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
        super().__init__(timeout=None)  # No timeout for persistent view
        self.bot = bot_instance
        self.custom_id = "refresh_highscores"  # Adding custom ID for persistence

    @discord.ui.button(label="Refresh Highscores", style=discord.ButtonStyle.primary, emoji="🔄", custom_id="refresh_highscores_button")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Defer the response to buy time for processing, specify thinking is true
            await interaction.response.defer(ephemeral=True, thinking=True)

            print(f"Refresh button clicked by {interaction.user}")

            try:
                clan_data = await fetch_clan_data()

                if not clan_data:
                    try:
                        await interaction.followup.send("Error fetching clan data. Please try again later.", ephemeral=True)
                    except discord.NotFound:
                        # If interaction expires, try to message the channel
                        await interaction.channel.send("Error fetching clan data. Please try again later.")
                    return

                # Create a new embed with updated data
                embed = create_highscores_embed(clan_data)

                # Create a new view for the updated message
                view = RefreshButton(self.bot)

                try:
                    # Get the original message via the message that triggered this interaction
                    message = interaction.message
                    if message:
                        await message.edit(embed=embed, view=view)
                        highscore_messages["main"] = message

                        try:
                            await interaction.followup.send("✅ Highscores updated successfully!", ephemeral=True)
                        except discord.NotFound:
                            # If interaction expires, try with a new message
                            await interaction.channel.send("✅ Highscores updated successfully!")
                    else:
                        # Fallback if we can't get the interaction message
                        channel = interaction.channel
                        new_message = await channel.send(embed=embed, view=view)
                        highscore_messages["main"] = new_message

                        try:
                            await interaction.followup.send("✅ Created new highscores message!", ephemeral=True)
                        except discord.NotFound:
                            pass  # Already sent the new message to the channel
                except Exception as edit_error:
                    print(f"Error updating message: {edit_error}")
                    # Send a new message if editing fails
                    channel = interaction.channel
                    new_message = await channel.send("⚠️ Could not update existing message. Here's the latest data:", embed=embed, view=view)
                    highscore_messages["main"] = new_message
            except Exception as data_error:
                print(f"Error fetching or processing data: {data_error}")
                try:
                    await interaction.followup.send(f"An error occurred: {str(data_error)}", ephemeral=True)
                except discord.NotFound:
                    # If interaction expired, try channel
                    await interaction.channel.send(f"An error occurred during refresh: {str(data_error)}")
        except Exception as e:
            print(f"Error in refresh button handler: {e}")
            try:
                channel = interaction.channel
                await channel.send(f"An error occurred during refresh: {str(e)}")
            except:
                pass  # Last resort failed, nothing more we can do

def create_highscores_embed(clan_data):
    """Create a Discord embed with the clan highscores"""
    embed = discord.Embed(
        title="OSRS Defence Clan Highscores",
        description="Top players in OSRS Defence clan",
        color=discord.Color.blue()
    )

    # Add top 10 by total level
    def get_total_level_and_exp(player: Dict) -> Tuple[int, int]:
        try:
            # Try to get the player's experience from different sources
            # First check latestSnapshot
            if player.get('latestSnapshot') and player['latestSnapshot'].get('data'):
                data = player['latestSnapshot'].get('data', {})
                skills = data.get('skills', {})
                if skills and 'overall' in skills:
                    overall = skills.get('overall', {})
                    level = overall.get('level', 0)
                    exp = overall.get('experience', 0)
                    if level > 0 or exp > 0:
                        return (level, exp)

            # Check stats directly 
            if player.get('stats') and 'overall' in player.get('stats', {}):
                overall = player['stats'].get('overall', {})
                level = overall.get('level', 0)
                exp = overall.get('experience', 0)
                if level > 0 or exp > 0:
                    return (level, exp)

            # Check if exp is directly on the player object
            if isinstance(player.get('exp'), (int, float)) and player['exp'] > 0:
                exp = player['exp']
                # Estimate level based on exp
                level = min(2277, max(3, int(exp / 100000))) 
                return (level, exp)

            # If player has neither stats nor latestSnapshot but has total level
            if isinstance(player.get('ehp'), (int, float)) and player['ehp'] > 0:
                # Estimate from EHP
                return (int(player['ehp'] * 10), int(player['ehp'] * 100000))

        except Exception as e:
            print(f"Error extracting data for {player.get('username', 'Unknown')}: {e}")

        return (0, 0)

    # Sort players by total level and exp
    sorted_players = sorted(
        clan_data, 
        key=get_total_level_and_exp,
        reverse=True
    )

    # Filter out players with 0 level/exp
    valid_players = [p for p in sorted_players if get_total_level_and_exp(p)[0] > 0]
    top_players = valid_players[:10]

    # Add top 10 by total level field
    top_level_text = ""
    for index, player in enumerate(top_players, 1):
        username = player.get('username', 'Unknown')
        display_name = player.get('displayName', username)
        level, exp = get_total_level_and_exp(player)
        top_level_text += f"**{index}.** {display_name} | Lvl: {level} | XP: {exp:,}\n"

    embed.add_field(name="Top 10 by Total Level", value=top_level_text or "No data available", inline=False)

    # Add top skills section - include primary combat skills
    key_skills = ["attack", "defence", "strength", "hitpoints", "ranged", "prayer", "magic"]

    for skill in key_skills:
        # Define a function to get skill level and experience
        def get_skill_data(player: Dict) -> Tuple[int, int]:
            try:
                # Try to get from latestSnapshot first
                if player.get('latestSnapshot') and player['latestSnapshot'].get('data'):
                    data = player['latestSnapshot'].get('data', {})
                    skills = data.get('skills', {})
                    if skills and skill in skills:
                        skill_data = skills.get(skill, {})
                        level = skill_data.get('level', 0)
                        exp = skill_data.get('experience', 0)
                        if level > 0 or exp > 0:
                            return (level, exp)

                # Try to get from stats directly
                if player.get('stats') and skill in player.get('stats', {}):
                    skill_data = player['stats'].get(skill, {})
                    level = skill_data.get('level', 0)
                    exp = skill_data.get('experience', 0)
                    if level > 0 or exp > 0:
                        return (level, exp)

                # If getting from direct fields didn't work, try to estimate from the player's other fields
                if isinstance(player.get('exp'), (int, float)) and player['exp'] > 0:
                    total_exp = player['exp']
                    # Different estimation strategies for different skills
                    if skill in ["attack", "strength", "defence", "hitpoints"]:
                        est_level = min(99, max(1, int((total_exp / 1000000) * 3)))
                        est_exp = int(total_exp / 10)
                        return (est_level, est_exp)
                    elif skill in ["ranged", "prayer", "magic"]:
                        est_level = min(99, max(1, int((total_exp / 1200000) * 3)))
                        est_exp = int(total_exp / 12)
                        return (est_level, est_exp)

            except Exception as e:
                print(f"Error getting {skill} data for {player.get('username', 'Unknown')}: {e}")
            return (0, 0)

        # Get players with non-zero skill data
        valid_skill_players = [p for p in clan_data if get_skill_data(p)[0] > 0]

        # Sort players by skill level, then by experience
        skill_sorted = sorted(
            valid_skill_players,
            key=lambda p: (get_skill_data(p)[0], get_skill_data(p)[1]),
            reverse=True
        )[:5]  # Top 5 to keep embed manageable

        skill_text = ""
        for index, player in enumerate(skill_sorted, 1):
            display_name = player.get('displayName', player.get('username', 'Unknown'))
            level, exp = get_skill_data(player)
            skill_text += f"{index}. {display_name} ({level})\n"

        if skill_text:
            embed.add_field(name=skill.title(), value=skill_text, inline=True)
        else:
            embed.add_field(name=skill.title(), value="No data", inline=True)

    # Add a field for boss KC
    # Most common bosses
    popular_bosses = ["zulrah", "vorkath", "chambers_of_xeric", "tombs_of_amascut", "the_gauntlet", "theatre_of_blood"]

    for boss_name in popular_bosses:
        boss_text = ""

        def get_boss_kc(player: Dict) -> int:
            try:
                if player.get('latestSnapshot') and player['latestSnapshot'].get('data') and player['latestSnapshot']['data'].get('bosses'):
                    bosses = player['latestSnapshot']['data'].get('bosses', {})
                    if boss_name in bosses:
                        kc = bosses[boss_name]
                        if isinstance(kc, (int, float)) and kc > 0:
                            return kc
                if player.get('stats') and player.get('stats').get('bosses') and boss_name in player.get('stats').get('bosses', {}):
                    kc = player.get('stats').get('bosses', {}).get(boss_name, 0)
                    if isinstance(kc, (int, float)) and kc > 0:
                        return kc
            except Exception as e:
                print(f"Error getting KC for {boss_name} from {player.get('username', 'Unknown')}: {e}")
            return 0

        boss_players = [p for p in clan_data if get_boss_kc(p) > 0]
        sorted_boss_players = sorted(boss_players, key=get_boss_kc, reverse=True)[:3]

        for idx, player in enumerate(sorted_boss_players, 1):
            kc = get_boss_kc(player)
            if kc > 0:
                display_name = player.get('displayName', player.get('username', 'Unknown'))
                boss_text += f"{idx}. {display_name}: {kc} KC\n"

        if boss_text:
            embed.add_field(
                name=boss_name.replace('_', ' ').title(), 
                value=boss_text, 
                inline=True
            )

    # Add timestamp and footer
    embed.timestamp = discord.utils.utcnow()
    embed.set_footer(text="Last updated")

    return embed

@bot.tree.command(name="clanhighscores", description="Show clan highscores")
async def clanhighscores(interaction: discord.Interaction):
    try:
        # Defer the response to buy time for processing
        await interaction.response.defer(ephemeral=True)

        # Check permissions first
        channel = interaction.channel
        bot_member = channel.guild.get_member(bot.user.id)
        permissions = channel.permissions_for(bot_member)
        
        if not permissions.send_messages or not permissions.embed_links:
            await interaction.followup.send(
                "❌ I don't have enough permissions in this channel. Please make sure I have 'Send Messages' and 'Embed Links' permissions.",
                ephemeral=True
            )
            print(f"Missing required permissions in channel {channel.id}")
            print(f"Bot needs: Send Messages: {permissions.send_messages}, Embed Links: {permissions.embed_links}")
            return

        clan_data = await fetch_clan_data()
        if not clan_data:
            await interaction.followup.send("Error fetching clan data. Please try again later.", ephemeral=True)
            return

        # Create an embed with the data
        embed = create_highscores_embed(clan_data)

        # Create the view with refresh button
        view = RefreshButton(bot)

        # Send the embed with the button to the channel
        try:
            message = await channel.send(embed=embed, view=view)
            highscore_messages["main"] = message

            # Send confirmation to the user
            await interaction.followup.send("✅ Highscores posted to channel!", ephemeral=True)
        except discord.Forbidden as e:
            await interaction.followup.send(
                f"❌ I don't have permission to send messages in this channel. Error: {str(e)}",
                ephemeral=True
            )
            print(f"Permission denied when sending message to channel {channel.id}: {e}")
        except Exception as e:
            await interaction.followup.send(f"❌ Error sending message: {str(e)}", ephemeral=True)
            print(f"Error sending message to channel {channel.id}: {e}")

    except Exception as e:
        print(f"Error in clanhighscores command: {e}")
        # Try to handle the case where the initial defer failed
        try:
            await interaction.followup.send(f"An error occurred while updating highscores: {str(e)}", ephemeral=True)
        except:
            # If followup fails, try to send to the channel directly
            try:
                channel = interaction.channel
                if channel and channel.permissions_for(channel.guild.me).send_messages:
                    await channel.send(f"Error processing highscores command: {str(e)}")
            except Exception as channel_error:
                print(f"Failed to send error message to channel: {channel_error}")

# Add a regular command for highscores as well
@bot.command()
async def highscores(ctx):
    """Show clan highscores"""
    async with ctx.typing():
        try:
            clan_data = await fetch_clan_data()
            if not clan_data:
                await ctx.send("Error fetching clan data. Please try again later.")
                return

            # Create an embed with the data
            embed =create_highscores_embed(clan_data)

            # Create the view with refresh button
            view = RefreshButton(bot)

            # Send the embed with the button
            message = await ctx.send(embed=embed, view=view)
            highscore_messages["main"] = message

        except Exception as e:
            print(f"Error in highscores command: {e}")
            await ctx.send(f"An error occurred while updating highscores: {str(e)}")

@tasks.loop(hours=24)
async def update_highscores_task():
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            print("Channel not found.")
            return

        # Check permissions first
        bot_member = channel.guild.get_member(bot.user.id)
        permissions = channel.permissions_for(bot_member)
        
        if not permissions.send_messages or not permissions.embed_links:
            print(f"Missing required permissions in channel {CHANNEL_ID}.")
            print(f"Bot needs: Send Messages: {permissions.send_messages}, Embed Links: {permissions.embed_links}")
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
            try:
                highscore_messages["main"] = await channel.send(embed=embed, view=view)
                print(f"Successfully sent new highscores message to channel {CHANNEL_ID}")
            except discord.Forbidden:
                print(f"403 Forbidden: Bot lacks permission to send messages in channel {CHANNEL_ID}")
            except Exception as e:
                print(f"Error sending message: {e}")
        else:
            try:
                await highscore_messages["main"].edit(embed=embed, view=view)
                print(f"Successfully updated highscores message in channel {CHANNEL_ID}")
            except discord.Forbidden:
                print(f"403 Forbidden: Bot lacks permission to edit messages in channel {CHANNEL_ID}")
                # Try to send a new message if editing fails due to permissions
                try:
                    highscore_messages["main"] = await channel.send(embed=embed, view=view)
                    print(f"Sent a new message instead of editing in channel {CHANNEL_ID}")
                except discord.Forbidden:
                    print(f"403 Forbidden: Bot lacks permission to send messages in channel {CHANNEL_ID}")
                except Exception as e:
                    print(f"Error sending message: {e}")
            except Exception as e:
                print(f"Error editing message: {e}")
                # If editing fails, try sending a new message
                try:
                    highscore_messages["main"] = await channel.send(embed=embed, view=view)
                except Exception as e2:
                    print(f"Also failed to send a new message: {e2}")
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

        # Register the persistent view for the refresh button
        bot.add_view(RefreshButton(bot))
        print("Registered persistent view for refresh button")

        # Try to retrieve existing highscores messages and add views to them
        if CHANNEL_ID:
            try:
                channel = bot.get_channel(CHANNEL_ID)
                if channel:
                    # Try to get the last 10 messages to find highscores messages
                    async for message in channel.history(limit=10):
                        if message.author == bot.user and message.embeds and len(message.embeds) > 0:
                            embed = message.embeds[0]
                            if embed.title and "OSRS Defence Clan Highscores" in embed.title:
                                # This is a highscores message, add the view to it
                                await message.edit(view=RefreshButton(bot))
                                highscore_messages["main"] = message
                                print(f"Restored view for existing highscores message (ID: {message.id})")
                                break
            except Exception as hist_error:
                print(f"Error retrieving channel history: {hist_error}")

        # Start the automatic update task
        if not update_highscores_task.is_running():
            update_highscores_task.start()
            print("Started highscores update task")
    except Exception as e:
        print(f"Error during startup: {e}")

    print("Bot is ready! Try !ping to test or /clanhighscores to view OSRS clan highscores")

if __name__ == "__main__":
    if not TOKEN:
        print("Please set the DISCORD_TOKEN environment variable")
        exit(1)
    if CHANNEL_ID == 0:
        print("Please set the CHANNEL_ID environment variable")
        exit(1)
    bot.run(TOKEN)