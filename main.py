import discord
from discord.ui import View, Button
import asyncio
import json
import requests
import time
from datetime import datetime
from discord import errors as discord_errors
import concurrent.futures

# Custom View for Highscores dropdown menu
class HighscoresView(View):
    def __init__(self, bot, cached_embeds=None, active_category="skills"):
        super().__init__(timeout=None)  # No timeout for the view
        self.bot = bot
        self.cached_embeds = cached_embeds or {}
        self.active_category = active_category

        # Add the Skills button
        skills_button = discord.ui.Button(
            style=discord.ButtonStyle.primary if active_category == "skills" else discord.ButtonStyle.secondary,
            label="Skills",
            custom_id="skills_button"
        )
        skills_button.callback = self.skills_button_callback
        self.add_item(skills_button)

        # Add the Bosses button
        bosses_button = discord.ui.Button(
            style=discord.ButtonStyle.primary if active_category == "bosses" else discord.ButtonStyle.secondary,
            label="Bosses",
            custom_id="bosses_button"
        )
        bosses_button.callback = self.bosses_button_callback
        self.add_item(bosses_button)

        # Add the appropriate dropdown based on active category
        if active_category == "skills":
            self.add_item(SkillsDropdown(self.bot, self.cached_embeds))
        else:
            self.add_item(BossesDropdown(self.bot, self.cached_embeds))

    async def skills_button_callback(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Create a new view with skills as active category
        new_view = HighscoresView(self.bot, self.cached_embeds, active_category="skills")

        # Get the total (Overall) embed or use cached one
        if "total" in self.cached_embeds and hasattr(self.cached_embeds["total"], "_timestamp"):
            embed = self.cached_embeds["total"]
            current_time = time.time()
            cache_age = current_time - self.cached_embeds["total"]._timestamp

            if cache_age > 86400:  # If cache is older than 24 hours, refresh it
                embed = await self.bot.update_highscores(view_type="total")
                embed._timestamp = current_time
                self.cached_embeds["total"] = embed
        else:
            embed = await self.bot.update_highscores(view_type="total")
            embed._timestamp = time.time()
            self.cached_embeds["total"] = embed

        await interaction.message.edit(embed=embed, view=new_view)
        await interaction.followup.send("Switched to Skills category", ephemeral=True)

    async def bosses_button_callback(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Create a new view with bosses as active category
        new_view = HighscoresView(self.bot, self.cached_embeds, active_category="bosses")

        # Get a generic bosses overview embed or create one
        bosses_overview_key = "bosses_overview"

        if bosses_overview_key in self.cached_embeds and hasattr(self.cached_embeds[bosses_overview_key], "_timestamp"):
            embed = self.cached_embeds[bosses_overview_key]
            current_time = time.time()
            cache_age = current_time - self.cached_embeds[bosses_overview_key]._timestamp

            if cache_age > 86400:  # If cache is older than 24 hours, refresh it
                embed = await self.bot.create_bosses_overview_embed()
                embed._timestamp = current_time
                self.cached_embeds[bosses_overview_key] = embed
        else:
            embed = await self.bot.create_bosses_overview_embed()
            embed._timestamp = time.time()
            self.cached_embeds[bosses_overview_key] = embed

        await interaction.message.edit(embed=embed, view=new_view)
        await interaction.followup.send("Switched to Bosses category", ephemeral=True)

# Dropdown menu for highscores selection
class SkillsDropdown(discord.ui.Select):
    def __init__(self, bot, cached_embeds=None):
        self.bot = bot
        self.cached_embeds = cached_embeds or {}

        # Define all skill options
        options = [
            discord.SelectOption(label="Overall", value="total", description="Overall total level highscores"),
            discord.SelectOption(label="Defence", value="defence", description="Defence skill highscores"),
            discord.SelectOption(label="Hitpoints", value="hitpoints", description="Hitpoints skill highscores"),
            discord.SelectOption(label="Prayer", value="prayer", description="Prayer skill highscores"),
            discord.SelectOption(label="Slayer", value="slayer", description="Slayer skill highscores"),
            discord.SelectOption(label="Cooking", value="cooking", description="Cooking skill highscores"),
            discord.SelectOption(label="Woodcutting", value="woodcutting", description="Woodcutting skill highscores"),
            discord.SelectOption(label="Fletching", value="fletching", description="Fletching skill highscores"),
            discord.SelectOption(label="Fishing", value="fishing", description="Fishing skill highscores"),
            discord.SelectOption(label="Firemaking", value="firemaking", description="Firemaking skill highscores"),
            discord.SelectOption(label="Crafting", value="crafting", description="Crafting skill highscores"),
            discord.SelectOption(label="Mining", value="mining", description="Mining skill highscores"),
            discord.SelectOption(label="Smithing", value="smithing", description="Smithing skill highscores"),
            discord.SelectOption(label="Herblore", value="herblore", description="Herblore skill highscores"),
            discord.SelectOption(label="Agility", value="agility", description="Agility skill highscores"),
            discord.SelectOption(label="Thieving", value="thieving", description="Thieving skill highscores"),
            discord.SelectOption(label="Farming", value="farming", description="Farming skill highscores"),
            discord.SelectOption(label="Runecrafting", value="runecrafting", description="Runecrafting skill highscores"),
            discord.SelectOption(label="Hunter", value="hunter", description="Hunter skill highscores"),
            discord.SelectOption(label="Construction", value="construction", description="Construction skill highscores"),
        ]

        super().__init__(placeholder="Select a skill category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            selected_value = self.values[0]
            current_time = time.time()

            # Check if we have a cached embed and if it's still valid (less than 24 hours old)
            cached_entry = self.cached_embeds.get(selected_value, None)
            cache_age = 0

            if cached_entry and hasattr(cached_entry, '_timestamp'):
                cache_age = current_time - cached_entry._timestamp

            # Check if it's the overall total or a specific skill
            if cached_entry and cache_age < 86400:  # Use cached embed if less than 24 hours old
                embed = cached_entry
                print(f"Using cached embed for {selected_value} (age: {cache_age/60:.1f} minutes)")
            elif selected_value == "total":
                embed = await self.bot.update_highscores(view_type="total")
                embed._timestamp = current_time  # Add timestamp to track age
                self.cached_embeds["total"] = embed
            else:
                # For specific skill
                embed = await self.bot.create_single_category_embed(selected_value)
                embed._timestamp = current_time  # Add timestamp to track age
                self.cached_embeds[selected_value] = embed

            # Create a new HighscoresView with cached embeds to replace the existing view
            new_view = HighscoresView(self.bot, self.cached_embeds, active_category="skills")
            await interaction.message.edit(embed=embed, view=new_view)

            # Send a follow-up message that's only visible to the user who clicked
            category_name = next((option.label for option in self.options if option.value == selected_value), selected_value)
            try:
                if cached_entry and cache_age < 86400:  # Use cached embed if less than 24 hours old
                    time_ago = f"{int(cache_age/60)} minutes" if cache_age < 3600 else f"{int(cache_age/3600)} hours"
                    await interaction.followup.send(f"{category_name} highscores displayed! (cached from {time_ago} ago)", ephemeral=True)
                else:
                    await interaction.followup.send(f"{category_name} highscores updated!", ephemeral=True)
            except Exception as e:
                print(f"Error sending followup: {str(e)}")
                # Try a simpler message as fallback
                try:
                    await interaction.followup.send(f"{category_name} highscores displayed!", ephemeral=True)
                except:
                    pass  # Silently ignore if even the fallback fails
        except discord_errors.NotFound:
            print(f"Interaction expired for {self.values[0]}")
        except Exception as e:
            print(f"Error in skills dropdown callback: {str(e)}")
            await interaction.followup.send(f"Error updating highscores: {str(e)}", ephemeral=True)

class BossesDropdown(discord.ui.Select):
    def __init__(self, bot, cached_embeds=None):
        self.bot = bot
        self.cached_embeds = cached_embeds or {}

        # Define all boss options - up to 25 maximum allowed by Discord
        options = [
            # Overview option
            discord.SelectOption(label="Boss Overview", value="bosses_overview", description="Overview of top boss kills"),
            # Core bosses from the new list
            discord.SelectOption(label="Barrows Chests", value="barrows_chests", description="Barrows Chests highscores"),
            discord.SelectOption(label="Chambers of Xeric", value="chambers_of_xeric", description="Chambers of Xeric boss highscores"),
            discord.SelectOption(label="Commander Zilyana", value="commander_zilyana", description="Commander Zilyana boss highscores"),
            discord.SelectOption(label="Corporeal Beast", value="corporeal_beast", description="Corporeal Beast highscores"),
            discord.SelectOption(label="Giant Mole", value="giant_mole", description="Giant Mole boss highscores"),
            discord.SelectOption(label="Kalphite Queen", value="kalphite_queen", description="Kalphite Queen boss highscores"),
            discord.SelectOption(label="King Black Dragon", value="king_black_dragon", description="King Black Dragon highscores"),
            discord.SelectOption(label="K'ril Tsutsaroth", value="kril_tsutsaroth", description="K'ril Tsutsaroth boss highscores"),
            discord.SelectOption(label="Sarachnis", value="sarachnis", description="Sarachnis boss highscores"),
            discord.SelectOption(label="TzTok-Jad", value="tztok_jad", description="TzTok-Jad highscores"),
            discord.SelectOption(label="Wintertodt", value="wintertodt", description="Wintertodt boss highscores"),
            # Some less common bosses
            discord.SelectOption(label="Callisto", value="callisto", description="Callisto boss highscores"),
            discord.SelectOption(label="Cerberus", value="cerberus", description="Cerberus boss highscores"),
            discord.SelectOption(label="Chaos Elemental", value="chaos_elemental", description="Chaos Elemental highscores"),
            discord.SelectOption(label="Tempoross", value="tempoross", description="Tempoross boss highscores"),
            discord.SelectOption(label="Venenatis", value="venenatis", description="Venenatis boss highscores"),
            discord.SelectOption(label="Vetion", value="vetion", description="Vetion boss highscores"),
            discord.SelectOption(label="Scorpia", value="scorpia", description="Scorpia boss highscores"),
            discord.SelectOption(label="Skotizo", value="skotizo", description="Skotizo boss highscores"),
            # Removed Dagannoth Kings combined entry since it's not in the new list
        ]

        super().__init__(placeholder="Select a boss category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        try:
            # Use defer with ephemeral=True to show loading only to the user who clicked
            await interaction.response.defer(ephemeral=True, thinking=True)

            selected_value = self.values[0]
            current_time = time.time()

            # Check if we have a cached embed and if it's still valid (less than 24 hours old)
            cached_entry = self.cached_embeds.get(selected_value, None)
            cache_age = 0

            if cached_entry and hasattr(cached_entry, '_timestamp'):
                cache_age = current_time - cached_entry._timestamp

            # For bosses overview or specific boss
            if cached_entry and cache_age < 86400:  # Use cached embed if less than 24 hours old
                embed = cached_entry
                print(f"Using cached embed for {selected_value} (age: {cache_age/60:.1f} minutes)")
            elif selected_value == "bosses_overview":
                embed = await self.bot.create_bosses_overview_embed()
                embed._timestamp = current_time
                self.cached_embeds["bosses_overview"] = embed
            else:
                # For specific boss
                embed = await self.bot.create_single_category_embed(selected_value)
                embed._timestamp = current_time
                self.cached_embeds[selected_value] = embed

            # Create a new HighscoresView with cached embeds to replace the existing view
            new_view = HighscoresView(self.bot, self.cached_embeds, active_category="bosses")
            await interaction.message.edit(embed=embed, view=new_view)

            # Send a follow-up message that's only visible to the user who clicked
            category_name = next((option.label for option in self.options if option.value == selected_value), selected_value)
            try:
                if cached_entry and cache_age < 86400:  # Use cached embed if less than 24 hours old
                    time_ago = f"{int(cache_age/60)} minutes" if cache_age < 3600 else f"{int(cache_age/3600)} hours"
                    await interaction.followup.send(f"{category_name} highscores displayed! (cached from {time_ago} ago)", ephemeral=True)
                else:
                    await interaction.followup.send(f"{category_name} highscores updated!", ephemeral=True)
            except Exception as e:
                print(f"Error sending followup: {str(e)}")
                # Try a simpler message as fallback
                try:
                    await interaction.followup.send(f"{category_name} highscores displayed!", ephemeral=True)
                except:
                    pass  # Silently ignore if even the fallback fails
        except discord_errors.NotFound:
            print(f"Interaction expired for {self.values[0]}")
        except Exception as e:
            print(f"Error in bosses dropdown callback: {str(e)}")
            await interaction.followup.send(f"Error updating highscores: {str(e)}", ephemeral=True)

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
        self.CACHE_DURATION = 86400  # Cache duration in seconds (24 hours)

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

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')

    # Cache for player validation results (name -> [is_valid, timestamp])
    player_validation_cache = {}
    # Cache expiry time in seconds (6 hours)
    CACHE_EXPIRY = 6 * 60 * 60

    async def is_valid_player(self, player_name):
        try:
            # Set this to True to see very detailed debug information
            DEBUG = False # Reduced debug output
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
            description=f"Top players in {group_name} by total level (≤ 2 in Attack/Strength/Magic/Ranged, any level Defence/Hitpoints/Prayer)",
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

        # Add the top 15 by Total Level
        top_level_text = ""
        if processed_players:
            # Sort by total level first, then by total exp
            level_sorted = sorted(processed_players, key=lambda x: (-x['total_level'], -x['total_exp']))
            for i, player in enumerate(level_sorted[:15], 1):
                top_level_text += f"{i}. {player['name']} | Lvl: {player['total_level']} | XP: {player['total_exp']:,}\n"
        else:
            top_level_text = "No players found meeting the criteria (≤ 2 in Attack/Strength/Magic/Ranged)"

        # Add the top 15 by Total Experience
        top_exp_text = ""
        if processed_players:
            # Sort purely by total exp
            exp_sorted = sorted(processed_players, key=lambda x: -x['total_exp'])
            for i, player in enumerate(exp_sorted[:15], 1):
                top_exp_text += f"{i}. {player['name']} | Lvl: {player['total_level']} | XP: {player['total_exp']:,}\n"
        else:
            top_exp_text = "No players found meeting the criteria (≤ 2 in Attack/Strength/Magic/Ranged)"

        embed.add_field(name="Top 15 Players by Total Level", value=top_level_text, inline=False)
        embed.add_field(name="Top 15 Players by Total Experience", value=top_exp_text, inline=False)
        print(f"Filtering stats: {valid_player_count} players included, {excluded_count} excluded")
        embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')} | {valid_player_count} valid players")

        return embed

    async def create_skills_embed(self, group_name, part=1):
        # All skills, excluding Attack, Strength, Magic, and Ranged
        all_skills = [
            'defence', 'hitpoints', 'prayer', 
            'cooking', 'woodcutting', 'fletching', 'fishing', 'firemaking', 'crafting',
            'smithing', 'mining', 'herblore', 'agility', 'thieving', 'slayer',
            'farming', 'runecrafting', 'hunter', 'construction'
        ]

        # Split skills into three parts
        skills_per_part = len(all_skills) // 3
        if part == 1:
            skills = all_skills[:skills_per_part]  # First third of skills
        elif part == 2:
            skills = all_skills[skills_per_part:skills_per_part*2]  # Middle third of skills
        else:  # part 3
            skills = all_skills[skills_per_part*2:]  # Last third of skills

        # Prepare skills embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Skills {part}",
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

            # If we don't have 10 valid entries yet, process more players
            processed_count = 0
            valid_count = 0

            # Process players in batches until we have 10 or have processed all available
            batch_start = 0
            while valid_count < 10 and batch_start < len(skill_hiscores):
                batch_end = min(batch_start + 10, len(skill_hiscores))
                current_batch = skill_hiscores[batch_start:batch_end]

                # Validate this batch of players
                validation_tasks = []
                for entry in current_batch:
                    player_name = entry['player']['displayName']
                    validation_tasks.append((entry, self.is_valid_player(player_name)))

                for entry, validation_task in validation_tasks:
                    is_valid = await validation_task
                    if is_valid:
                        # Extract player info
                        player_name = entry['player']['displayName']
                        skill_level = 0
                        exp = 0

                        # Get data from the entry
                        if 'data' in entry:
                            data = entry['data']
                            if 'level' in data:
                                skill_level = data.get('level', 0)
                            if 'experience' in data:
                                exp = data.get('experience', 0)

                        # Only include players who have levels in this skill
                        if exp > 0:
                            valid_count += 1
                            skill_data['text'] += f"{valid_count}. {player_name} | Lvl: {skill_level} | XP: {exp:,}\n"
                            skill_data['has_data'] = True

                            # Stop once we have 10 valid entries
                            if valid_count >= 10:
                                break

                # Move to the next batch of players
                batch_start = batch_end

                # Small delay between batches to avoid rate limiting
                await asyncio.sleep(0.1)

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
            else:
                # Add a placeholder message if no results
                embed.add_field(
                    name=skill_data['name'],
                    value="No players found with levels in this skill",
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

    async def create_bosses_embed(self, group_name, part=1):
        # Split all bosses into five groups
        all_bosses = [
            'abyssal_sire', 'alchemical_hydra', 'amoxliatl', 'araxxor', 'artio', 
            'barrows_chests', 'bryophyta', 'callisto', 'calvarion', 'cerberus', 
            'chambers_of_xeric', 'chambers_of_xeric_challenge_mode', 'chaos_elemental', 
            'chaos_fanatic', 'commander_zilyana', 'corporeal_beast', 'crazy_archaeologist', 
            'duke_sucellus', 'general_graardor', 'giant_mole', 'grotesque_guardians', 
            'hespori', 'kalphite_queen', 'king_black_dragon', 'kraken', 'kreearra', 
            'kril_tsutsaroth', 'lunar_chests', 'mimic', 'nex', 'nightmare', 
            'phosanis_nightmare', 'obor', 'phantom_muspah', 'sarachnis', 'scorpia', 
            'scurrius', 'skotizo', 'sol_heredit', 'spindel', 'tempoross', 
            'the_gauntlet', 'the_corrupted_gauntlet', 'the_hueycoatl', 'the_leviathan', 
            'the_royal_titans', 'the_whisperer', 'theatre_of_blood', 'theatre_of_blood_hard_mode', 
            'thermonuclear_smoke_devil', 'tombs_of_amascut', 'tombs_of_amascut_expert', 
            'tzkal_zuk', 'tztok_jad', 'vardorvis', 'venenatis', 'vetion', 
            'vorkath', 'wintertodt', 'zalcano', 'zulrah'
        ]

        # Calculate how many bosses per part (about 10 per part)
        bosses_per_part = len(all_bosses) // 5

        if part == 1:
            bosses = all_bosses[:bosses_per_part]
        elif part == 2:
            bosses = all_bosses[bosses_per_part:2*bosses_per_part]
        elif part == 3:
            bosses = all_bosses[2*bosses_per_part:3*bosses_per_part]
        elif part == 4:
            bosses = all_bosses[3*bosses_per_part:4*bosses_per_part]
        else:  # part 5
            bosses = all_bosses[4*bosses_per_part:]

        # Prepare bosses embed
        embed = discord.Embed(
            title=f"{group_name} Highscores - Bosses {part}",
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

        # Add results to embed
        for boss_data in boss_results:
            if boss_data['has_data']:
                embed.add_field(name=boss_data['name'], value=boss_data['text'], inline=True)

        embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")
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

    async def create_single_category_embed(self, category):
        """Create an embed for a single skill or boss category showing top 20 players"""
        try:
            # Get group name
            group_name = "OSRS Defence"  # Default name
            group_info = await self.wom_client.get_group_details(self.GROUP_ID)
            if group_info and 'name' in group_info:
                group_name = group_info['name']

            # Check if it's a skill or boss by looking at the name
            all_skills = [
                'defence', 'hitpoints', 'prayer', 'cooking', 'woodcutting', 
                'fletching', 'fishing', 'firemaking', 'crafting', 'smithing', 
                'mining', 'herblore', 'agility', 'thieving', 'slayer', 'farming', 
                'runecrafting', 'hunter', 'construction'
            ]

            is_skill = category in all_skills

            # Format the category name for display
            display_name = ' '.join(word.capitalize() for word in category.split('_'))

            # Create the embed
            embed = discord.Embed(
                title=f"{group_name} Highscores - {display_name}",
                description=f"Top 15 players in {display_name} for {group_name} (≤ 2 in Attack/Strength/Magic/Ranged, any level Defence/Hitpoints/Prayer)",
                color=0x3498db,
                timestamp=datetime.now()
            )

            # Get the highscores for this category
            highscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=category)
            if not highscores:
                embed.add_field(name="Error", value="Could not fetch highscores for this category", inline=False)
                return embed

            # Process players in batches
            valid_players = []
            batch_size = 10
            batches = [highscores[i:i+batch_size] for i in range(0, min(60, len(highscores)), batch_size)]

            for batch in batches:
                # Create validation tasks
                validation_tasks = []
                for entry in batch:
                    player_name = entry['player']['displayName']
                    validation_tasks.append((entry, self.is_valid_player(player_name)))

                # Process results
                for entry, validation_task in validation_tasks:
                    is_valid = await validation_task
                    if is_valid:
                        player_name = entry['player']['displayName']

                        # Get appropriate data based on whether it's a skill or boss
                        if is_skill:
                            if 'data' in entry and 'level' in entry['data'] and 'experience' in entry['data']:
                                level = entry['data']['level']
                                exp = entry['data']['experience']
                                # Only include if they have XP in this skill
                                if exp > 0:
                                    valid_players.append({
                                        'name': player_name,
                                        'level': level,
                                        'exp': exp
                                    })
                            else:  # It's a boss
                                if 'data' in entry and 'kills' in entry['data']:
                                    kills = entry['data']['kills']
                                    # Only include if they have kills for this boss
                                    if kills > 0:
                                        valid_players.append({
                                            'name': player_name,
                                            'kills': kills
                                        })

                        # If we have enough players, stop processing
                        if len(valid_players) >= 15:  # We only display 15 anyway
                            break

                        # Small delay between batches
                        await asyncio.sleep(0.1)

            # Sort the players appropriately
            if is_skill:
                # Sort by level first, then by exp
                valid_players.sort(key=lambda x: (-x['level'], -x['exp']))

                # Add players to the embed
                player_list_text = ""
                for i, player in enumerate(valid_players[:15], 1):
                    player_list_text += f"{i}. {player['name']} | Lvl: {player['level']} | XP: {player['exp']:,}\n"

                if player_list_text:
                    embed.add_field(name=f"Top Players in {display_name}", value=player_list_text, inline=False)
                else:
                    embed.add_field(name=f"Top Players in {display_name}", value="No players found with levels in this skill", inline=False)
            else:
                # Sort by kill count
                valid_players.sort(key=lambda x: -x['kills'])

                # Add players to the embed
                player_list_text = ""
                for i, player in enumerate(valid_players[:15], 1):
                    player_list_text += f"{i}. {player['name']} | KC: {player['kills']:,}\n"

                if player_list_text:
                    embed.add_field(name=f"Top Players at {display_name}", value=player_list_text, inline=False)
                else:
                    embed.add_field(name=f"Top Players at {display_name}", value="No players found with kills for this boss", inline=False)

            # Add footer
            player_count = len(valid_players)
            embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')} | {player_count} valid players")

            return embed
        except Exception as e:
            print(f"Error creating embed for {category}: {str(e)}")
            # Create an error embed
            error_embed = discord.Embed(
                title="Error",
                description=f"An error occurred while creating highscores for {category}: {str(e)}",
                color=0xFF0000
            )
            return error_embed

    async def create_bosses_overview_embed(self):
        """Create an overview embed showing top 10 highest KC players across all bosses"""
        try:
            # Get group name
            group_name = "OSRS Defence"  # Default name
            group_info = await self.wom_client.get_group_details(self.GROUP_ID)
            if group_info and 'name' in group_info:
                group_name = group_info['name']

            # Create the overview embed
            embed = discord.Embed(
                title=f"{group_name} Highscores - Top Boss KCs",
                description=f"Top 10 highest boss KCs in {group_name} (≤ 2 in Attack/Strength/Magic/Ranged, any level Defence/Hitpoints/Prayer)",
                color=0x3498db,
                timestamp=datetime.now()
            )

            # All bosses to check
            all_bosses = [
                'amoxliatl', 'araxxor', 'barrows_chests', 'bryophyta', 'callisto', 
                'calvarion', 'cerberus', 'chambers_of_xeric', 'chambers_of_xeric_challenge_mode', 
                'chaos_elemental', 'chaos_fanatic', 'commander_zilyana', 'corporeal_beast', 
                'crazy_archaeologist', 'deranged_archaeologist', 'giant_mole', 'hespori', 
                'kalphite_queen', 'king_black_dragon', 'kril_tsutsaroth', 'lunar_chests', 
                'obor', 'sarachnis', 'scorpia', 'scurrius', 'skotizo', 'spindel', 
                'tempoross', 'the_hueycoatl', 'the_royal_titans', 'thermonuclear_smoke_devil', 
                'tztok_jad', 'venenatis', 'vetion', 'wintertodt'
            ]

            # Store all player KCs across all bosses
            all_kcs = []

            # Process a batch of bosses at a time to avoid rate limiting
            batch_size = 5
            boss_batches = [all_bosses[i:i+batch_size] for i in range(0, len(all_bosses), batch_size)]

            for boss_batch in boss_batches:
                boss_tasks = []
                for boss_name in boss_batch:
                    # Create a task for each boss in the batch
                    async def process_boss(boss):
                        try:
                            # Format boss name for display
                            display_name = ' '.join(word.capitalize() for word in boss.split('_'))

                            # Get the highscores for this boss
                            boss_hiscores = await self.wom_client.get_group_hiscores(self.GROUP_ID, metric=boss)
                            if not boss_hiscores:
                                return []

                            # Find valid players with kills
                            boss_kcs = []
                            max_to_check = min(5, len(boss_hiscores))  # Check top 5 for each boss

                            # Create validation tasks
                            validation_tasks = []
                            for entry in boss_hiscores[:max_to_check]:
                                player_name = entry['player']['displayName']
                                validation_tasks.append((entry, self.is_valid_player(player_name)))

                            # Process results
                            for entry, validation_task in validation_tasks:
                                is_valid = await validation_task
                                if is_valid:
                                    player_name = entry['player']['displayName']

                                    if 'data' in entry and 'kills' in entry['data']:
                                        kills = entry['data']['kills']

                                        # Only include if they have kills for this boss
                                        if kills > 0:
                                            boss_kcs.append({
                                                'name': player_name,
                                                'boss': display_name,
                                                'kills': kills
                                            })

                            return boss_kcs
                        except Exception as e:
                            print(f"Error processing boss {boss}: {str(e)}")
                            return []

                    boss_tasks.append(process_boss(boss_name))

                # Run all boss tasks in this batch concurrently
                batch_results = await asyncio.gather(*boss_tasks)

                # Combine all results
                for result in batch_results:
                    all_kcs.extend(result)

                # Small delay between batches to avoid API rate limits
                await asyncio.sleep(0.5)

            # Find the top 10 KCs across all bosses
            all_kcs.sort(key=lambda x: -x['kills'])
            top_10_kcs = all_kcs[:10]

            if top_10_kcs:
                top_kcs_text = ""
                for i, entry in enumerate(top_10_kcs, 1):
                    top_kcs_text += f"{i}. {entry['name']} - {entry['kills']:,} {entry['boss']} KC\n"

                embed.add_field(
                    name="Top 10 Highest Boss KCs",
                    value=top_kcs_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="Top 10 Highest Boss KCs",
                    value="No valid players found with boss kills",
                    inline=False
                )

            # Add footer
            embed.set_footer(text=f"Last updated | {datetime.now().strftime('%I:%M %p')}")

            return embed
        except Exception as e:
            print(f"Error creating boss overview embed: {str(e)}")
            # Create an error embed
            error_embed = discord.Embed(
                title="Error",
                description=f"An error occurred while creating the boss overview: {str(e)}",
                color=0xFF0000
            )
            return error_embed

    # Dagannoth Kings function removed
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
            elif view_type == "bosses1":
                embed = await self.create_bosses_embed1(group_name)
            elif view_type == "bosses2":
                embed = await self.create_bosses_embed2(group_name)
            elif view_type == "bosses3":
                embed = await self.create_bosses_embed3(group_name)
            elif view_type == "bosses4":
                embed = await self.create_bosses_embed4(group_name)
            elif view_type == "bosses5":
                embed = await self.create_bosses_embed5(group_name)
            elif view_type == "bosses_overview":
                embed = await self.create_bosses_overview_embed()
            # Check if it's a specific skill or boss
            elif view_type in ['defence', 'hitpoints', 'prayer', 'cooking', 'woodcutting', 
                              'fletching', 'fishing', 'firemaking', 'crafting', 'smithing', 
                              'mining', 'herblore', 'agility', 'thieving', 'slayer', 'farming', 
                              'runecrafting', 'hunter', 'construction'] or view_type in [
                              'abyssal_sire', 'alchemical_hydra', 'chambers_of_xeric', 
                              'theatre_of_blood', 'vorkath', 'zulrah', 'nex', 'nightmare', 
                              'the_corrupted_gauntlet', 'tombs_of_amascut', 'king_black_dragon', 
                              'tztok_jad', 'general_graardor', 'commander_zilyana', 'kreearra', 
                              'kril_tsutsaroth', 'giant_mole', 'kalphite_queen', 'sarachnis', 
                              'barrows_chests', 'corporeal_beast', 'tzkal_zuk', 'vardorvis']:
                embed = await self.create_single_category_embed(view_type)
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
                # Create view with buttons and pass cached embeds - default to skills view
                view = HighscoresView(self, self.cached_embeds, active_category="skills")

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
                    # Create view with buttons - preserve the active category if we can detect it from current view
                    active_category = "skills"  # Default

                    # Try to determine the current active category from the message
                    if hasattr(self.last_message, "components") and self.last_message.components:
                        for row in self.last_message.components:
                            for component in row.children:
                                if isinstance(component, discord.ui.Button):
                                    if component.custom_id == "skills_button" and component.style == discord.ButtonStyle.primary:
                                        active_category = "skills"
                                        break
                                    elif component.custom_id == "bosses_button" and component.style == discord.ButtonStyle.primary:
                                        active_category = "bosses"
                                        break

                    view = HighscoresView(self, self.cached_embeds, active_category=active_category)

                    # Edit the last message instead of sending a new one
                    await self.last_message.edit(embed=embed_or_error, view=view)
                    await message.add_reaction("✅")  # Add a checkmark reaction to indicate success
                except Exception as e:
                    print(f"DEBUG: Error updating message: {str(e)}")
                    await message.channel.send("Error updating the message. Sending a new one instead.")

                    # Create view with buttons
                    view = HighscoresView(self, self.cached_embeds, active_category="skills")
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

    # Preload common categories in the background
    asyncio.create_task(preload_categories(client))

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

# Preload categories to improve performance
async def preload_categories(bot):
    print("Preloading common highscore categories...")
    current_time = time.time()
    # Preload total first
    total_embed = await bot.update_highscores(view_type="total")
    total_embed._timestamp = current_time
    bot.cached_embeds["total"] = total_embed

    # Preload bosses overview
    try:
        bosses_overview_embed = await bot.create_bosses_overview_embed()
        bosses_overview_embed._timestamp = current_time
        bot.cached_embeds["bosses_overview"] = bosses_overview_embed
        print("Preloaded bosses overview")
    except Exception as e:
        print(f"Error preloading bosses overview: {str(e)}")

    # List of important categories to preload
    categories = [
        "defence", "hitpoints", "prayer", "slayer",
        "chambers_of_xeric", "theatre_of_blood", "vorkath"
    ]

    # Load them in the background
    for category in categories:
        try:
            embed = await bot.create_single_category_embed(category)
            embed._timestamp = current_time
            bot.cached_embeds[category] = embed
            print(f"Preloaded {category} highscores")
            await asyncio.sleep(1)  # Small delay to prevent rate limiting
        except Exception as e:
            print(f"Error preloading {category}: {str(e)}")

    print("Finished preloading highscore categories")

# Run the bot
client.run(TOKEN)