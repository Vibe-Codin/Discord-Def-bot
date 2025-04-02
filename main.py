import discord
import asyncio
import json
import requests
from datetime import datetime

# Discord bot token
import os
TOKEN = os.environ.get('DISCORD_BOT_TOKEN', '')  # Get token from Replit secrets

# WiseOldMan API client
class WOMClient:
    def __init__(self):
        self.base_url = "https://api.wiseoldman.net/v2"

    async def get_group_details(self, group_id):
        url = f"{self.base_url}/groups/{group_id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None

    async def get_group_hiscores(self, group_id, metric='overall'):
        url = f"{self.base_url}/groups/{group_id}/hiscores"
        params = {'metric': metric}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return None

# Discord bot
class HighscoresBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wom_client = WOMClient()
        self.GROUP_ID = 2763  # Group ID for OSRS Defence clan
        self.last_message = None

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')

    async def update_highscores(self, message=None):
        try:
            # Get group details
            group_details = await self.wom_client.get_group_details(self.GROUP_ID)
            if not group_details:
                return "Could not fetch group details"

            group_name = group_details.get('name', 'Unknown Group')

            # Get overall hiscores for total level ranking
            overall_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric='overall')
            if not overall_hiscores:
                return "Could not fetch overall hiscores"

            # Prepare highscores embed
            embed = discord.Embed(
                title=f"{group_name} Highscores",
                description=f"Top players in {group_name}",
                color=0x3498db,
                timestamp=datetime.now()
            )

            # Process all players to get total levels and experience
            processed_players = []
            for entry in overall_hiscores:
                player_name = entry['player']['displayName']

                # Use the level field directly from the API for total level
                total_level = 0
                total_exp = 0

                # Get total level and exp from the API
                if 'data' in entry:
                    if 'level' in entry['data']:
                        total_level = entry['data']['level']
                    if 'experience' in entry['data']:
                        total_exp = entry['data']['experience']
                
                # Fallback if we couldn't find it in the expected location
                if total_level == 0 and 'player' in entry and 'exp' in entry['player']:
                    total_exp = entry['player']['exp']

                processed_players.append({
                    'name': player_name,
                    'total_level': total_level,
                    'total_exp': total_exp
                })

            # Sort players first by total level (descending), then by total exp (descending) if levels are the same
            processed_players.sort(key=lambda x: (x['total_level'], x['total_exp']), reverse=True)

            # Add the top 10 by Total Level
            top_10_text = "Top 10 by Total Level\n"
            for i, player in enumerate(processed_players[:10], 1):
                # Format to match what you see in Discord
                top_10_text += f"{i}. {player['name']} | Lvl: {player['total_level']} | XP: {player['total_exp']:,}\n"

            embed.add_field(name="", value=top_10_text, inline=False)

            # Print the entire payload for debugging one entry (only once)
            if overall_hiscores and len(overall_hiscores) > 0:
                # Print structure of the first entry for debugging
                print(f"Debug - Structure of first entry in overall_hiscores:")
                print(json.dumps(overall_hiscores[0], indent=2))

                # Check if we actually have data to display
                print(f"Debug - Found {len(overall_hiscores)} players in the hiscores")
                print(f"Debug - First player name: {overall_hiscores[0]['player']['displayName'] if 'player' in overall_hiscores[0] else 'Unknown'}")

                # Check if the field was added to the embed
                print(f"Debug - Current embed fields: {len(embed.fields)}")

            # Get hiscores for all individual skills
            skills = [
                'attack', 'defence', 'strength', 'hitpoints', 'ranged', 'prayer', 'magic',
                'cooking', 'woodcutting', 'fletching', 'fishing', 'firemaking', 'crafting',
                'smithing', 'mining', 'herblore', 'agility', 'thieving', 'slayer',
                'farming', 'runecraft', 'hunter', 'construction'
            ]

            for skill in skills:
                skill_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=skill)
                if skill_hiscores:
                    skill_text = ""
                    # Only get top 5 for each skill to avoid making the message too long
                    for i, entry in enumerate(skill_hiscores[:5], 1):
                        player_name = entry['player']['displayName']

                        # For individual skills, get level and experience directly from the data object
                        skill_level = 0
                        exp = 0

                        # The API returns this in a more straightforward way for individual skills
                        if 'data' in entry:
                            data = entry['data']
                            if 'level' in data:
                                skill_level = data.get('level', 0)
                            if 'experience' in data:
                                exp = data.get('experience', 0)

                        # Only include players who actually have levels in this skill
                        if exp > 0:
                            skill_text += f"{i}. {player_name} | Lvl: {skill_level} | XP: {exp:,}\n"

                    if skill_text:  # Only add field if there are players with levels
                        embed.add_field(name=skill.capitalize(), value=skill_text, inline=True)

            embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")

            # If the embed has no fields, add a message indicating no data was found
            if len(embed.fields) == 0:
                embed.description = f"No hiscores data found for {group_name}. Please make sure the group exists and has members."

            return embed
        except Exception as e:
            return f"An error occurred while updating highscores: {str(e)}"

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.lower() == '/clanhighscores':
            # For /clanhighscores, we just display the highscores with latest data
            processing_msg = await message.channel.send("Fetching highscores... Please wait a moment.")
            print(f"DEBUG: Received command: {message.content}")

            embed_or_error = await self.update_highscores(message)

            if isinstance(embed_or_error, str):
                print(f"DEBUG: Error returned: {embed_or_error}")
                await message.channel.send(f"⚠️ {embed_or_error}")
            else:
                print("DEBUG: Successfully created embed, sending to channel")
                # Send a new message with the highscores
                new_message = await message.channel.send(embed=embed_or_error)
                self.last_message = new_message

                # Delete the processing message after sending the embed
                try:
                    await processing_msg.delete()
                except:
                    pass

                print("DEBUG: Message sent successfully")

        elif message.content.lower() == '!refresh':
            # For !refresh, we update the last sent message if it exists
            if self.last_message is None:
                await message.channel.send("No highscores message to refresh. Please use `/clanhighscores` first.")
                return

            processing_msg = await message.channel.send("Refreshing highscores... Please wait a moment.")
            print(f"DEBUG: Received refresh command")

            embed_or_error = await self.update_highscores(message)

            if isinstance(embed_or_error, str):
                print(f"DEBUG: Error returned: {embed_or_error}")
                await message.channel.send(f"⚠️ {embed_or_error}")
            else:
                print("DEBUG: Successfully created embed, updating last message")
                try:
                    # Edit the last message instead of sending a new one
                    await self.last_message.edit(embed=embed_or_error)
                    await message.add_reaction("✅")  # Add a checkmark reaction to indicate success
                except Exception as e:
                    print(f"DEBUG: Error updating message: {str(e)}")
                    await message.channel.send("Error updating the message. Sending a new one instead.")
                    new_message = await message.channel.send(embed=embed_or_error)
                    self.last_message = new_message

                # Delete the processing message after updating
                try:
                    await processing_msg.delete()
                except:
                    pass

                print("DEBUG: Message refreshed successfully")

intents = discord.Intents.default()
intents.message_content = True

client = HighscoresBot(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

    # Find a channel to post initial highscores
    for guild in client.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed_or_error = await client.update_highscores()
                if isinstance(embed_or_error, str):
                    await channel.send(f"⚠️ {embed_or_error}")
                else:
                    message = await channel.send(embed=embed_or_error)
                    client.last_message = message
                break
        break

# Run the bot
client.run(TOKEN)