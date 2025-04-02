import discord
from discord.ui import View, Button
import asyncio
import json
import requests
from datetime import datetime

# Custom View for Highscores buttons
class HighscoresView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)  # No timeout for the view
        self.bot = bot
        
        # Add the three buttons
        total_btn = Button(style=discord.ButtonStyle.primary, label="Total Level", custom_id="total")
        skills_btn = Button(style=discord.ButtonStyle.primary, label="Skills", custom_id="skills")
        bosses_btn = Button(style=discord.ButtonStyle.primary, label="Bosses", custom_id="bosses")
        
        # Add button click handlers
        total_btn.callback = self.total_callback
        skills_btn.callback = self.skills_callback
        bosses_btn.callback = self.bosses_callback
        
        # Add buttons to the view
        self.add_item(total_btn)
        self.add_item(skills_btn)
        self.add_item(bosses_btn)
    
    async def total_callback(self, interaction):
        await interaction.response.defer()
        embed = await self.bot.update_highscores(view_type="total")
        await interaction.message.edit(embed=embed, view=self)
    
    async def skills_callback(self, interaction):
        await interaction.response.defer()
        embed = await self.bot.update_highscores(view_type="skills")
        await interaction.message.edit(embed=embed, view=self)
    
    async def bosses_callback(self, interaction):
        await interaction.response.defer()
        embed = await self.bot.update_highscores(view_type="bosses")
        await interaction.message.edit(embed=embed, view=self)

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

    async def create_total_level_embed(self, group_name):
        # Get overall hiscores for total level ranking
        overall_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric='overall')
        if not overall_hiscores:
            return None

        # Prepare highscores embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Total Level",
            description=f"Top players in {group_name} by total level",
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

        # Sort players by total level and then by total exp (both descending)
        processed_players.sort(key=lambda x: (-x['total_level'], -x['total_exp']))

        # Add the top 20 by Total Level
        top_text = ""
        for i, player in enumerate(processed_players[:20], 1):
            top_text += f"{i}. {player['name']} | Total: {player['total_level']} | XP: {player['total_exp']:,}\n"

        embed.add_field(name="Top 20 Players by Total Level", value=top_text, inline=False)
        embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")

        return embed

    async def create_skills_embed(self, group_name):
        # Prepare skills embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Skills",
            description=f"Top 5 players in each skill for {group_name}",
            color=0x3498db,
            timestamp=datetime.now()
        )

        # Get hiscores for all individual skills
        skills = [
            'attack', 'defence', 'strength', 'hitpoints', 'ranged', 'prayer', 'magic',
            'cooking', 'woodcutting', 'fletching', 'fishing', 'firemaking', 'crafting',
            'smithing', 'mining', 'herblore', 'agility', 'thieving', 'slayer',
            'farming', 'runecraft', 'hunter', 'construction'
        ]

        # Process all skills
        for skill in skills:
            skill_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=skill)
            if skill_hiscores:
                skill_text = ""
                # Only get top 5 for each skill
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
        return embed

    async def create_bosses_embed(self, group_name):
        # Prepare bosses embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Bosses",
            description=f"Top 5 players for each boss in {group_name}",
            color=0x3498db,
            timestamp=datetime.now()
        )

        # Add boss hiscores
        bosses = [
            'abyssal_sire', 'alchemical_hydra', 'barrows_chests', 'bryophyta',
            'callisto', 'cerberus', 'chambers_of_xeric', 'chambers_of_xeric_challenge_mode',
            'chaos_elemental', 'chaos_fanatic', 'commander_zilyana', 'corporeal_beast',
            'crazy_archaeologist', 'dagannoth_prime', 'dagannoth_rex', 'dagannoth_supreme',
            'deranged_archaeologist', 'general_graardor', 'giant_mole', 'grotesque_guardians',
            'hespori', 'kalphite_queen', 'king_black_dragon', 'kraken',
            'kreearra', 'kril_tsutsaroth', 'mimic', 'nex',
            'nightmare', 'phosanis_nightmare', 'obor', 'sarachnis',
            'scorpia', 'skotizo', 'tempoross', 'the_gauntlet',
            'the_corrupted_gauntlet', 'theatre_of_blood', 'theatre_of_blood_hard_mode', 'thermonuclear_smoke_devil',
            'tombs_of_amascut', 'tombs_of_amascut_expert', 'tzkal_zuk', 'tztok_jad',
            'venenatis', 'vetion', 'vorkath', 'wintertodt',
            'zalcano', 'zulrah'
        ]

        # Process bosses
        for boss in bosses:
            try:
                boss_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=boss)
                if boss_hiscores:
                    boss_text = ""
                    # Only get top 5 for each boss
                    for i, entry in enumerate(boss_hiscores[:5], 1):
                        player_name = entry['player']['displayName']

                        # Get the kill count
                        kills = 0
                        if 'data' in entry and 'kills' in entry['data']:
                            kills = entry['data']['kills']

                        # Only include players who have kills for this boss
                        if kills > 0:
                            boss_text += f"{i}. {player_name} | KC: {kills:,}\n"

                    if boss_text:  # Only add field if there are players with kills
                        # Format boss name for display
                        boss_display_name = ' '.join(word.capitalize() for word in boss.split('_'))
                        embed.add_field(name=boss_display_name, value=boss_text, inline=True)
            except Exception as e:
                print(f"Error processing boss {boss}: {str(e)}")
                continue

        embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")
        return embed

    async def update_highscores(self, message=None, view_type="total"):
        try:
            # Get group details
            group_details = await self.wom_client.get_group_hiscores(self.GROUP_ID)
            if not group_details:
                return "Could not fetch group details"

            group_name = "OSRS Defence"  # Default name in case we can't get it from API

            # Try to get the proper group name if possible
            group_info = await self.wom_client.get_group_details(self.GROUP_ID)
            if group_info and 'name' in group_info:
                group_name = group_info['name']

            # Create appropriate embed based on view type
            if view_type == "total":
                embed = await self.create_total_level_embed(group_name)
            elif view_type == "skills":
                embed = await self.create_skills_embed(group_name)
            elif view_type == "bosses":
                embed = await self.create_bosses_embed(group_name)
            else:
                embed = await self.create_total_level_embed(group_name)  # Default to total level

            if embed is None:
                return "Could not create highscores embed"

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
                # Create view with buttons for switching between views
                view = HighscoresView(self)
                
                # Send a new message with the highscores and buttons
                new_message = await message.channel.send(embed=embed_or_error, view=view)
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
                    # Create view with buttons
                    view = HighscoresView(self)
                    
                    # Edit the last message instead of sending a new one
                    await self.last_message.edit(embed=embed_or_error, view=view)
                    await message.add_reaction("✅")  # Add a checkmark reaction to indicate success
                except Exception as e:
                    print(f"DEBUG: Error updating message: {str(e)}")
                    await message.channel.send("Error updating the message. Sending a new one instead.")
                    
                    # Create view with buttons
                    view = HighscoresView(self)
                    new_message = await message.channel.send(embed=embed_or_error, view=view)
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
                    # Create view with buttons
                    view = HighscoresView(client)
                    message = await channel.send(embed=embed_or_error, view=view)
                    client.last_message = message
                break
        break

# Run the bot
client.run(TOKEN)