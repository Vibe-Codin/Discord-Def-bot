import discord
from discord.ui import View, Button
from discord import app_commands
from discord import errors as discord_errors
import asyncio
import json
import requests
import time
import random
from datetime import datetime
from discord import errors as discord_errors
import concurrent.futures
import logging

logger = logging.getLogger(__name__)

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
        try:
            # Show a loading message to the user who clicked
            await interaction.response.send_message("Switching to Skills category... Please wait.", ephemeral=True)

            # Create a new view with skills as active category
            new_view = HighscoresView(self.bot, self.cached_embeds, active_category="skills")

            # Always use cached embed if available, otherwise create a new one
            if "total" in self.cached_embeds:
                embed = self.cached_embeds["total"]
                # Update the timestamp to show it's current
                embed.timestamp = datetime.now()
            else:
                embed = await self.bot.update_highscores(view_type="total")
                if isinstance(embed, discord.Embed):
                    embed.timestamp = datetime.now()
                    self.cached_embeds["total"] = embed

            try:
                await interaction.message.edit(embed=embed, view=new_view)
                await interaction.edit_original_response(content="✅ Switched to Skills category")
            except discord.errors.HTTPException as e:
                print(f"Error editing message in skills button: {str(e)}")
                try:
                    await interaction.message.channel.send(embed=embed, view=new_view)
                    await interaction.edit_original_response(content="✅ Created new Skills embed (couldn't update existing message)")
                except Exception as e2:
                    print(f"Error sending new message: {str(e2)}")
                    await interaction.edit_original_response(content="❌ Failed to update or create Skills embed")
        except Exception as e:
            print(f"Error in skills_button_callback: {str(e)}")
            try:
                await interaction.edit_original_response(content="❌ An error occurred while processing your request")
            except:
                print("Could not update error message")

    async def bosses_button_callback(self, interaction):
        try:
            # Check if we already have the bosses overview embed cached
            bosses_overview_key = "bosses_overview"
            using_cached = bosses_overview_key in self.cached_embeds

            # Show appropriate loading message
            if using_cached:
                await interaction.response.send_message("Switching to Bosses category... (using cached data)", ephemeral=True)
            else:
                await interaction.response.send_message("Switching to Bosses category... Please wait while loading data.", ephemeral=True)

            # Create a new view with bosses as active category immediately
            try:
                new_view = HighscoresView(self.bot, self.cached_embeds, active_category="bosses")
            except Exception as view_error:
                print(f"Error creating bosses view: {str(view_error)}")
                await interaction.edit_original_response(content=f"❌ Error creating bosses view: {str(view_error)}")
                return

            # Get a generic bosses overview embed or create one
            if using_cached:
                embed = self.cached_embeds[bosses_overview_key]
                # Update the timestamp to show it's current
                embed.timestamp = datetime.now()
                print("Using cached bosses overview data")
            else:
                print("Need to create new bosses overview embed")
                embed = await self.bot.create_bosses_overview_embed()
                if isinstance(embed, discord.Embed):
                    embed.timestamp = datetime.now()
                    self.cached_embeds[bosses_overview_key] = embed
                    # Store cache time for this embed
                    self.bot.cache_times[bosses_overview_key] = time.time()

            success = False
            error_message = None

            try:
                await interaction.message.edit(embed=embed, view=new_view)
                success = True
            except discord.errors.HTTPException as e:
                error_message = str(e)
                print(f"Error editing message in bosses button: {error_message}")
                # Try to send a new message instead
                try:
                    await interaction.message.channel.send(embed=embed, view=new_view)
                    success = True
                    await interaction.edit_original_response(content="✅ Created new Bosses embed (couldn't update existing message)")
                except Exception as e2:
                    error_message = str(e2)
                    print(f"Error sending new message: {error_message}")

            if success:
                if using_cached:
                    # Get cache age
                    cache_age = 0
                    if hasattr(self.bot, 'cache_times') and bosses_overview_key in self.bot.cache_times:
                        cache_age = time.time() - self.bot.cache_times[bosses_overview_key]
                        time_ago = f"{int(cache_age/60)} minutes" if cache_age < 3600 else f"{int(cache_age/3600)} hours"
                        await interaction.edit_original_response(content=f"✅ Switched to Bosses category (cached from {time_ago} ago)")
                    else:
                        await interaction.edit_original_response(content=f"✅ Switched to Bosses category")
                else:
                    await interaction.edit_original_response(content="✅ Switched to Bosses category (freshly loaded)")
            else:
                await interaction.edit_original_response(content=f"❌ Failed to update or create Bosses embed: {error_message}")
        except Exception as e:
            error_msg = str(e)
            print(f"Error in bosses_button_callback: {error_msg}")
            try:
                await interaction.edit_original_response(content=f"❌ An error occurred: {error_msg}")
            except:
                print("Could not update error message")

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
            # Show a loading message to the user who clicked
            await interaction.response.send_message("Loading skill data... Please wait.", ephemeral=True)

            selected_value = self.values[0]
            current_time = time.time()

            # Check if we have a cached embed
            cached_entry = self.cached_embeds.get(selected_value, None)
            cache_age = 0

            if cached_entry and hasattr(self.bot, 'cache_times') and selected_value in self.bot.cache_times:
                cache_age = current_time - self.bot.cache_times[selected_value]

            if cached_entry:
                embed = cached_entry
                # Update the timestamp
                embed.timestamp = datetime.now()
                print(f"Using cached embed for {selected_value}")
            elif selected_value == "total":
                embed = await self.bot.update_highscores(view_type="total")
                if isinstance(embed, discord.Embed):
                    # Set a proper discord.py timestamp
                    embed.timestamp = datetime.now()
                    self.cached_embeds["total"] = embed
            else:
                # For specific skill
                embed = await self.bot.create_single_category_embed(selected_value)
                if isinstance(embed, discord.Embed):
                    # Set a proper discord.py timestamp
                    embed.timestamp = datetime.now()
                    self.cached_embeds[selected_value] = embed

            # Create a new HighscoresView with cached embeds to replace the existing view
            new_view = HighscoresView(self.bot, self.cached_embeds, active_category="skills")

            edited = False
            try:
                await interaction.message.edit(embed=embed, view=new_view)
                edited = True
            except discord.errors.HTTPException as e:
                print(f"Error editing message: {str(e)}")
                # If edit fails, try to send a new message
                try:
                    await interaction.message.channel.send(embed=embed, view=new_view)
                    edited = True
                except Exception as e2:
                    print(f"Error sending new message: {str(e2)}")

            # Only send followup if we successfully edited the message
            if edited:
                # Update the "please wait" message instead of sending a new one
                category_name = next((option.label for option in self.options if option.value == selected_value), selected_value)
                try:
                    if cached_entry and cache_age < 86400:  # Use cached embed if less than 24 hours old
                        time_ago = f"{int(cache_age/60)} minutes" if cache_age < 3600 else f"{int(cache_age/3600)} hours"
                        await interaction.edit_original_response(content=f"✅ {category_name} highscores displayed! (cached from {time_ago} ago)")
                    else:
                        await interaction.edit_original_response(content=f"✅ {category_name} highscores updated!")
                except Exception as e:
                    print(f"Error updating original response: {str(e)}")
            else:
                await interaction.edit_original_response(content="❌ Failed to update the highscores display")

        except discord_errors.NotFound:
            print(f"Interaction expired for {self.values[0] if hasattr(self, 'values') and self.values else 'unknown'}")
        except Exception as e:
            print(f"Error in skills dropdown callback: {str(e)}")

    # Default timeout for API requests (in seconds)
    API_TIMEOUT = 15

    # Additional error handling for dropdown callbacks
    async def safe_interaction_response(self, interaction, content, ephemeral=True):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(content, ephemeral=ephemeral)
            else:
                await interaction.followup.send(content, ephemeral=ephemeral)
            return True
        except Exception as e:
            print(f"Error responding to interaction: {str(e)}")
            return False

            try:
                await interaction.followup.send(f"Error updating highscores: {str(e)}", ephemeral=True)
            except:
                print(f"Could not send error followup")

class BossesDropdown(discord.ui.Select):
    def __init__(self, bot, cached_embeds=None):
        self.bot = bot
        self.cached_embeds = cached_embeds or {}

        # Define boss options - 25 maximum allowed by Discord, using 24 here
        options = [
            # Overview option
            discord.SelectOption(label="Boss Overview", value="bosses_overview", description="Overview of top boss kills"),
            # The 24 specific bosses requested
            discord.SelectOption(label="Bryophyta", value="bryophyta", description="Bryophyta boss highscores"),
            discord.SelectOption(label="Callisto", value="callisto", description="Callisto boss highscores"),
            discord.SelectOption(label="Chambers of Xeric", value="chambers_of_xeric", description="Chambers of Xeric highscores"),
            discord.SelectOption(label="Chambers of Xeric CM", value="chambers_of_xeric_challenge_mode", description="Chambers of Xeric CM highscores"),
            discord.SelectOption(label="Chaos Elemental", value="chaos_elemental", description="Chaos Elemental highscores"),
            discord.SelectOption(label="Chaos Fanatic", value="chaos_fanatic", description="Chaos Fanatic highscores"),
            discord.SelectOption(label="Commander Zilyana", value="commander_zilyana", description="Commander Zilyana boss highscores"),
            discord.SelectOption(label="Corporeal Beast", value="corporeal_beast", description="Corporeal Beast highscores"),
            discord.SelectOption(label="Crazy Archaeologist", value="crazy_archaeologist", description="Crazy Archaeologist highscores"),
            discord.SelectOption(label="Deranged Archaeologist", value="deranged_archaeologist", description="Deranged Archaeologist highscores"),
            discord.SelectOption(label="Giant Mole", value="giant_mole", description="Giant Mole boss highscores"),
            discord.SelectOption(label="Kalphite Queen", value="kalphite_queen", description="Kalphite Queen boss highscores"),
            discord.SelectOption(label="King Black Dragon", value="king_black_dragon", description="King Black Dragon highscores"),
            discord.SelectOption(label="K'ril Tsutsaroth", value="kril_tsutsaroth", description="K'ril Tsutsaroth boss highscores"),
            discord.SelectOption(label="Obor", value="obor", description="Obor boss highscores"),
            discord.SelectOption(label="Sarachnis", value="sarachnis", description="Sarachnis boss highscores"),
            discord.SelectOption(label="Scorpia", value="scorpia", description="Scorpia boss highscores"),
            discord.SelectOption(label="Scurrius", value="scurrius", description="Scurrius boss highscores"),
            discord.SelectOption(label="Tempoross", value="tempoross", description="Tempoross boss highscores"),
            discord.SelectOption(label="The Hueycoatl", value="the_hueycoatl", description="The Hueycoatl boss highscores"),
            discord.SelectOption(label="The Royal Titans", value="the_royal_titans", description="The Royal Titans highscores"),
            discord.SelectOption(label="Venenatis", value="venenatis", description="Venenatis boss highscores"),
            discord.SelectOption(label="Vetion", value="vetion", description="Vetion boss highscores"),
            discord.SelectOption(label="Wintertodt", value="wintertodt", description="Wintertodt boss highscores"),
        ]

        # Ensure we don't exceed 25 options (Discord limit)
        if len(options) > 25:
            print(f"Warning: Dropdown has {len(options)} options, limiting to 25")
            options = options[:25]

        super().__init__(placeholder="Select a boss category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        try:
            # Show a loading message to the user who clicked
            await interaction.response.send_message("Loading boss data... Please wait.", ephemeral=True)

            selected_value = self.values[0]
            current_time = time.time()

            # Check if we have a cached embed and if it's still valid (less than 24 hours old)
            cached_entry = self.cached_embeds.get(selected_value, None)
            cache_age = 0

            # Store cache time in a separate dictionary to avoid attribute issues
            if not hasattr(self.bot, 'cache_times'):
                self.bot.cache_times = {}

            if cached_entry and selected_value in self.bot.cache_times:
                cache_age = current_time - self.bot.cache_times[selected_value]
                embed = cached_entry
                print(f"Using cached embed for {selected_value} (age: {cache_age/60:.1f} minutes)")
                # Update timestamp to show it's current
                embed.timestamp = datetime.now()
            elif selected_value == "bosses_overview":
                embed = await self.bot.create_bosses_overview_embed()
                if isinstance(embed, discord.Embed):
                    self.bot.cache_times[selected_value] = current_time
                    embed.timestamp = datetime.now()
                    self.cached_embeds["bosses_overview"] = embed
            else:
                # For specific boss
                embed = await self.bot.create_single_category_embed(selected_value)
                if isinstance(embed, discord.Embed):
                    self.bot.cache_times[selected_value] = current_time
                    embed.timestamp = datetime.now()
                    self.cached_embeds[selected_value] = embed

            # Create a new HighscoresView with cached embeds to replace the existing view
            new_view = HighscoresView(self.bot, self.cached_embeds, active_category="bosses")

            edited = False
            try:
                await interaction.message.edit(embed=embed, view=new_view)
                edited = True
            except discord.errors.HTTPException as e:
                print(f"Error editing message: {str(e)}")
                # If edit fails, try to send a new message
                try:
                    await interaction.message.channel.send(embed=embed, view=new_view)
                    edited = True
                except Exception as e2:
                    print(f"Error sending new message: {str(e2)}")

            # Only send followup if we successfully edited the message
            if edited:
                # Update the "please wait" message instead of sending a new one
                category_name = next((option.label for option in self.options if option.value == selected_value), selected_value)
                try:
                    if cached_entry and cache_age < 86400:  # Use cached embed if less than 24 hours old
                        time_ago = f"{int(cache_age/60)} minutes" if cache_age < 3600 else f"{int(cache_age/3600)} hours"
                        await interaction.edit_original_response(content=f"✅ {category_name} highscores displayed! (cached from {time_ago} ago)")
                    else:
                        await interaction.edit_original_response(content=f"✅ {category_name} highscores updated!")
                except Exception as e:
                    print(f"Error updating original response: {str(e)}")
            else:
                await interaction.edit_original_response(content="❌ Failed to update the highscores display")

        except discord_errors.NotFound:
            print(f"Interaction expired for {self.values[0] if hasattr(self, 'values') and self.values else 'unknown'}")
        except Exception as e:
            print(f"Error in bosses dropdown callback: {str(e)}")
            try:
                await interaction.followup.send(f"Error updating highscores: {str(e)}", ephemeral=True)
            except:
                print(f"Could not send error followup")

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
        self.api_semaphore = asyncio.Semaphore(5) # Added semaphore here
        self.user_agent = "Discord Highscores Bot (https://github.com/yourusername/yourrepo)" # Added User-Agent

    async def _get_cached_or_fetch(self, cache_key, url, params=None, timeout=15):
        current_time = time.time()

        # Check if we have a cached response and it's still valid
        if cache_key in self.cache and current_time < self.cache_expiry.get(cache_key, 0):
            print(f"Using cached data for {cache_key} (age: {(current_time - (self.cache_expiry.get(cache_key, 0) - self.CACHE_DURATION))/60:.1f} minutes)")
            return self.cache[cache_key]

        # Make the API request with retry logic for rate limits
        max_retries = 5  # Increased max retries
        retry_count = 0

        while retry_count <= max_retries:
            try:
                async with self.api_semaphore: # Acquire semaphore before making request
                    headers = {'User-Agent': self.user_agent} #Added User-Agent to headers
                    response = self.session.get(url, params=params, timeout=timeout, headers=headers)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Cache the successful response
                        self.cache[cache_key] = data
                        self.cache_expiry[cache_key] = current_time + self.CACHE_DURATION
                        return data
                    except ValueError as json_error:
                        print(f"JSON parsing error for {url}: {str(json_error)}")
                        # If we can't parse JSON but have cached data, return that
                        if cache_key in self.cache:
                            print(f"Using older cached data for {cache_key} after JSON parse error")
                            return self.cache[cache_key]
                        return None
                elif response.status_code == 429:
                    # Rate limited - implement exponential backoff with jitter
                    base_wait_time = 2.0 * (2 ** retry_count)  # 2, 4, 8, 16, 32 seconds
                    # Add jitter (±20%)
                    jitter = base_wait_time * 0.2 * (2 * random.random() - 1)
                    wait_time = base_wait_time + jitter
                    print(f"Rate limited (429) for {url}, waiting {wait_time:.1f}s before retry ({retry_count+1}/{max_retries+1})")
                    await asyncio.sleep(wait_time)
                    retry_count += 1
                else:
                    print(f"API returned status code {response.status_code} for {url}")
                    # Check if we have cached data we can use instead
                    if cache_key in self.cache:
                        print(f"Using older cached data for {cache_key} as fallback")
                        return self.cache[cache_key]
                    return None
            except requests.exceptions.Timeout:
                print(f"Request timeout for {url}, attempt {retry_count+1}/{max_retries+1}")
                retry_count += 1
                if retry_count <= max_retries:
                    await asyncio.sleep(2.0)  # Increased wait time
                else:
                    # Check if we have cached data we can use instead
                    if cache_key in self.cache:
                        print(f"Using older cached data for {cache_key} as fallback after timeout")
                        return self.cache[cache_key]
                    return None
            except Exception as e:
                print(f"API request error for {url}: {str(e)}")
                retry_count += 1
                if retry_count <= max_retries:
                    await asyncio.sleep(2.0)  # Increased wait time
                else:
                    # Check if we have cached data we can use instead
                    if cache_key in self.cache:
                        print(f"Using older cached data for {cache_key} as fallback after error")
                        return self.cache[cache_key]
                    return None

        # If we've exhausted all retries
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
        # Get intents from kwargs if provided, otherwise create default ones
        super().__init__(*args, **kwargs)

        # Create command tree for slash commands
        self.tree = discord.app_commands.CommandTree(self)

        self.wom_client = WOMClient()
        self.GROUP_ID = 2763  # Group ID for OSRS Defence clan
        self.last_message = None
        self.cached_embeds = {}
        # Semaphore to limit concurrent API requests
        self.api_semaphore = asyncio.Semaphore(5)  # Allow up to 5 concurrent API requests
        # Cache for player validation results
        self.player_validation_cache = {}
        self.cache_times = {} # Added cache_times dictionary

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
            max_retries = 4  # Increased max retries
            player_details = None
            session = requests.Session()  # Use a session for better performance
            session.headers.update({'User-Agent': 'Discord Highscores Bot (https://github.com/yourusername/yourrepo)'}) # Added User-Agent

            while retry_count < max_retries and player_details is None:
                try:
                    # Directly request player stats from the API
                    url = f"https://api.wiseoldman.net/v2/players/{player_name}"
                    response = session.get(url, timeout=15)  # Increased timeout slightly

                    if response.status_code == 200:
                        player_details = response.json()
                    elif response.status_code == 429:
                        # Rate limited - implement exponential backoff
                        wait_time = 1.0 * (2 ** retry_count)  # 1, 2, 4, 8 seconds
                        print(f"API returned status code 429 for player {player_name}, waiting {wait_time}s before retry")
                        retry_count += 1
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"API returned status code {response.status_code} for player {player_name}")
                        retry_count += 1
                        await asyncio.sleep(1.0)  # Increased wait time for better rate limit handling
                except Exception as e:
                    print(f"Request error for player {player_name}: {str(e)}")
                    retry_count += 1
                    await asyncio.sleep(1.0)  # Increased wait time

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
        rate_limited_count = 0

        # Use a bounded semaphore to limit concurrent API calls
        # and process players in batches to avoid overwhelming the API

        print(f"Processing up to 30 players for total level highscores")

        # Process players in batches to validate them
        batch_size = 5  # Reduced batch size to avoid rate limits
        # Process up to 30 players to get at least 20 valid ones
        max_players_to_check = min(30, len(overall_hiscores))
        batches = [overall_hiscores[i:i+batch_size] for i in range(0, max_players_to_check, batch_size)]

        # Track how many players we've fully processed
        players_processed = 0

        for batch_index, batch in enumerate(batches):
            # Create tasks for validating all players in the batch concurrently
            validation_tasks = []
            for entry in batch:
                player_name = entry['player']['displayName']
                validation_tasks.append((player_name, entry, asyncio.create_task(self.is_valid_player(player_name))))

            # Process results as they complete
            for player_name, entry, validation_task in validation_tasks:
                try:
                    players_processed += 1
                    is_valid = await validation_task

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

                except Exception as e:
                    if "429" in str(e):
                        print(f"Rate limited while processing player {player_name}. Waiting before retrying.")
                        rate_limited_count += 1
                    else:
                        print(f"Error processing player {player_name}: {str(e)}")

            # Larger delay between batches to avoid rate limiting
            # Exponential backoff based on batch index
            delay = min(1.0 + (batch_index * 0.5), 5.0)  # Gradually increase delay up to 5 seconds
            print(f"Waiting {delay:.1f}s before next batch to avoid rate limits...")
            await asyncio.sleep(delay)

        print(f"Processed a total of {players_processed} players out of requested {max_players_to_check}")

        # Print the actual number of players we processed vs filtered
        print(f"Processed {len(processed_players)} valid players from {max_players_to_check} total checked")

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
                validation_tasks.append((player_name, asyncio.create_task(self.is_valid_player(player_name))))

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
                    validation_tasks.append((entry, asyncio.create_task(self.is_valid_player(player_name))))

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
                    validation_tasks.append((player_name, entry, asyncio.create_task(self.is_valid_player(player_name))))

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
            else:
                # Add a placeholder message
                embed.add_field(
                    name=boss_data['name'],
                    value="No qualifying players found with kills",
                    inline=True
                )

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
                    validation_tasks.append((entry, asyncio.create_task(self.is_valid_player(player_name))))

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

            # The 24 specific bosses to check as requested
            all_bosses = [
                'bryophyta', 'callisto', 'chambers_of_xeric', 
                'chambers_of_xeric_challenge_mode', 'chaos_elemental', 'chaos_fanatic', 
                'commander_zilyana', 'corporeal_beast', 'crazy_archaeologist', 
                'deranged_archaeologist', 'giant_mole', 'kalphite_queen', 'king_black_dragon', 
                'kril_tsutsaroth', 'obor', 'sarachnis', 'scorpia', 'scurrius', 
                'tempoross', 'the_hueycoatl', 'the_royal_titans', 'venenatis', 
                'vetion', 'wintertodt'
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
                                validation_tasks.append((entry, asyncio.create_task(self.is_valid_player(player_name))))

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
                              'barrows_chests', 'bryophyta', 'callisto', 'chambers_of_xeric', 
                              'chambers_of_xeric_challenge_mode', 'chaos_elemental', 'chaos_fanatic', 
                              'commander_zilyana', 'corporeal_beast', 'crazy_archaeologist', 
                              'deranged_archaeologist', 'giant_mole', 'kalphite_queen', 'king_black_dragon', 
                              'kril_tsutsaroth', 'obor', 'sarachnis', 'scorpia', 'scurrius', 
                              'tempoross', 'the_hueycoatl', 'the_royal_titans', 'venenatis', 
                              'vetion', 'wintertodt']:
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
            # For !refresh, we update the last sent message if itexists:
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

        elif message.content.lower() == '/cacherefresh' or message.content.lower() == '/refreshcache':
            # Refresh cache and create new embed
            processing_msg = await message.channel.send("Refreshing highscores cache and creating a new embed...")
            print(f"DEBUG: Received cacherefresh command")

            # Force refresh the cache
            embed_or_error = await self.update_highscores(message, force_refresh=True)

            if isinstance(embed_or_error, str):
                print(f"DEBUG: Error returned: {embed_or_error}")
                await message.channel.send(f"⚠️ {embed_or_error}")
            else:
                # Set timestamp
                if isinstance(embed_or_error, discord.Embed):
                    embed_or_error.timestamp = datetime.now()

                # Create view with buttons
                view = HighscoresView(self, self.cached_embeds, active_category="skills")

                # Send a new message with refreshed data
                new_message = await message.channel.send(embed=embed_or_error, view=view)
                self.last_message = new_message

                # Delete the processing message
                try:
                    await processing_msg.delete()
                except:
                    pass

                print("DEBUG: Cache refreshed and new embed created successfully")

        elif message.content.lower() == '/new':
            # Create a new embed without refreshing cache
            processing_msg = await message.channel.send("Creating a new highscores embed without refreshing cache...")
            print(f"DEBUG: Received new embed command")

            # Get embed from cache or create a new one without refreshing
            if "total" in self.cached_embeds:
                embed = self.cached_embeds["total"]
                embed.timestamp = datetime.now()
            else:
                embed = await self.update_highscores(message, force_refresh=False)

            if isinstance(embed, str):
                print(f"DEBUG: Error returned: {embed}")
                await message.channel.send(f"⚠️ {embed}")
            else:
                # Create view with buttons
                view = HighscoresView(self, self.cached_embeds, active_category="skills")

                # Send a new message
                new_message = await message.channel.send(embed=embed, view=view)
                self.last_message = new_message

                # Delete the processing message
                try:
                    await processing_msg.delete()
                except:
                    pass

                print("DEBUG: New embed created successfully without refreshing cache")

intents = discord.Intents.default()
intents.message_content = True

client = HighscoresBot(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

    # Sync commands with Discord - Enhanced with better error handling and retry
    print("Syncing commands with Discord...")
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Clear all existing commands before adding the ones we want
            print("Clearing existing commands...")
            client.tree.clear_commands(guild=None)

            # Only register the 'new' and 'refreshcache' commands
            print("Registering only /new and /refreshcache commands...")

            # Remove any existing commands with the same names
            for cmd in client.tree.get_commands():
                if cmd.name in ["new", "cacherefresh"]:
                    client.tree.remove_command(cmd.name)

            # Add commands explicitly before syncing
            @client.tree.command(name="new", description="Push a new highscores embed without refreshing cache")
            @app_commands.checks.cooldown(1, 30.0, key=lambda i: i.guild_id)
            async def new_command(interaction: discord.Interaction):
                try:
                    # Respond immediately to prevent timeout
                    await interaction.response.defer(thinking=True, ephemeral=True)

                    # Get the channel where the command was used
                    channel = interaction.channel
                    if not channel:
                        await interaction.followup.send("Couldn't access this channel. Try again in a text channel.", ephemeral=True)
                        return

                    # Immediately follow up to acknowledge the command
                    await interaction.followup.send("Creating a new highscores embed...", ephemeral=True)

                    try:
                        # Start the background processing task immediately
                        loading_message = await channel.send("Creating new highscores embed... please wait...")

                        # Get embed from cache or create a new one
                        if "total" in client.cached_embeds:
                            embed = client.cached_embeds["total"]
                            embed.timestamp = datetime.now()
                            print("Using cached total embed for /new command")
                        else:
                            print("No cached total embed found, creating new one for /new command")
                            embed = await client.update_highscores(force_refresh=False)

                        if isinstance(embed, discord.Embed):
                            # Create a new view with cached embeds
                            view = HighscoresView(client, client.cached_embeds, active_category="skills")
                            
                            # Edit the loading message
                            try:
                                await loading_message.edit(content=None, embed=embed, view=view)
                                client.last_message = loading_message
                            except discord.errors.HTTPException as http_err:
                                print(f"HTTP error when editing message: {str(http_err)}")
                                # If edit fails, send a new message
                                new_message = await channel.send(embed=embed, view=view)
                                client.last_message = new_message
                                await loading_message.delete()
                        else:
                            # If we got an error string back
                            error_message = "Error creating highscores embed"
                            if isinstance(embed, str):
                                error_message = embed
                            await loading_message.edit(content=f"⚠️ {error_message}")
                    except Exception as e:
                        print(f"Error in /new command execution: {str(e)}")
                        await channel.send(f"Error creating new highscores embed: {str(e)}")
                except Exception as outer_e:
                    error_message = str(outer_e)
                    print(f"Critical error in /new command: {error_message}")
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.send_message(f"An error occurred: {error_message}", ephemeral=True)
                        else:
                            await interaction.followup.send(f"An error occurred: {error_message}", ephemeral=True)
                    except:
                        print("Could not respond to interaction after error")

            @client.tree.command(name="cacherefresh", description="Refresh highscores cache and push a new embed")
            @app_commands.checks.cooldown(1, 60.0, key=lambda i: i.guild_id)
            async def refresh_cache_command(interaction: discord.Interaction):
                try:
                    # Respond immediately to prevent timeout
                    await interaction.response.defer(thinking=True, ephemeral=True)

                    channel = interaction.channel
                    if not channel:
                        await interaction.followup.send("Couldn't access this channel. Try again in a text channel.", ephemeral=True)
                        return

                    # Immediately follow up to acknowledge the command
                    await interaction.followup.send("Starting cache refresh... I'll post the new embed when it's ready.", ephemeral=True)

                    try:
                        # Start the background processing task but don't wait for it
                        async def background_refresh():
                            try:
                                # Create a loading message
                                loading_message = await channel.send("Refreshing highscores data... please wait...")

                                # Force refresh the cache
                                embed = await client.update_highscores(force_refresh=True)

                                # Set timestamp
                                if isinstance(embed, discord.Embed):
                                    embed.timestamp = datetime.now()

                                    # Create view with buttons
                                    view = HighscoresView(client, client.cached_embeds)

                                    # Edit loading message with the new embed or send new message if edit fails
                                    try:
                                        await loading_message.edit(content=None, embed=embed, view=view)
                                        client.last_message = loading_message
                                    except Exception:
                                        new_message = await channel.send(embed=embed, view=view)
                                        client.last_message = new_message
                                        await loading_message.delete()
                                else:
                                    # If we got an error string back
                                    await loading_message.edit(content=f"Error refreshing cache: {embed}")
                            except Exception as e:
                                print(f"Error in background refresh: {str(e)}")
                                try:
                                    await channel.send(f"Error refreshing highscores: {str(e)}")
                                except:
                                    print(f"Could not send error message to channel")

                        # Start the background task without awaiting it
                        asyncio.create_task(background_refresh())

                    except Exception as e:
                        print(f"Error in refresh_cache command: {str(e)}")
                        await interaction.followup.send(f"Error starting refresh: {str(e)}", ephemeral=True)
                except Exception as outer_e:
                    print(f"Critical error in cacherefresh command: {str(outer_e)}")
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.send_message(f"An error occurred: {str(outer_e)}", ephemeral=True)
                        else:
                            await interaction.followup.send(f"An error occurred: {str(outer_e)}", ephemeral=True)
                    except:
                        print("Could not respond to interaction after error")

            # Sync the commands globally (may take up to an hour to propagate)
            print("Syncing command tree...")
            await client.tree.sync()

            # Verify sync was successful
            commands_after = client.tree.get_commands()
            print(f"Commands synced successfully! Commands in tree: {len(commands_after)}")
            print(f"Available commands: {[cmd.name for cmd in commands_after]}")

            # If no commands were synced, try one more additional sync
            if len(commands_after) == 0:
                print("No commands found after sync, attempting one more sync...")
                await asyncio.sleep(3)
                await client.tree.sync()
                commands_after = client.tree.get_commands()
                print(f"Second sync attempt: {len(commands_after)} commands")

            break
        except Exception as e:
            retry_count += 1
            print(f"Error syncing commands (attempt {retry_count}/{max_retries}): {str(e)}")
            if retry_count < max_retries:
                print(f"Waiting 5 seconds before retry...")
                await asyncio.sleep(5)
            else:
                print("Failed to sync commands after multiple attempts.")

# Add error handler for slash command errors
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds.", ephemeral=True)
    else:
        print(f"Command error: {error}")
        await ctx.send(f"An error occurred: {error}", ephemeral=True)

# Add error handler for app command errors
@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
            ephemeral=True
        )
    else:
        error_message = f"Command error: {str(error)}"
        print(error_message)
        try:
            if interaction.response.is_done():
                await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)
            else:
                await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
        except Exception as e:
            print(f"Error sending error message: {e}")

# Command registration is complete
print("All commands registered to the tree")



# Run the bot
client.run(TOKEN)