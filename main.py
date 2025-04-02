import discord
from discord.ui import View, Button
import asyncio
import json
import requests
from datetime import datetime
from discord import errors as discord_errors

# Custom View for Highscores buttons
class HighscoresView(View):
    def __init__(self, bot, cached_embeds=None):
        super().__init__(timeout=None)  # No timeout for the view
        self.bot = bot
        self.cached_embeds = cached_embeds or {}

        # Add six buttons - total, skills1, skills2, and three boss buttons
        total_btn = Button(style=discord.ButtonStyle.primary, label="Total Level", custom_id="total")
        skills1_btn = Button(style=discord.ButtonStyle.primary, label="Skills 1", custom_id="skills1")
        skills2_btn = Button(style=discord.ButtonStyle.primary, label="Skills 2", custom_id="skills2")
        bosses1_btn = Button(style=discord.ButtonStyle.primary, label="Bosses 1", custom_id="bosses1")
        bosses2_btn = Button(style=discord.ButtonStyle.primary, label="Bosses 2", custom_id="bosses2")
        bosses3_btn = Button(style=discord.ButtonStyle.primary, label="Bosses 3", custom_id="bosses3")

        # Add button click handlers
        total_btn.callback = self.total_callback
        skills1_btn.callback = self.skills1_callback
        skills2_btn.callback = self.skills2_callback
        bosses1_btn.callback = self.bosses1_callback
        bosses2_btn.callback = self.bosses2_callback
        bosses3_btn.callback = self.bosses3_callback

        # Add buttons to the view
        self.add_item(total_btn)
        self.add_item(skills1_btn)
        self.add_item(skills2_btn)
        self.add_item(bosses1_btn)
        self.add_item(bosses2_btn)
        self.add_item(bosses3_btn)

    async def total_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            if "total" in self.cached_embeds:
                embed = self.cached_embeds["total"]
            else:
                embed = await self.bot.update_highscores(view_type="total")
                self.cached_embeds["total"] = embed

            await interaction.message.edit(embed=embed, view=self)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send("Highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for total button")
        except Exception as e:
            print(f"Error in total callback: {str(e)}")

    async def skills1_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            if "skills1" in self.cached_embeds:
                embed = self.cached_embeds["skills1"]
            else:
                embed = await self.bot.update_highscores(view_type="skills1")
                self.cached_embeds["skills1"] = embed

            await interaction.message.edit(embed=embed, view=self)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send("Skills 1 highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for skills1 button")
        except Exception as e:
            print(f"Error in skills1 callback: {str(e)}")

    async def skills2_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            if "skills2" in self.cached_embeds:
                embed = self.cached_embeds["skills2"]
            else:
                embed = await self.bot.update_highscores(view_type="skills2")
                self.cached_embeds["skills2"] = embed

            await interaction.message.edit(embed=embed, view=self)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send("Skills 2 highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for skills2 button")
        except Exception as e:
            print(f"Error in skills2 callback: {str(e)}")

    async def bosses1_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            if "bosses1" in self.cached_embeds:
                embed = self.cached_embeds["bosses1"]
            else:
                embed = await self.bot.update_highscores(view_type="bosses1")
                self.cached_embeds["bosses1"] = embed

            await interaction.message.edit(embed=embed, view=self)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send("Bosses 1 highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for bosses1 button")
        except Exception as e:
            print(f"Error in bosses1 callback: {str(e)}")

    async def bosses2_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            if "bosses2" in self.cached_embeds:
                embed = self.cached_embeds["bosses2"]
            else:
                embed = await self.bot.update_highscores(view_type="bosses2")
                self.cached_embeds["bosses2"] = embed

            await interaction.message.edit(embed=embed, view=self)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send("Bosses 2 highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for bosses2 button")
        except Exception as e:
            print(f"Error in bosses2 callback: {str(e)}")

    async def bosses3_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            if "bosses3" in self.cached_embeds:
                embed = self.cached_embeds["bosses3"]
            else:
                embed = await self.bot.update_highscores(view_type="bosses3")
                self.cached_embeds["bosses3"] = embed

            await interaction.message.edit(embed=embed, view=self)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send("Bosses 3 highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for bosses3 button")
        except Exception as e:
            print(f"Error in bosses3 callback: {str(e)}")

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

    async def get_player_details(self, username):
        try:
            url = f"{self.base_url}/players/{username}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API error for player {username}: Status code {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching player details for {username}: {str(e)}")
            return None

# Discord bot
class HighscoresBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wom_client = WOMClient()
        self.GROUP_ID = 2763  # Group ID for OSRS Defence clan
        self.last_message = None
        self.cached_embeds = {}

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')

    async def is_valid_player(self, player_name):
        try:
            # Get individual player details for combat skill levels
            player_details = await self.wom_client.get_player_details(player_name)
            
            # Debug output for troubleshooting
            print(f"Validating player: {player_name}")
            
            # IMPORTANT CHANGE: If we can't get details for a player or if skills data is missing,
            # include them by default (being lenient) - this allows players to show up in lists
            if not player_details:
                print(f"Player {player_name}: Could not fetch details, INCLUDING by default")
                return True
                
            if 'data' not in player_details or 'skills' not in player_details['data']:
                print(f"Player {player_name}: No skills data available, INCLUDING by default")
                return True

            skills = player_details['data']['skills']

            # These are the skills we're checking (must be 2 or less)
            restricted_skills = ['attack', 'strength', 'magic', 'ranged']
            
            # Only exclude players if we can CONFIRM they have more than level 2
            # in the restricted skills
            for skill_name in restricted_skills:
                if skill_name not in skills:
                    # If skill is missing, we can't verify - include by default
                    print(f"Player {player_name}: {skill_name.capitalize()} data missing, INCLUDING by default")
                    continue
                
                # Get the level for this skill
                skill_level = skills[skill_name].get('level', 1)  # Default to 1 if can't find
                
                # If level is more than 2, exclude the player
                if skill_level > 2:
                    print(f"Player {player_name} EXCLUDED: {skill_name.capitalize()} level {skill_level} > 2")
                    return False
            
            # All checks passed, player meets requirements
            print(f"Player {player_name} VALIDATED - meets requirements (≤ 2 in Attack/Strength/Magic/Ranged)")
            return True
            
        except Exception as e:
            print(f"Error validating player {player_name}: {str(e)}")
            # If there's an error, include them by default
            print(f"Player {player_name}: Error during validation, INCLUDING by default")
            return True

    async def create_total_level_embed(self, group_name):
        # Get overall hiscores for total level ranking
        overall_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric='overall')
        if not overall_hiscores:
            return None

        # Prepare highscores embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Total Level",
            description=f"Top players in {group_name} by total level (≤ 2 in Attack/Strength/Magic/Ranged, any level Defence/Hitpoints/Prayer)",
            color=0x3498db,
            timestamp=datetime.now()
        )
        
        # Cache valid players to avoid repeated API calls
        valid_players_cache = {}
        
        # Process all players to get total levels and experience
        processed_players = []
        valid_player_count = 0
        
        print(f"Processing {len(overall_hiscores)} players for total level highscores")
        for entry in overall_hiscores:
            player_name = entry['player']['displayName']
            
            # Check player cache first
            if player_name in valid_players_cache:
                is_valid = valid_players_cache[player_name]
            else:
                # Check if player meets combat level criteria
                is_valid = await self.is_valid_player(player_name)
                valid_players_cache[player_name] = is_valid  # Cache the result
            
            if not is_valid:
                print(f"FILTERED OUT: {player_name} - over combat skill limit")
                continue  # Skip this player if they have more than 2 in any combat skill
                
            valid_player_count += 1

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

        # Add the top 20 by Total Level (or fewer if not enough valid players)
        top_text = ""
        if processed_players:
            for i, player in enumerate(processed_players[:20], 1):
                top_text += f"{i}. {player['name']} | Total: {player['total_level']} | XP: {player['total_exp']:,}\n"
        else:
            top_text = "No players found meeting the criteria (≤ 2 in Attack/Strength/Magic/Ranged)"

        embed.add_field(name="Top 20 Players by Total Level", value=top_text, inline=False)
        embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")

        return embed

    async def create_skills_embed(self, group_name, part=1):
        # All skills, excluding Attack, Strength, Magic, and Ranged
        all_skills = [
            'defence', 'hitpoints', 'prayer', 
            'cooking', 'woodcutting', 'fletching', 'fishing', 'firemaking', 'crafting',
            'smithing', 'mining', 'herblore', 'agility', 'thieving', 'slayer',
            'farming', 'runecraft', 'hunter', 'construction'
        ]

        # Split skills into two parts
        skills_per_part = len(all_skills) // 2
        if part == 1:
            skills = all_skills[:skills_per_part]  # First half of skills
            part_range = "Combat & Basic"
        else:  # part 2
            skills = all_skills[skills_per_part:]  # Second half of skills
            part_range = "Gathering & Production"

        # Prepare skills embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Skills {part_range}",
            description=f"Top 5 players in each skill for {group_name} (≤ 2 in Attack/Strength/Magic/Ranged, any level Defence/Hitpoints/Prayer)",
            color=0x3498db,
            timestamp=datetime.now()
        )

        # Process skills for this part
        for skill in skills:
            skill_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=skill)
            if skill_hiscores:
                skill_text = ""
                valid_count = 0
                processed_count = 0

                # Keep processing until we get 5 valid players or run out of entries
                while valid_count < 5 and processed_count < len(skill_hiscores):
                    entry = skill_hiscores[processed_count]
                    processed_count += 1

                    player_name = entry['player']['displayName']

                    # Check if player meets combat level criteria
                    if not await self.is_valid_player(player_name):
                        print(f"Skipping {player_name} for {skill} highscore - over combat skill limit")
                        continue  # Skip this player

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
                        valid_count += 1
                        skill_text += f"{valid_count}. {player_name} | Lvl: {skill_level} | XP: {exp:,}\n"

                if skill_text:  # Only add field if there are players with levels
                    embed.add_field(name=skill.capitalize(), value=skill_text, inline=True)

        embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")
        return embed

    async def create_skills_embed1(self, group_name):
        return await self.create_skills_embed(group_name, part=1)

    async def create_skills_embed2(self, group_name):
        return await self.create_skills_embed(group_name, part=2)

    async def create_bosses_embed(self, group_name, part=1):
        # Split all bosses into three groups
        all_bosses = [
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

        # Calculate how many bosses per part
        bosses_per_part = len(all_bosses) // 3
        if part == 1:
            bosses = all_bosses[:bosses_per_part]
            part_range = "1-16"
        elif part == 2:
            bosses = all_bosses[bosses_per_part:2*bosses_per_part]
            part_range = "17-32"
        else:  # part 3
            bosses = all_bosses[2*bosses_per_part:]
            part_range = "33-50"

        # Prepare bosses embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Bosses {part_range}",
            description=f"Top 5 players for each boss in {group_name} (≤ 2 in Attack/Strength/Magic/Ranged, any level Defence/Hitpoints/Prayer)",
            color=0x3498db,
            timestamp=datetime.now()
        )

        # Process bosses for this part
        for boss in bosses:
            try:
                boss_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=boss)
                if boss_hiscores:
                    boss_text = ""
                    valid_count = 0
                    processed_count = 0

                    # Keep processing until we get 5 valid players or run out of entries
                    while valid_count < 5 and processed_count < len(boss_hiscores):
                        entry = boss_hiscores[processed_count]
                        processed_count += 1

                        player_name = entry['player']['displayName']

                        # Check if player meets combat level criteria
                        if not await self.is_valid_player(player_name):
                            print(f"Skipping {player_name} for {boss} highscore - over combat skill limit")
                            continue  # Skip this player

                        # Get the kill count
                        kills = 0
                        if 'data' in entry and 'kills' in entry['data']:
                            kills = entry['data']['kills']

                        # Only include players who have kills for this boss
                        if kills > 0:
                            valid_count += 1
                            boss_text += f"{valid_count}. {player_name} | KC: {kills:,}\n"

                    if boss_text:  # Only add field if there are players with kills
                        # Format boss name for display
                        boss_display_name = ' '.join(word.capitalize() for word in boss.split('_'))
                        embed.add_field(name=boss_display_name, value=boss_text, inline=True)
            except Exception as e:
                print(f"Error processing boss {boss}: {str(e)}")
                continue

        embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")
        return embed

    async def create_bosses_embed1(self, group_name):
        return await self.create_bosses_embed(group_name, part=1)

    async def create_bosses_embed2(self, group_name):
        return await self.create_bosses_embed(group_name, part=2)

    async def create_bosses_embed3(self, group_name):
        return await self.create_bosses_embed(group_name, part=3)

    async def update_highscores(self, message=None, view_type="total", force_refresh=False):
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
            elif view_type == "skills1":
                embed = await self.create_skills_embed1(group_name)
            elif view_type == "skills2":
                embed = await self.create_skills_embed2(group_name)
            elif view_type == "bosses1":
                embed = await self.create_bosses_embed1(group_name)
            elif view_type == "bosses2":
                embed = await self.create_bosses_embed2(group_name)
            elif view_type == "bosses3":
                embed = await self.create_bosses_embed3(group_name)
            else:
                embed = await self.create_total_level_embed(group_name)  # Default to total level

            if embed is None:
                return "Could not create highscores embed"

            if not force_refresh:
                self.cached_embeds[view_type] = embed

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
                # Create view with buttons and pass cached embeds
                view = HighscoresView(self, self.cached_embeds)

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

            # Force refresh the cache
            embed_or_error = await self.update_highscores(message, force_refresh=True)

            if isinstance(embed_or_error, str):
                print(f"DEBUG: Error returned: {embed_or_error}")
                await message.channel.send(f"⚠️ {embed_or_error}")
            else:
                print("DEBUG: Successfully created embed, updating last message")
                try:
                    # Create view with buttons
                    view = HighscoresView(self, self.cached_embeds)

                    # Edit the last message instead of sending a new one
                    await self.last_message.edit(embed=embed_or_error, view=view)
                    await message.add_reaction("✅")  # Add a checkmark reaction to indicate success
                except Exception as e:
                    print(f"DEBUG: Error updating message: {str(e)}")
                    await message.channel.send("Error updating the message. Sending a new one instead.")

                    # Create view with buttons
                    view = HighscoresView(self, self.cached_embeds)
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
                    view = HighscoresView(client, client.cached_embeds)
                    message = await channel.send(embed=embed_or_error, view=view)
                    client.last_message = message
                break
        break

# Run the bot
client.run(TOKEN)