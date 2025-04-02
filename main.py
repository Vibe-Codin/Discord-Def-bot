
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
                level = entry['data'].get('level', 0)
                exp = entry['data'].get('experience', 0)
                top_10_text += f"{i}. {player_name} | Lvl: {level} | XP: {exp:,}\n"
            
            embed.add_field(name="", value=top_10_text, inline=False)
            
            # Get hiscores for individual skills
            skills = ['attack', 'defence', 'strength', 'hitpoints', 'ranged', 'prayer', 'magic']
            
            for skill in skills:
                skill_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=skill)
                if skill_hiscores:
                    skill_text = ""
                    # Only get top 5 for each skill to avoid making the message too long
                    for i, entry in enumerate(skill_hiscores[:5], 1):
                        player_name = entry['player']['displayName']
                        # Only include players who actually have levels in this skill
                        if entry['data'].get('experience', 0) > 0:
                            level = entry['data'].get('level', 0)
                            skill_text += f"{i}. {player_name} ({level})\n"
                    
                    if skill_text:  # Only add field if there are players with levels
                        embed.add_field(name=skill.capitalize(), value=skill_text, inline=True)
            
            embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")
            
            return embed
        except Exception as e:
            return f"An error occurred while updating highscores: {str(e)}"

    async def on_message(self, message):
        if message.author == self.user:
            return
        
        if message.content.lower() == '!refresh':
            await message.channel.send("Refreshing highscores... Please wait a moment.")
            embed_or_error = await self.update_highscores(message)
            
            if isinstance(embed_or_error, str):
                await message.channel.send(f"⚠️ {embed_or_error}")
            else:
                if self.last_message:
                    try:
                        await self.last_message.edit(content="", embed=embed_or_error)
                        await message.channel.send("Highscores updated!")
                    except discord.errors.NotFound:
                        new_message = await message.channel.send(embed=embed_or_error)
                        self.last_message = new_message
                    except discord.errors.Forbidden:
                        await message.channel.send("⚠️ Could not update existing message. Here's the latest data:")
                        new_message = await message.channel.send(embed=embed_or_error)
                        self.last_message = new_message
                else:
                    new_message = await message.channel.send(embed=embed_or_error)
                    self.last_message = new_message

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
