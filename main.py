
import discord
from discord.ext import commands, tasks
import aiohttp
import os
import json

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
        
        # Try different API endpoints based on documentation
        # First, get the group details to verify we can access the correct clan
        group_endpoint = f"{WISE_OLD_MAN_BASE_URL}/groups/name/osrs-defence"
        print(f"Fetching group details from: {group_endpoint}")
        
        import requests
        try:
            # First try to use requests library directly to reduce any potential issues
            response = requests.get(group_endpoint, headers=headers, timeout=15)
            print(f"Group details response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    group_data = response.json()
                    print(f"Group data: {json.dumps(group_data, indent=2)[:200]}...")
                    
                    # If we got valid group data, now fetch members
                    if 'id' in group_data:
                        group_id = group_data['id']
                        print(f"Found group ID: {group_id}")
                        
                        # Use the found group ID to fetch members
                        members_endpoint = f"{WISE_OLD_MAN_BASE_URL}/groups/{group_id}/members"
                        print(f"Fetching members from: {members_endpoint}")
                        
                        members_response = requests.get(members_endpoint, headers=headers, timeout=15)
                        if members_response.status_code == 200:
                            members_data = members_response.json()
                            print(f"Found {len(members_data)} members")
                            return members_data
                except json.JSONDecodeError as e:
                    print(f"Error decoding group JSON: {e}")
        except Exception as e:
            print(f"Error with direct request: {e}")
        
        # If direct request failed, try aiohttp as fallback
        endpoints = [
            f"{WISE_OLD_MAN_BASE_URL}/groups/name/osrs-defence",  # Get group details first
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/details",  # Get group details by ID
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/members",  # Then get members
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/competitions" # Try competitions as a fallback
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
                            members_data = json.loads(text_data)
                            if members_data:
                                print(f"Successfully parsed data from {url}")
                                return members_data
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
            # Try to get the group by name first
            f"{WISE_OLD_MAN_BASE_URL}/groups/name/osrs-defence",
            
            # Group endpoints
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}",
            
            # Member endpoints
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/members", 
            
            # Competition endpoints
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}/competitions"
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


@bot.tree.command(name="testgroup", description="Test fetching the group details from Wise Old Man API")
async def testgroup(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        # Try to get the group details by name
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'OSRS-Defence-Discord-Bot/1.0'
        }
        
        # Try both name and ID methods
        group_urls = [
            f"{WISE_OLD_MAN_BASE_URL}/groups/name/osrs-defence",
            f"{WISE_OLD_MAN_BASE_URL}/groups/{CLAN_ID}"
        ]
        
        results = []
        
        # Use requests for maximum compatibility
        import requests
        for url in group_urls:
            try:
                response = requests.get(url, headers=headers, timeout=15)
                status_code = response.status_code
                results.append(f"URL: {url}\nStatus: {status_code}")
                
                if response.text and response.text.strip():
                    try:
                        json_data = response.json()
                        formatted_json = json.dumps(json_data, indent=2)
                        results.append(f"Response: {formatted_json}\n\n")
                        
                        if 'id' in json_data:
                            group_id = json_data['id']
                            results.append(f"Found group ID: {group_id}")
                            
                            # Try to get members for this group
                            members_url = f"{WISE_OLD_MAN_BASE_URL}/groups/{group_id}/members"
                            members_response = requests.get(members_url, headers=headers, timeout=15)
                            
                            if members_response.status_code == 200:
                                members_data = members_response.json()
                                member_count = len(members_data)
                                results.append(f"Found {member_count} members")
                                if member_count > 0:
                                    # Show first member as example
                                    results.append(f"First member: {json.dumps(members_data[0], indent=2)}")
                    except json.JSONDecodeError:
                        results.append(f"Response: {response.text[:200]} (Not valid JSON)\n\n")
                else:
                    results.append(f"Response: Empty content\n\n")
            except Exception as e:
                results.append(f"Error with {url}: {str(e)}\n\n")
        
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

@bot.tree.command(name="testmembers", description="Test fetching clan members")
async def testmembers(interaction: discord.Interaction):
    await interaction.response.defer()
    clan_data = await fetch_clan_data()
    if clan_data:
        member_count = len(clan_data)
        sample = clan_data[:3] if member_count >= 3 else clan_data
        await interaction.followup.send(f"Found {member_count} members. First 3: {str(sample)[:1000]}")
    else:
        await interaction.followup.send("Failed to fetch clan data")

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
