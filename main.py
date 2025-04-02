import discord
from discord.ext import commands, tasks
import aiohttp
import os
import json

# Set your Wise Old Man clan ID, channel ID, and base URL
CLAN_ID = "2763"  # OSRS Defence clan ID
WISE_OLD_MAN_BASE_URL = "https://api.wiseoldman.net/v2"  # Using v2 API
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
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents, activity=discord.Game(name="!clanhighscores"))

# Global dictionary to store the message objects for updating
highscore_messages = {
    "msg1": None,
    "msg2": None,
    "msg3": None
}

async def fetch_clan_data():
    try:
        # Use headers according to API documentation
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'OSRS-Defence-Discord-Bot/1.0'
        }

        # According to the Wise Old Man API docs, use v2 endpoint
        group_endpoint = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}"
        group_members_endpoint = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/members"
        group_hiscores_endpoint = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/hiscores"
        group_details_endpoint = f"{WISE_OLD_MAN_BASE_URL}/groups/name/OSRS%20Defence"

        print(f"Fetching group details from: {group_endpoint}")
        print(f"Members endpoint: {group_members_endpoint}")
        print(f"Hiscores endpoint: {group_hiscores_endpoint}")

        import requests
        try:
            # First fetch group details to verify we have a valid group
            response = requests.get(group_endpoint, headers=headers, timeout=15)
            print(f"Group details response status: {response.status_code}")
            print(f"Group details response text: {response.text[:200]}...") #Added debug info

            if response.status_code == 200 and response.text.strip():
                try:
                    group_data = response.json()
                    print(f"Group data: {json.dumps(group_data, indent=2)[:200]}...")

                    # Extract members from group data if available
                    if 'memberships' in group_data and group_data['memberships']:
                        # Convert memberships to player list
                        player_data = []
                        for membership in group_data['memberships']:
                            if 'player' in membership and isinstance(membership['player'], dict):
                                player_data.append(membership['player'])

                        if player_data:
                            print(f"Extracted {len(player_data)} players from group data")
                            return player_data

                    # Get detailed player data from hiscores endpoint
                    hiscores_response = requests.get(group_hiscores_endpoint, headers=headers, timeout=15)
                    if hiscores_response.status_code == 200 and hiscores_response.text.strip():
                        try:
                            hiscores_data = hiscores_response.json()
                            print(f"Found hiscores data with {len(hiscores_data)} entries")
                            # Print sample data structure to help with debugging
                            if len(hiscores_data) > 0:
                                print(f"Sample hiscores data: {json.dumps(hiscores_data[0], indent=2)[:200]}...")
                            return hiscores_data
                        except json.JSONDecodeError as e:
                            print(f"Error decoding hiscores JSON: {e}")

                    # Try the members endpoint as fallback
                    members_response = requests.get(group_members_endpoint, headers=headers, timeout=15)
                    if members_response.status_code == 200 and members_response.text.strip():
                        try:
                            members_data = members_response.json()
                            # Extract player details from each membership
                            player_data = []
                            for membership in members_data:
                                if 'player' in membership and isinstance(membership['player'], dict):
                                    player_data.append(membership['player'])

                            print(f"Found {len(player_data)} player records from memberships")
                            return player_data
                        except json.JSONDecodeError as e:
                            print(f"Error decoding members JSON: {e}")
                    else:
                        print(f"Failed to get members: {members_response.status_code}")
                        print(f"Response text: {members_response.text[:100] if members_response.text else 'Empty'}")

                    # Try to extract member usernames directly from the group data
                    member_usernames = []
                    if 'memberCount' in group_data and group_data['memberCount'] > 0:
                        # If we have a clan chat name, add it as the first "member"
                        if 'clanChat' in group_data and group_data['clanChat']:
                            member_usernames.append(group_data['clanChat'].lower())

                        # Try to find members mentioned in description
                        if 'description' in group_data and group_data['description']:
                            # Split by common separators and add as potential members
                            words = group_data['description'].replace(',', ' ').replace('\n', ' ').split()
                            for word in words:
                                word = word.strip().lower()
                                if word and len(word) >= 3 and ' ' not in word and word not in member_usernames:
                                    member_usernames.append(word)

                    if member_usernames:
                        print(f"Extracted {len(member_usernames)} usernames from group data")
                        return member_usernames

                    # If we got this far but couldn't get detailed player data, return the group data
                    # The build_messages function will handle extracting members from it
                    return group_data

                except json.JSONDecodeError as e:
                    print(f"Error decoding group JSON: {e}")
            else:
                print(f"Failed to get group details: {response.status_code}")
                print(f"Response text: {response.text[:100] if response.text else 'Empty'}")

                # Try fetching by name as a fallback
                name_response = requests.get(group_details_endpoint, headers=headers, timeout=15)
                if name_response.status_code == 200 and name_response.text.strip():
                    try:
                        group_by_name = name_response.json()
                        print(f"Successfully fetched group by name")
                        return group_by_name
                    except json.JSONDecodeError as e:
                        print(f"Error decoding group by name JSON: {e}")
        except Exception as e:
            print(f"Error with direct request: {e}")

        # If direct request failed, try aiohttp as fallback
        # Using correct v2 API endpoints from documentation
        endpoints = [
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/hiscores",  # Group hiscores data
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}",  # Group details by ID
            f"{WISE_OLD_MAN_BASE_URL}/groups/name/OSRS%20Defence",  # Group details by name
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/gained",  # Group gained stats
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/records",  # Group records
            f"{WISE_OLD_MAN_BASE_URL}/competitions?groupId={CLAN_ID}",  # Group competitions
            f"{WISE_OLD_MAN_BASE_URL}/players/search?username=Defence" # Search for players
        ]

        async with aiohttp.ClientSession() as session:
            for url in endpoints:
                print(f"Trying endpoint: {url}")
                try:
                    async with session.get(url, headers=headers) as resp:
                        print(f"Response status: {resp.status}")
                        print(f"Response headers: {dict(resp.headers)}")

                        if resp.status == 404:
                            print(f"Endpoint not found: {url}")
                            continue

                        if resp.status != 200:
                            print(f"Error status: {resp.status}")
                            continue

                        text_data = await resp.text()
                        if not text_data:
                            print(f"Empty response from {url}")
                            continue

                        print(f"Got response from {url}: {text_data[:200]}")

                        try:
                            data = json.loads(text_data)
                            if data:
                                print(f"Successfully parsed data from {url}")
                                return data
                        except json.JSONDecodeError as je:
                            print(f"JSON parse error from {url}: {je}")
                            continue
                except Exception as e:
                    print(f"Error with endpoint {url}: {e}")
                    continue

        # Fallback to direct HTTP request if aiohttp fails
        import requests
        print("Trying direct HTTP request...")
        for url in endpoints:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                print(f"Direct request to {url}: status {response.status_code}")
                print(f"Direct request to {url}: text {response.text[:200]}...") #Added debug info

                if response.status_code == 200 and response.text:
                    try:
                        data = response.json()
                        if data:
                            print(f"Successfully parsed data from direct request to {url}")
                            return data
                    except json.JSONDecodeError:
                        print(f"JSON parse error from direct request to {url}")
            except Exception as e:
                print(f"Error with direct request to {url}: {e}")

        print("All attempts to fetch clan data failed")
        return None
    except Exception as e:
        print(f"Error fetching clan data: {str(e)}")
        return None

def build_messages(clan_data):
    if not clan_data:
        print("No clan data received")
        return None, None, None

    # Check if we received a group object instead of member list
    if isinstance(clan_data, dict) and 'memberships' in clan_data:
        print("Received group data, extracting members...")
        # Extract members from the group data
        if not clan_data.get('memberships', []):
            print("No memberships found in group data")
            return "No members found", "No skill data available", "No boss data available"
        players = []
        for membership in clan_data.get('memberships', []):
            if 'player' in membership and isinstance(membership['player'], dict):
                players.append(membership['player'])
        clan_data = players
        print(f"Extracted {len(players)} players from group data")
    # If we received a list but not of player objects, it might be just usernames
    elif isinstance(clan_data, list) and len(clan_data) > 0 and not isinstance(clan_data[0], dict):
        # Convert simple username list to dummy player objects
        players = []
        for username in clan_data:
            players.append({"username": username, "displayName": username})
        clan_data = players
        print(f"Converted {len(players)} usernames to dummy player objects")
    # If we received a dict with simple clan structure, create dummy players from member names
    elif isinstance(clan_data, dict) and 'name' in clan_data and not 'memberships' in clan_data:
        clan_name = clan_data.get('name', 'Unknown')
        clanChat = clan_data.get('clanChat', 'Unknown')
        players = [
            {"username": clan_name, "displayName": clan_name},
            {"username": clanChat, "displayName": clanChat}
        ]
        # Extract member usernames from description if available
        description = clan_data.get('description', '')
        if description:
            # Split description by commas, newlines or other separators
            possible_members = [m.strip() for m in description.replace(',', ' ').replace('\n', ' ').split()]
            for member in possible_members:
                if member and len(member) > 2 and member not in [p["username"] for p in players]:
                    players.append({"username": member, "displayName": member})
        clan_data = players
        print(f"Created {len(players)} dummy players from clan metadata")

    # Filter out users with offensive combat stats > 2
    filtered = []
    for player in clan_data:
        if not isinstance(player, dict):
            print(f"Invalid player data format: {player}")
            continue

        # Try to access player's latest snapshot data
        # In the API, player stats are in the 'latestSnapshot' field
        skills_data = {}
        if 'latestSnapshot' in player and player['latestSnapshot']:
            latest_snapshot = player['latestSnapshot']
            if isinstance(latest_snapshot, dict):
                if 'data' in latest_snapshot:
                    snapshot_data = latest_snapshot['data']
                    if isinstance(snapshot_data, dict):
                        if 'skills' in snapshot_data:
                            skills_data = snapshot_data['skills']
                        elif any(skill in snapshot_data for skill in skills_list):
                            skills_data = snapshot_data
                elif 'skills' in latest_snapshot:
                    skills_data = latest_snapshot['skills']

        valid = True
        for skill in offensive_skills:
            # Check if the skill data exists and get the level
            if skills_data and skill in skills_data:
                level = skills_data[skill].get('level', 0)
                if level > 2:
                    valid = False
                    break

        if valid:
            filtered.append(player)

    if not filtered:
        print("No players passed the filter")
        # Return placeholder messages so the bot doesn't fail
        return "No valid players found", "**Top 10 per Skill:**\n\n*No data available*", "**Top 10 per Boss KC:**\n\n*No data available*"

    # Helper function to get total level and experience
    def get_total_level_and_exp(player):
        # First try to get it from the player's exp field for experience
        total_exp = player.get('exp', 0)

        # For maxed players in OSRS, total level should be 2277 (99 in all 23 skills)
        max_total_level = 2277

        # Set a default level of 0 that we'll try to improve
        total_level = 0

        # Check if the player has latestSnapshot data
        if 'latestSnapshot' in player and player['latestSnapshot']:
            snapshot = player['latestSnapshot']

            # Check if this is a direct WOM API response format
            if isinstance(snapshot, dict):
                # Try to get exp from player top-level fields first (these are often more reliable)
                if total_exp == 0 and 'exp' in player:
                    total_exp = player['exp']

                # Try path: latestSnapshot.data.skills.overall
                if 'data' in snapshot and isinstance(snapshot['data'], dict):
                    data = snapshot['data']
                    if 'skills' in data and isinstance(data['skills'], dict):
                        skills_data = data['skills']

                        # Check for overall level directly
                        if 'overall' in skills_data and isinstance(skills_data['overall'], dict):
                            overall = skills_data['overall']
                            if 'level' in overall:
                                total_level = overall['level']
                            if total_exp == 0 and 'experience' in overall:
                                total_exp = overall['experience']

                        # If overall doesn't have level, try to sum individual skill levels
                        if total_level == 0:
                            skill_levels = []
                            for skill_name, skill_data in skills_data.items():
                                if skill_name != 'overall' and isinstance(skill_data, dict) and 'level' in skill_data:
                                    skill_levels.append(skill_data['level'])
                            if skill_levels:
                                total_level = sum(skill_levels)

                    # Try direct overall in data
                    elif 'overall' in data and isinstance(data['overall'], dict):
                        if total_level == 0 and 'level' in data['overall']:
                            total_level = data['overall']['level']
                        if total_exp == 0 and 'experience' in data['overall']:
                            total_exp = data['overall']['experience']

        # For high-level accounts with lots of XP, assume they are maxed if we couldn't get a level
        if total_level == 0 and total_exp > 200_000_000:  # Very high XP, likely maxed
            total_level = max_total_level
        elif total_level == 0 and total_exp > 13_034_431:  # XP for level 99 in all skills
            total_level = max_total_level
        elif total_level == 0 and total_exp > 0:
            # Estimate level based on experience (rough approximation)
            estimated_level = int(total_exp / 7000)
            total_level = min(estimated_level, max_total_level)  # Cap at max level

        return (total_level, total_exp)

    # First message: Top 10 players by Total Level
    sorted_total = sorted(
        filtered, 
        key=lambda x: get_total_level_and_exp(x), 
        reverse=True
    )
    top_total = sorted_total[:10]
    msg1 = "**Top 10 by Total Level:**\n"

    for player in top_total:
        username = player.get('username', 'Unknown')
        display_name = player.get('displayName', username)
        level, exp = get_total_level_and_exp(player)

        msg1 += f"- {display_name} | Level: {level} | XP: {exp:,}\n"

    if len(top_total) == 0:
        msg1 += "*No player data available*\n"

    # Second message: Top 10 per Skill
    msg2 = "**Top 10 per Skill:**\n"
    for skill in skills_list:
        msg2 += f"\n**{skill.title()}:**\n"

        # Define a function to safely extract skill experience and level for sorting
        def get_skill_data(player, skill_name):
            # Initialize with defaults
            exp = 0
            level = 0

            # First try top-level player fields (some API responses have this)
            if skill_name == 'overall':
                exp = player.get('exp', 0)
                level = player.get('level', 0)
                if exp > 0 or level > 0:
                    return (exp, level)

            # Try to extract from different snapshot structures
            if 'latestSnapshot' not in player or not player['latestSnapshot']:
                return (exp, level)

            snapshot = player['latestSnapshot']
            # Try different paths to find skill data
            if isinstance(snapshot, dict):
                # Path 1: latestSnapshot.data.skills.{skill}
                if 'data' in snapshot and isinstance(snapshot['data'], dict):
                    data = snapshot['data']
                    if 'skills' in data and isinstance(data['skills'], dict):
                        skills = data['skills']
                        if skill_name in skills and isinstance(skills[skill_name], dict):
                            skill_data = skills[skill_name]
                            exp = skill_data.get('experience', 0)
                            level = skill_data.get('level', 0)
                    # Path 2: latestSnapshot.data.{skill}
                    elif skill_name in data and isinstance(data[skill_name], dict):
                        skill_data = data[skill_name]
                        exp = skill_data.get('experience', 0)
                        level = skill_data.get('level', 0)
                # Path 3: latestSnapshot.skills.{skill}
                elif 'skills' in snapshot and isinstance(snapshot['skills'], dict):
                    skills = snapshot['skills']
                    if skill_name in skills and isinstance(skills[skill_name], dict):
                        skill_data = skills[skill_name]
                        exp = skill_data.get('experience', 0)
                        level = skill_data.get('level', 0)

            return (exp, level)

        # Sort players by skill experience using the helper function
        sorted_skill = sorted(
            filtered,
            key=lambda x: get_skill_data(x, skill)[0],  # Sort by experience
            reverse=True
        )

        top_skill = sorted_skill[:10]
        player_added = False

        for player in top_skill:
            username = player.get('username', 'Unknown')
            display_name = player.get('displayName', username)
            exp, level = get_skill_data(player, skill)

            # Add player to the message if they have any data for this skill
            if exp > 0 or level > 0:
                msg2 += f"- {display_name} | Level: {level} | XP: {exp:,}\n"
                player_added = True

        if not player_added:
            # Only for the first skill, add more detailed message about data being missing
            if skill == skills_list[0]:
                msg2 += "*No data available - The Wise Old Man API might not have this skill data*\n"
            else:
                msg2 += "*No data available*\n"

    # Third message: Top 10 per Boss KC
    # Get the list of all bosses from all players
    boss_set = set()
    for player in filtered:
        if 'latestSnapshot' in player and isinstance(player['latestSnapshot'], dict):
            if 'data' in player['latestSnapshot'] and isinstance(player['latestSnapshot']['data'], dict):
                if 'bosses' in player['latestSnapshot']['data'] and isinstance(player['latestSnapshot']['data']['bosses'], dict):
                    boss_data = player['latestSnapshot']['data']['bosses']
                    for boss in boss_data.keys():
                        boss_set.add(boss)

    bosses_list = sorted(boss_set)

    msg3 = "**Top 10 per Boss KC:**\n"
    if not bosses_list:
        msg3 += "\n*No boss data available*\n"
    else:
        for boss in bosses_list:
            msg3 += f"\n**{boss.title()}:**\n"

            # Sort players by boss KC
            sorted_boss = sorted(
                filtered,
                key=lambda x: (
                    x.get('latestSnapshot', {}).get('data', {}).get('bosses', {}).get(boss, 0)
                    if isinstance(x.get('latestSnapshot', {}).get('data', {}).get('bosses', {}), dict) else 0
                ),
                reverse=True
            )

            top_boss = sorted_boss[:10]
            player_added = False

            for player in top_boss:
                username = player.get('username', 'Unknown')
                kc = 0

                if 'latestSnapshot' in player and isinstance(player['latestSnapshot'], dict):
                    if 'data' in player['latestSnapshot'] and isinstance(player['latestSnapshot']['data'], dict):
                        if 'bosses' in player['latestSnapshot']['data'] and isinstance(player['latestSnapshot']['data']['bosses'], dict):
                            kc = player['latestSnapshot']['data']['bosses'].get(boss, 0)

                if kc > 0:
                    msg3 += f"- {username} | KC: {kc}\n"
                    player_added = True

            if not player_added:
                msg3 += "*No data available*\n"

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

@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! Bot latency: {round(bot.latency * 1000)}ms')

@bot.tree.command(name="testapi", description="Test the Wise Old Man API connection")
async def testapi(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        # Try multiple methods to get API data
        test_results = []

        # Try using the documented API endpoints more precisely
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'OSRS-Defence-Discord-Bot/1.0'
        }

        # Using documentation at https://docs.wiseoldman.net/
        endpoints = [
            # Group endpoints from docs
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}",
            f"{WISE_OLD_MAN_BASE_URL}/groups/name/OSRS%20Defence",

            # Group stats endpoints
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/gained",
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/records",

            # Competition endpoints
            f"{WISE_OLD_MAN_BASE_URL}/competitions?groupId={CLAN_ID}",

            # Player search - might help identify group members
            f"{WISE_OLD_MAN_BASE_URL}/players/search/names?username=Defence"
        ]

        async with aiohttp.ClientSession() as session:
            for url in endpoints:
                try:
                    async with session.get(url, headers=headers) as resp:
                        status = resp.status
                        resp_headers = dict(resp.headers)
                        text = await resp.text()
                        try:
                            if text and text.strip():
                                json_data = json.loads(text)
                                formatted_json = json.dumps(json_data, indent=2)[:500]  # Limit to 500 chars
                                test_results.append(f"URL: {url}\nStatus: {status}\nHeaders: {json.dumps(resp_headers, indent=2)}\nResponse: {formatted_json}...\n\n")
                            else:
                                test_results.append(f"URL: {url}\nStatus: {status}\nHeaders: {json.dumps(resp_headers, indent=2)}\nResponse: Empty response\n\n")
                        except json.JSONDecodeError:
                            test_results.append(f"URL: {url}\nStatus: {status}\nHeaders: {json.dumps(resp_headers, indent=2)}\nResponse: {text[:200]} (Not valid JSON)\n\n")
                except Exception as e:
                    test_results.append(f"URL: {url}\nError: {str(e)}\n\n")

        # Method 2: Try direct HTTP request with better response handling
        import requests
        for url in endpoints:
            try:
                response = requests.get(url, headers=headers, timeout=15)
                status_code = response.status_code
                test_results.append(f"Direct request to {url}\nStatus: {status_code}")

                # Try to parse JSON if the response has content
                if response.text and response.text.strip():
                    try:
                        json_data = response.json()
                        formatted_json = json.dumps(json_data, indent=2)[:500]
                        test_results.append(f"Response: {formatted_json}...\n\n")
                    except json.JSONDecodeError:
                        test_results.append(f"Response: {response.text[:200]} (Not valid JSON)\n\n")
                else:
                    test_results.append(f"Response: Empty content\n\n")
            except Exception as e:
                test_results.append(f"Direct request to {url}\nError: {str(e)}\n\n")

        # Send results
        debug_info = "API Test Results:\n\n" + "\n".join(test_results)
        if len(debug_info) > 2000:
            # Split long messages
            parts = [debug_info[i:i+1900] for i in range(0, len(debug_info), 1900)]
            for i, part in enumerate(parts):
                await interaction.followup.send(f"Part {i+1}/{len(parts)}:\n{part}")
        else:
            await interaction.followup.send(debug_info)
    except Exception as e:
        await interaction.followup.send(f"API Error: {str(e)}")

@bot.tree.command(name="testgroup", description="Test fetching the group details from Wise Old Man API")
async def testgroup(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        # Try to get the group details by ID
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'OSRS-Defence-Discord-Bot/1.0'
        }

        # Use the correct API endpoints from the documentation
        group_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}"
        members_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/members"
        hiscores_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/hiscores?metric=overall"

        results = []

        # Use requests for maximum compatibility
        import requests

        # 1. Get group details
        try:
            response = requests.get(group_url, headers=headers, timeout=15)
            status_code = response.status_code
            results.append(f"Group URL: {group_url}\nStatus: {status_code}")

            if response.text and response.text.strip():
                try:
                    group_data = response.json()
                    # Limit to first 500 chars to avoid discord message limit
                    formatted_json = json.dumps(group_data, indent=2)[:500] + "..."
                    results.append(f"Group data: {formatted_json}\n")

                    # 2. Get group members
                    members_response = requests.get(members_url, headers=headers, timeout=15)
                    if members_response.status_code == 200:
                        members_data = members_response.json()
                        member_count = len(members_data)
                        results.append(f"Found {member_count} members")

                        if member_count > 0:
                            # Show first member as example (limit to 500 chars)
                            member_json = json.dumps(members_data[0], indent=2)[:500] + "..."
                            results.append(f"First member: {member_json}\n")

                            # 3. Get group hiscores
                            hiscores_response = requests.get(hiscores_url, headers=headers, timeout=15)
                            if hiscores_response.status_code == 200:
                                hiscores_data = hiscores_response.json()
                                results.append(f"Found {len(hiscores_data)} hiscores entries")

                                if len(hiscores_data) > 0:
                                    # Show first hiscore entry (limit to 500 chars)
                                    hiscore_json = json.dumps(hiscores_data[0], indent=2)[:500] + "..."
                                    results.append(f"First hiscore entry: {hiscore_json}")
                    else:
                        results.append(f"Failed to get members: Status {members_response.status_code}")
                except json.JSONDecodeError:
                    results.append(f"Response: {response.text[:200]} (Not valid JSON)\n")
            else:
                results.append(f"Response: Empty content\n")
        except Exception as e:
            results.append(f"Error with {group_url}: {str(e)}\n")

        # Send results
        debug_info = "Group Test Results:\n\n" + "\n".join(results)
        if len(debug_info) > 2000:
            # Split long messages
            parts = [debug_info[i:i+1900] for i in range(0, len(debug_info), 1900)]
            for i, part in enumerate(parts):
                await interaction.followup.send(f"Part {i+1}/{len(parts)}:\n{part}")
        else:
            await interaction.followup.send(debug_info)
    except Exception as e:
        await interaction.followup.send(f"Error in testgroup command: {str(e)}")

@bot.tree.command(name="testmembers", description="Test fetching clan members")
async def testmembers(interaction: discord.Interaction):
    await interaction.response.defer()

    # Use headers according to API documentation
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'OSRS-Defence-Discord-Bot/1.0'
    }

    # Direct call to members endpoint
    import requests
    members_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/members"

    try:
        response = requests.get(members_url, headers=headers, timeout=15)
        if response.status_code == 200 and response.text.strip():
            try:
                members_data = response.json()
                member_count = len(members_data)

                # Get the structure of the first member to understand it
                if member_count > 0:
                    first_member = members_data[0]
                    keys = list(first_member.keys())

                    # Get player data structure if available
                    player_keys = []
                    if 'player' in first_member and isinstance(first_member['player'], dict):
                        player_keys = list(first_member['player'].keys())

                    # Check for snapshot data if it exists
                    snapshot_info = "No snapshot data found"
                    if ('player' in first_member and 
                        'latestSnapshot' in first_member['player'] and 
                        first_member['player']['latestSnapshot']):
                        snapshot = first_member['player']['latestSnapshot']
                        snapshot_info = f"Snapshot found with keys: {list(snapshot.keys())}"

                        # Check for skills data
                        if 'data' in snapshot and 'skills' in snapshot['data']:
                            skill_keys = list(snapshot['data']['skills'].keys())
                            snapshot_info += f"\nSkills available: {skill_keys[:10]}..."

                    # Format the first member as a string with limited length
                    sample_json = json.dumps(first_member, indent=2)[:900]

                    message = f"Found {member_count} members.\n\n"
                    message += f"Member structure keys: {keys}\n\n"
                    message += f"Player structure keys: {player_keys}\n\n"
                    message += f"Snapshot info: {snapshot_info}\n\n"
                    message += f"Sample member data:\n{sample_json}"

                    # Send the detailed info
                    await interaction.followup.send(message)
                else:
                    await interaction.followup.send(f"Found {member_count} members but no data is available.")
            except json.JSONDecodeError as e:
                await interaction.followup.send(f"Error parsing member data: {str(e)}")
        else:
            await interaction.followup.send(f"Failed to fetch members: Status {response.status_code}")
    except Exception as e:
        await interaction.followup.send(f"Error fetching members: {str(e)}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    try:
        await bot.tree.sync()
        print("Successfully synced application commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    update_highscores_task.start()
    print("Bot is ready! Try !ping to test or /testapi to check API connection")

if __name__ == "__main__":
    if not TOKEN:
        print("Please set the DISCORD_TOKEN environment variable")
        exit(1)
    if CHANNEL_ID == 0:
        print("Please set the CHANNEL_ID environment variable")
        exit(1)
    bot.run(TOKEN)