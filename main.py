import discord
from discord.ui import View, Button
import asyncio
import json
import requests
import time
from datetime import datetime
from discord import errors as discord_errors
import concurrent.futures

# Custom View for Highscores buttons
class HighscoresView(View):
    def __init__(self, bot, cached_embeds=None):
        super().__init__(timeout=None)  # No timeout for the view
        self.bot = bot
        self.cached_embeds = cached_embeds or {}

        # Create buttons - total and 3 skills buttons
        total_btn = Button(style=discord.ButtonStyle.primary, label="Total Level", custom_id="total")
        skills1_btn = Button(style=discord.ButtonStyle.primary, label="Skills 1", custom_id="skills1")
        skills2_btn = Button(style=discord.ButtonStyle.primary, label="Skills 2", custom_id="skills2")
        skills3_btn = Button(style=discord.ButtonStyle.primary, label="Skills 3", custom_id="skills3")
        
        # Add button click handlers for skills and total
        total_btn.callback = self.total_callback
        skills1_btn.callback = self.skills1_callback
        skills2_btn.callback = self.skills2_callback
        skills3_btn.callback = self.skills3_callback

        # Add basic buttons to the view
        self.add_item(total_btn)
        self.add_item(skills1_btn)
        self.add_item(skills2_btn)
        self.add_item(skills3_btn)
        
        # Add boss buttons based on which categories have data
        self.add_boss_buttons()
        
    def add_boss_buttons(self):
        # Create buttons for bosses based on which categories actually have data
        boss_buttons = []
        
        # Always add Bosses 1 button (primary category)
        bosses1_btn = Button(style=discord.ButtonStyle.primary, label="Bosses 1", custom_id="bosses1")
        bosses1_btn.callback = self.bosses1_callback
        boss_buttons.append(bosses1_btn)
        
        # Add buttons for the remaining boss categories if they have data
        # or if we don't know yet (on first load)
        if not hasattr(self.bot, 'boss_categories_with_data') or not self.bot.boss_categories_with_data or 2 in self.bot.boss_categories_with_data:
            bosses2_btn = Button(style=discord.ButtonStyle.primary, label="Bosses 2", custom_id="bosses2")
            bosses2_btn.callback = self.bosses2_callback
            boss_buttons.append(bosses2_btn)
            
        if not hasattr(self.bot, 'boss_categories_with_data') or not self.bot.boss_categories_with_data or 3 in self.bot.boss_categories_with_data:
            bosses3_btn = Button(style=discord.ButtonStyle.primary, label="Bosses 3", custom_id="bosses3")
            bosses3_btn.callback = self.bosses3_callback
            boss_buttons.append(bosses3_btn)
            
        if not hasattr(self.bot, 'boss_categories_with_data') or not self.bot.boss_categories_with_data or 4 in self.bot.boss_categories_with_data:
            bosses4_btn = Button(style=discord.ButtonStyle.primary, label="Bosses 4", custom_id="bosses4")
            bosses4_btn.callback = self.bosses4_callback
            boss_buttons.append(bosses4_btn)
            
        if not hasattr(self.bot, 'boss_categories_with_data') or not self.bot.boss_categories_with_data or 5 in self.bot.boss_categories_with_data:
            bosses5_btn = Button(style=discord.ButtonStyle.primary, label="Bosses 5", custom_id="bosses5")
            bosses5_btn.callback = self.bosses5_callback
            boss_buttons.append(bosses5_btn)
        
        # Add all boss buttons to the view
        for button in boss_buttons:
            self.add_item(button)

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

            # Get the group name for use in embeds
            group_name = "OSRS Defence"
            group_info = await self.bot.wom_client.get_group_details(self.bot.GROUP_ID)
            if group_info and 'name' in group_info:
                group_name = group_info['name']
                
            # Get boss data using the dynamic method
            embed, part = await self.bot.get_boss_embed(group_name, 1)
            self.cached_embeds[f"bosses{part}"] = embed
            
            # Create a new view with updated boss buttons based on current data
            new_view = HighscoresView(self.bot, self.cached_embeds)
            
            await interaction.message.edit(embed=embed, view=new_view)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send(f"Bosses {part} highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for bosses1 button")
        except Exception as e:
            print(f"Error in bosses1 callback: {str(e)}")

    async def bosses2_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            # Get the group name for use in embeds
            group_name = "OSRS Defence"
            group_info = await self.bot.wom_client.get_group_details(self.bot.GROUP_ID)
            if group_info and 'name' in group_info:
                group_name = group_info['name']
                
            # Get boss data using the dynamic method
            embed, part = await self.bot.get_boss_embed(group_name, 2)
            self.cached_embeds[f"bosses{part}"] = embed
            
            # Create a new view with updated boss buttons based on current data
            new_view = HighscoresView(self.bot, self.cached_embeds)
            
            await interaction.message.edit(embed=embed, view=new_view)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send(f"Bosses {part} highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for bosses2 button")
        except Exception as e:
            print(f"Error in bosses2 callback: {str(e)}")

    async def bosses3_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            # Get the group name for use in embeds
            group_name = "OSRS Defence"
            group_info = await self.bot.wom_client.get_group_details(self.bot.GROUP_ID)
            if group_info and 'name' in group_info:
                group_name = group_info['name']
                
            # Get boss data using the dynamic method
            embed, part = await self.bot.get_boss_embed(group_name, 3)
            self.cached_embeds[f"bosses{part}"] = embed
            
            # Create a new view with updated boss buttons based on current data
            new_view = HighscoresView(self.bot, self.cached_embeds)
            
            await interaction.message.edit(embed=embed, view=new_view)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send(f"Bosses {part} highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for bosses3 button")
        except Exception as e:
            print(f"Error in bosses3 callback: {str(e)}")

    async def bosses4_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            # Get the group name for use in embeds
            group_name = "OSRS Defence"
            group_info = await self.bot.wom_client.get_group_details(self.bot.GROUP_ID)
            if group_info and 'name' in group_info:
                group_name = group_info['name']
                
            # Get boss data using the dynamic method
            embed, part = await self.bot.get_boss_embed(group_name, 4)
            self.cached_embeds[f"bosses{part}"] = embed
            
            # Create a new view with updated boss buttons based on current data
            new_view = HighscoresView(self.bot, self.cached_embeds)
            
            await interaction.message.edit(embed=embed, view=new_view)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send(f"Bosses {part} highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for bosses4 button")
        except Exception as e:
            print(f"Error in bosses4 callback: {str(e)}")

    async def bosses5_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            # Get the group name for use in embeds
            group_name = "OSRS Defence"
            group_info = await self.bot.wom_client.get_group_details(self.bot.GROUP_ID)
            if group_info and 'name' in group_info:
                group_name = group_info['name']
                
            # Get boss data using the dynamic method
            embed, part = await self.bot.get_boss_embed(group_name, 5)
            self.cached_embeds[f"bosses{part}"] = embed
            
            # Create a new view with updated boss buttons based on current data
            new_view = HighscoresView(self.bot, self.cached_embeds)
            
            await interaction.message.edit(embed=embed, view=new_view)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send(f"Bosses {part} highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for bosses5 button")
        except Exception as e:
            print(f"Error in bosses5 callback: {str(e)}")

    async def skills3_callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            if "skills3" in self.cached_embeds:
                embed = self.cached_embeds["skills3"]
            else:
                embed = await self.bot.update_highscores(view_type="skills3")
                self.cached_embeds["skills3"] = embed

            await interaction.message.edit(embed=embed, view=self)
            # Send a follow-up message that's only visible to the user who clicked
            await interaction.followup.send("Skills 3 highscores updated!", ephemeral=True)
        except discord_errors.NotFound:
            print("Interaction expired for skills3 button")
        except Exception as e:
            print(f"Error in skills3 callback: {str(e)}")

# Discord bot token
import os
TOKEN = os.environ.get('DISCORD_BOT_TOKEN', '')  # Get token from Replit secrets

# WiseOldMan API client
class WOMClient:
    def __init__(self):
        self.base_url = "https://api.wiseoldman.net/v2"
        self.session = requests.Session()  # Use a persistent session for connection pooling
        self.cache = {}  # Simple cache for API responses
        self.cache_expiry = {}  # Track when cache entries expire
        self.CACHE_DURATION = 300  # Cache duration in seconds (5 minutes)

    async def _get_cached_or_fetch(self, cache_key, url, params=None, timeout=15):
        current_time = time.time()

        # Check if we have a cached response and it's still valid
        if cache_key in self.cache and current_time < self.cache_expiry.get(cache_key, 0):
            return self.cache[cache_key]

        # Make the API request
        try:
            response = self.session.get(url, params=params, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                # Cache the successful response
                self.cache[cache_key] = data
                self.cache_expiry[cache_key] = current_time + self.CACHE_DURATION
                return data
            return None
        except Exception as e:
            print(f"API request error for {url}: {str(e)}")
            return None

    async def get_group_details(self, group_id):
        cache_key = f"group_details_{group_id}"
        url = f"{self.base_url}/groups/{group_id}"
        return await self._get_cached_or_fetch(cache_key, url)

    async def get_group_hiscores(self, group_id, metric='overall'):
        cache_key = f"group_hiscores_{group_id}_{metric}"
        url = f"{self.base_url}/groups/{group_id}/hiscores"
        params = {'metric': metric}
        return await self._get_cached_or_fetch(cache_key, url, params)

    async def get_player_details(self, username):
        try:
            cache_key = f"player_details_{username}"
            url = f"{self.base_url}/players/{username}"

            data = await self._get_cached_or_fetch(cache_key, url, timeout=15)
            if data:
                return data

            # If we got here, something went wrong but was handled in _get_cached_or_fetch
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
        # Semaphore to limit concurrent API requests
        self.api_semaphore = asyncio.Semaphore(5)  # Allow up to 5 concurrent API requests
        # Cache for player validation results
        self.player_validation_cache = {}
        # Set to track which boss categories have data
        self.boss_categories_with_data = set()

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')

    # Cache for player validation results (name -> [is_valid, timestamp])
    player_validation_cache = {}
    # Cache expiry time in seconds (6 hours)
    CACHE_EXPIRY = 6 * 60 * 60

    async def is_valid_player(self, player_name):
        try:
            # Set this to True to see very detailed debug information
            DEBUG = True
            current_time = time.time()

            # Check cache first to avoid redundant API calls
            if player_name in self.player_validation_cache:
                cache_entry = self.player_validation_cache[player_name]
                # If cache is still valid (within expiry time)
                if current_time - cache_entry[1] < self.CACHE_EXPIRY:
                    if DEBUG:
                        print(f"Player {player_name}: Using cached validation result")
                    return cache_entry[0]  # Return cached validation result

            if DEBUG:
                print(f"Validating player: {player_name}")

            # Try to get player details with a retry mechanism
            retry_count = 0
            max_retries = 3
            player_details = None
            session = requests.Session()  # Use a session for better performance

            while retry_count < max_retries and player_details is None:
                try:
                    # Directly request player stats from the API
                    url = f"https://api.wiseoldman.net/v2/players/{player_name}"
                    response = session.get(url, timeout=15)  # Increased timeout slightly

                    if response.status_code == 200:
                        player_details = response.json()
                    else:
                        print(f"API returned status code {response.status_code} for player {player_name}")
                        retry_count += 1
                        await asyncio.sleep(0.5)  # Reduced wait time for faster processing
                except Exception as e:
                    print(f"Request error for player {player_name}: {str(e)}")
                    retry_count += 1
                    await asyncio.sleep(0.5)  # Reduced wait time

            # If we still couldn't get player details after retries, include them for now
            # This is temporary to avoid filtering out too many players due to API issues
            if not player_details:
                if DEBUG:
                    print(f"Player {player_name}: Could not fetch details after {max_retries} retries, INCLUDING TEMPORARILY")
                # Cache the result
                self.player_validation_cache[player_name] = [True, current_time]
                return True  # Include player if we can't fetch their details

            # Fast path check for required fields
            if (not player_details or 
                'latestSnapshot' not in player_details or 
                not player_details['latestSnapshot'] or 
                'data' not in player_details['latestSnapshot'] or 
                'skills' not in player_details['latestSnapshot']['data']):

                if DEBUG:
                    print(f"Player {player_name}: Missing required data fields, INCLUDING TEMPORARILY")
                # Cache the result
                self.player_validation_cache[player_name] = [True, current_time]
                return True

            skills = player_details['latestSnapshot']['data']['skills']

            if DEBUG:
                print(f"Player {player_name} skills data retrieved successfully")

            # These are the skills we're checking (must be 2 or less)
            restricted_skills = ['attack', 'strength', 'magic', 'ranged']

            # Check each restricted skill strictly - optimized lookup
            for skill_name in restricted_skills:
                # Skip if the skill is missing or incomplete
                if skill_name not in skills or 'level' not in skills[skill_name]:
                    if DEBUG:
                        print(f"Player {player_name}: {skill_name.capitalize()} data incomplete, INCLUDING TEMPORARILY")
                    self.player_validation_cache[player_name] = [True, current_time]
                    return True

                # If level is more than 2, exclude the player
                if skills[skill_name]['level'] > 2:
                    if DEBUG:
                        print(f"Player {player_name} EXCLUDED: {skill_name.capitalize()} level {skills[skill_name]['level']} > 2")
                    # Cache the negative result
                    self.player_validation_cache[player_name] = [False, current_time]
                    return False

            # All checks passed, player meets requirements
            if DEBUG:
                print(f"Player {player_name} VALIDATED - meets requirements (≤ 2 in Attack/Strength/Magic/Ranged)")
            # Cache the positive result
            self.player_validation_cache[player_name] = [True, current_time]
            return True

        except Exception as e:
            print(f"Error validating player {player_name}: {str(e)}")
            # If there's an error, include them temporarily to avoid filtering out too many players
            print(f"Player {player_name}: Error during validation, INCLUDING TEMPORARILY")
            # Don't cache errors to allow retry
            return True

    async def create_total_level_embed(self, group_name):
        # Get overall hiscores for total level ranking
        overall_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric='overall')
        if not overall_hiscores:
            return None

        # Prepare highscores embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Total Level",
            description=f"Top 10 players in {group_name} by total level (≤ 2 in Attack/Strength/Magic/Ranged, any level Defence/Hitpoints/Prayer)",
            color=0x3498db,
            timestamp=datetime.now()
        )

        # Process all players to get total levels and experience
        processed_players = []
        valid_player_count = 0
        excluded_count = 0

        # Use a bounded semaphore to limit concurrent API calls
        # and process players in batches to avoid overwhelming the API

        print(f"Processing {len(overall_hiscores)} players for total level highscores")

        # Process players in batches to validate them
        batch_size = 10  # Process 10 players at a time
        batches = [overall_hiscores[i:i+batch_size] for i in range(0, len(overall_hiscores), batch_size)]

        for batch in batches:
            # Create tasks for validating all players in the batch concurrently
            validation_tasks = []
            for entry in batch:
                player_name = entry['player']['displayName']
                validation_tasks.append(self.is_valid_player(player_name))

            # Run all validation tasks concurrently
            validation_results = await asyncio.gather(*validation_tasks)

            # Process the results
            for i, is_valid in enumerate(validation_results):
                entry = batch[i]
                player_name = entry['player']['displayName']

                if not is_valid:
                    print(f"FILTERED OUT: {player_name} - over combat skill limit or missing data")
                    excluded_count += 1
                    continue  # Skip this player

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

            # Small delay between batches to avoid rate limiting
            await asyncio.sleep(0.1)

        # Sort players by total level and then by total exp (both descending)
        processed_players.sort(key=lambda x: (-x['total_level'], -x['total_exp']))

        # Add the top 10 by Total Level
        top_level_text = ""
        if processed_players:
            # Make sure we have exactly 10 entries for total level
            level_sorted = sorted(processed_players, key=lambda x: (-x['total_level'], -x['total_exp']))
            players_to_show = min(10, len(level_sorted))  # In case we have fewer than 10 valid players
            
            for i, player in enumerate(level_sorted[:players_to_show], 1):
                top_level_text += f"{i}. {player['name']} | Lvl: {player['total_level']} | XP: {player['total_exp']:,}\n"
            
            # Add placeholder entries if we have fewer than 10 players
            if players_to_show < 10:
                for i in range(players_to_show + 1, 11):
                    top_level_text += f"{i}. No player qualifying\n"
        else:
            top_level_text = "No players found meeting the criteria (≤ 2 in Attack/Strength/Magic/Ranged)"

        # Add the top 10 by Total Experience
        top_exp_text = ""
        if processed_players:
            # Make sure we have exactly 10 entries for total experience
            exp_sorted = sorted(processed_players, key=lambda x: -x['total_exp'])
            players_to_show = min(10, len(exp_sorted))  # In case we have fewer than 10 valid players
            
            for i, player in enumerate(exp_sorted[:players_to_show], 1):
                top_exp_text += f"{i}. {player['name']} | Lvl: {player['total_level']} | XP: {player['total_exp']:,}\n"
                
            # Add placeholder entries if we have fewer than 10 players
            if players_to_show < 10:
                for i in range(players_to_show + 1, 11):
                    top_exp_text += f"{i}. No player qualifying\n"
        else:
            top_exp_text = "No players found meeting the criteria (≤ 2 in Attack/Strength/Magic/Ranged)"

        embed.add_field(name="Top 10 Players by Total Level", value=top_level_text, inline=False)
        embed.add_field(name="Top 10 Players by Total Experience", value=top_exp_text, inline=False)
        print(f"Filtering stats: {valid_player_count} players included, {excluded_count} excluded")
        embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')} | {valid_player_count} valid players")

        return embed

    async def create_skills_embed(self, group_name, part=1):
        # All skills, excluding Attack, Strength, Magic, and Ranged
        all_skills = [
            'defence', 'hitpoints', 'prayer', 
            'cooking', 'woodcutting', 'fletching', 'fishing', 'firemaking', 'crafting',
            'smithing', 'mining', 'herblore', 'agility', 'thieving', 'slayer',
            'farming', 'runecraft', 'hunter', 'construction'
        ]

        # Split skills into three parts
        skills_per_part = len(all_skills) // 3
        if part == 1:
            skills = all_skills[:skills_per_part]  # First third of skills
            part_range = "Combat & Core"
        elif part == 2:
            skills = all_skills[skills_per_part:skills_per_part*2]  # Middle third of skills
            part_range = "Gathering"
        else:  # part 3
            skills = all_skills[skills_per_part*2:]  # Last third of skills
            part_range = "Production"

        # Prepare skills embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Skills {part_range}",
            description=f"Top 10 players in each skill for {group_name} (≤ 2 in Attack/Strength/Magic/Ranged, any level Defence/Hitpoints/Prayer)",
            color=0x3498db,
            timestamp=datetime.now()
        )

        # Fetch all skill highscores concurrently to speed up processing
        async def process_skill(skill):
            skill_data = {
                'name': skill.capitalize(),
                'text': "",
                'inline': len(embed.fields) % 3 != 0
            }

            skill_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=skill)
            if not skill_hiscores:
                return skill_data

            valid_count = 0
            processed_count = 0
            valid_entries = []

            # First, concurrently validate the first batch of players
            max_to_check = min(15, len(skill_hiscores))  # Check first 15 players max
            batch = skill_hiscores[:max_to_check]

            # Create validation tasks
            validation_tasks = []
            for entry in batch:
                player_name = entry['player']['displayName']
                validation_tasks.append((player_name, self.is_valid_player(player_name)))

            # Process the results
            for player_name, validation_task in validation_tasks:
                is_valid = await validation_task
                if is_valid:
                    # Find the entry for this player
                    for entry in batch:
                        if entry['player']['displayName'] == player_name:
                            valid_entries.append(entry)
                            if len(valid_entries) >= 10:
                                break

            # Now process the valid entries to build the text - limit to exactly 10 players
            for i, entry in enumerate(valid_entries[:10], 1):
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
                    skill_data['text'] += f"{i}. {player_name} | Lvl: {skill_level} | XP: {exp:,}\n"
                    skill_data['has_data'] = True

            return skill_data

        # Process all skills concurrently
        skill_tasks = [process_skill(skill) for skill in skills]
        skill_results = await asyncio.gather(*skill_tasks)

        # Add all processed skills to the embed
        for skill_data in skill_results:
            if skill_data['text']:  # Only add field if there are players with levels
                embed.add_field(
                    name=skill_data['name'], 
                    value=skill_data['text'], 
                    inline=skill_data['inline']
                )

        embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")
        return embed

    async def create_skills_embed1(self, group_name):
        return await self.create_skills_embed(group_name, part=1)

    async def create_skills_embed2(self, group_name):
        return await self.create_skills_embed(group_name, part=2)

    async def create_skills_embed3(self, group_name):
        return await self.create_skills_embed(group_name, part=3)

    # Store boss categories with data (used to dynamically update the UI)
    boss_categories_with_data = set()

    async def create_bosses_embed(self, group_name, part=1):
        # Split all bosses into five groups
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

        # Calculate how many bosses per part (about 10 per part)
        bosses_per_part = len(all_bosses) // 5

        if part == 1:
            bosses = all_bosses[:bosses_per_part]
            part_range = "1-10"
        elif part == 2:
            bosses = all_bosses[bosses_per_part:2*bosses_per_part]
            part_range = "11-20"
        elif part == 3:
            bosses = all_bosses[2*bosses_per_part:3*bosses_per_part]
            part_range = "21-30"
        elif part == 4:
            bosses = all_bosses[3*bosses_per_part:4*bosses_per_part]
            part_range = "31-40"
        else:  # part 5
            bosses = all_bosses[4*bosses_per_part:]
            part_range = "41-50"

        # Prepare bosses embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Bosses {part_range}",
            description=f"Top 10 players for each boss in {group_name} (≤ 2 in Attack/Strength/Magic/Ranged, any level Defence/Hitpoints/Prayer)",
            color=0x3498db,
            timestamp=datetime.now()
        )

        # Process bosses concurrently for this part
        async def process_boss(boss):
            try:
                boss_display_name = ' '.join(word.capitalize() for word in boss.split('_'))
                boss_data = {
                    'name': boss_display_name,
                    'text': "",
                    'has_data': False
                }

                boss_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=boss)
                if not boss_hiscores:
                    return boss_data

                # Only check the first 15 players maximum to find 10 valid ones
                max_to_check = min(15, len(boss_hiscores))
                batch = boss_hiscores[:max_to_check]

                # Create validation tasks
                validation_tasks = []
                for entry in batch:
                    player_name = entry['player']['displayName']
                    validation_tasks.append((player_name, entry, self.is_valid_player(player_name)))

                # Process results in order of completion
                valid_entries = []
                for player_name, entry, validation_task in validation_tasks:
                    is_valid = await validation_task
                    if is_valid:
                        # Get the kill count
                        kills = 0
                        if 'data' in entry and 'kills' in entry['data']:
                            kills = entry['data']['kills']

                        # Only include players who have kills for this boss
                        if kills > 0:
                            valid_entries.append((player_name, kills))
                            if len(valid_entries) >= 10:
                                break

                # Build the text for this boss
                for i, (player_name, kills) in enumerate(valid_entries[:10], 1):
                    boss_data['text'] += f"{i}. {player_name} | KC: {kills:,}\n"
                    boss_data['has_data'] = True

                return boss_data
            except Exception as e:
                print(f"Error processing boss {boss}: {str(e)}")
                return {
                    'name': ' '.join(word.capitalize() for word in boss.split('_')),
                    'text': "",
                    'has_data': False
                }

        # Process all bosses concurrently with a semaphore to limit API calls
        async def process_all_bosses():
            tasks = []
            for boss in bosses:
                # Wait to acquire the semaphore before starting a new task
                async with self.api_semaphore:
                    tasks.append(process_boss(boss))
            return await asyncio.gather(*tasks)

        boss_results = await process_all_bosses()

        # Check if this boss category has any data
        has_any_data = False
        
        # Add results to embed
        for boss_data in boss_results:
            if boss_data['has_data']:
                has_any_data = True
                embed.add_field(name=boss_data['name'], value=boss_data['text'], inline=True)

        # Track which categories have data
        if has_any_data:
            self.boss_categories_with_data.add(part)
        elif part in self.boss_categories_with_data:
            self.boss_categories_with_data.remove(part)

        embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")
        
        # If this category has no data, return None instead of the embed
        if not has_any_data:
            return None
        
        return embed

    async def create_bosses_embed1(self, group_name):
        return await self.create_bosses_embed(group_name, part=1)

    async def create_bosses_embed2(self, group_name):
        return await self.create_bosses_embed(group_name, part=2)

    async def create_bosses_embed3(self, group_name):
        return await self.create_bosses_embed(group_name, part=3)

    async def create_bosses_embed4(self, group_name):
        return await self.create_bosses_embed(group_name, part=4)

    async def create_bosses_embed5(self, group_name):
        return await self.create_bosses_embed(group_name, part=5)
    
    # New method to get boss embeds in the correct order based on available data
    async def get_boss_embed(self, group_name, requested_part):
        # First, check if the requested part has data
        embed = await self.create_bosses_embed(group_name, part=requested_part)
        if embed:
            return embed, requested_part
        
        # If the requested part doesn't have data, find the next part that does
        for part in range(1, 6):
            if part == requested_part:
                continue  # Skip the part we already checked
                
            embed = await self.create_bosses_embed(group_name, part=part)
            if embed:
                return embed, part
                
        # If no parts have data, return a placeholder embed
        empty_embed = discord.Embed(
            title=f"{group_name} Highscores - Bosses",
            description="No boss data available for any players meeting the criteria (≤ 2 in Attack/Strength/Magic/Ranged).",
            color=0x3498db,
            timestamp=datetime.now()
        )
        empty_embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")
        return empty_embed, 0  # Return 0 as the part to indicate no valid parts

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
            elif view_type == "skills3":
                embed = await self.create_skills_embed3(group_name)
            elif view_type.startswith("bosses"):
                # Extract the part number from view_type (e.g., "bosses3" -> 3)
                try:
                    part = int(view_type[6:])
                    embed, actual_part = await self.get_boss_embed(group_name, part)
                    
                    # Update the view_type to match the actual part we're showing
                    if actual_part > 0:
                        view_type = f"bosses{actual_part}"
                except ValueError:
                    # If there's an issue parsing the part number, default to part 1
                    embed, actual_part = await self.get_boss_embed(group_name, 1)
                    if actual_part > 0:
                        view_type = f"bosses{actual_part}"
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