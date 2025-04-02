
import discord
import asyncio
import json
import requests
from datetime import datetime

# Discord bot token
TOKEN = ''  # You'll need to add your token

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
        self.GROUP_ID = 1  # Change to your OSRS Defence clan group ID
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
            
            # Add the top 10 by Total Level
            top_10_text = "Top 10 by Total Level\n"
            for i, entry in enumerate(overall_hiscores[:10], 1):
                player_name = entry['player']['displayName']
                
                # Initialize variables
                total_level = 0
                total_exp = 0
                
                # Calculate total level by summing individual skill levels
                # We'll ignore the 'overall' total level as it seems to be fixed at 2277
                if 'data' in entry and 'skills' in entry['data']:
                    skills_data = entry['data']['skills']
                    
                    # Sum individual skill levels (excluding 'overall')
                    skill_levels = []
                    for skill, data in skills_data.items():
                        if skill != 'overall' and 'level' in data:
                            skill_levels.append(data['level'])
                            total_exp += data.get('experience', 0)
                    
                    total_level = sum(skill_levels) if skill_levels else 0
                    
                    # If we also have 'overall' experience data, use that as it's more accurate
                    if 'overall' in skills_data and 'experience' in skills_data['overall']:
                        total_exp = skills_data['overall'].get('experience', total_exp)
                
                # Fallback to player total exp if available
                if total_exp == 0 and 'player' in entry and 'exp' in entry['player']:
                    total_exp = entry['player']['exp']
                
                top_10_text += f"{i}. {player_name} | Lvl: {total_level} | XP: {total_exp:,}\n"
            
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
            
            # Get hiscores for individual skills
            skills = ['attack', 'defence', 'strength', 'hitpoints', 'ranged', 'prayer', 'magic']
            
            for skill in skills:
                skill_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=skill)
                if skill_hiscores:
                    skill_text = ""
                    # Only get top 5 for each skill to avoid making the message too long
                    for i, entry in enumerate(skill_hiscores[:5], 1):
                        player_name = entry['player']['displayName']
                        
                        # For individual skills, look for the level in the correct structure
                        skill_level = 0
                        exp = 0
                        
                        # Navigate through the correct data structure
                        if 'data' in entry:
                            data = entry['data']
                            if 'skills' in data and skill in data['skills']:
                                skill_data = data['skills'][skill]
                                skill_level = skill_data.get('level', 0)
                                exp = skill_data.get('experience', 0)
                            elif 'level' in data:  # Direct level data (old structure)
                                skill_level = data.get('level', 0)
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
