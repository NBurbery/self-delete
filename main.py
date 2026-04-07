import re
import os
import asyncio
import random
import discord
print(discord.__version__)
import time
import json
from pathlib import Path
from typing import Optional, List
from discord.ext import commands, tasks

user_token = os.environ['token']
spam_id = os.environ['spam_id']
version = 'v2.3'
prefix = "."

P2Assistant = 854233015475109888
poketwo = 716390085896962058
Pokename = 874910942490677270
authorized_ids = [Pokename, poketwo, P2Assistant]
client = commands.Bot(command_prefix=prefix)
intervals = [3.6, 2.8, 3.0, 3.2, 3.4]

TIMEZONE_CONFIG_FILE = "timezone_config.json"
timezone_config = {}

def load_timezone_config():
    global timezone_config
    if os.path.exists(TIMEZONE_CONFIG_FILE):
        with open(TIMEZONE_CONFIG_FILE, 'r') as f:
            timezone_config = json.load(f)
    else:
        timezone_config = {}

def save_timezone_config():
    with open(TIMEZONE_CONFIG_FILE, 'w') as f:
        json.dump(timezone_config, f, indent=4)


# --- Pokemon list loading ---

POKEMON_LISTS = {}

def load_pokemon_lists():
    list_files = {
        'event': 'event.txt',
        'collection': 'collection.txt',
        'rare': 'rare.txt',
        'regional': 'regional.txt',
        'gmax': 'gmax.txt',
        'paradox': 'paradox.txt'
    }
    base_path = Path(__file__).parent
    for list_name, filename in list_files.items():
        filepath = base_path / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                pokemon = [line.strip().lower() for line in f if line.strip()]
                POKEMON_LISTS[list_name] = set(pokemon)
        else:
            POKEMON_LISTS[list_name] = set()

load_pokemon_lists()


# --- Ping detection helpers ---

POKEMON_PATTERNS = [
    r"^##\s*<:[^:]*:\d+>\s*([a-zA-Z\s.''-]+?)(?:〖[^〖]*〗)?\s*$",
    r"^##\s*([a-zA-Z\s.''-]+?)\s*<:[^:]*:\d+>(?:〖[^〖]*〗)?\s*$",
    r"^##\s*([a-zA-Z\s.''-]+?)(?:〖[^〖]*〗)?\s*<:[^:]*:\d+>\s*$",
    r"^##\s*([a-zA-Z\s.''-]+?)(?:〖[^〖]*〗)?(?:\s|$)",
    r"##\s*(?:<:[^:]*:\d+>\s*)?([a-zA-Z\s.''-]+?)(?:\s*<:[^:]*:\d+>)?(?:〖[^〖]*〗|【[^】]*】)?\s*$",
    r"^([a-zA-Z\s.''-]+?)[:]?,?\s*[\d.]+%",
    r"<<([^>]+)>>",
    r"\*\*([^*]+)\*\*",
    r"^([a-zA-Z\s.''-]+)\s*$"
]

def extract_text_from_message(message: discord.Message) -> str:
    return message.content.lower()

def extract_pokemon(content: str) -> Optional[str]:
    for pattern in POKEMON_PATTERNS:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match and match.group(1).strip():
            pokemon = match.group(1).strip()
            pokemon = re.sub(r'\s*(?:\*\*|level\s+\d+|lv\.?\s*\d+|:\s*[\d.]+%).*$', '', pokemon, flags=re.IGNORECASE)
            pokemon = re.sub(r'(?:〖[^〖]*〗|【[^】]*】)', '', pokemon)
            pokemon = re.sub(r':[a-zA-Z0-9_+-]+:', '', pokemon)
            pokemon = re.sub(r'<:[^:]+:\d+>', '', pokemon)
            pokemon = re.sub(r'^\s*##?\s*', '', pokemon)
            pokemon = re.sub(r'\s+', ' ', pokemon).strip()

            if (2 <= len(pokemon) <= 50 and
                re.match(r"^[a-zA-Z\s.''-]+$", pokemon) and
                not re.match(r'^\d+$', pokemon)):

                replacements = {
                    r"\bFarfetch'd\b": "Farfetch'd",
                    r"\bSir['\s]*Fetch'd\b": "Sirfetch'd",
                    r"\bMr\.\s*Mime\b": "Mr. Mime",
                    r"\bMime\s*Jr\.?\b": "Mime Jr.",
                }
                for pat, replacement in replacements.items():
                    pokemon = re.sub(pat, replacement, pokemon, flags=re.IGNORECASE)

                return pokemon
    return None

def has_active_users(content: str, message: discord.Message) -> bool:
    if message.role_mentions:
        return True
    active_users = 0
    monitored_bot_ids = {P2Assistant, poketwo, Pokename}
    for user in message.mentions:
        if user.id in monitored_bot_ids:
            continue
        if re.search(rf'\b{user.id}\s*\(AFK\)', content, re.IGNORECASE):
            continue
        active_users += 1
    content_no_emojis = re.sub(r'<:[^:]*:\d+>', '', content)
    for match in re.finditer(r'\b(\d{15,20})\s*(?:\(AFK\))?', content_no_emojis, re.IGNORECASE):
        user_id_str = match.group(0)
        user_id = int(match.group(1))
        if user_id in monitored_bot_ids:
            continue
        if '(AFK)' in user_id_str.upper():
            continue
        active_users += 1
    return active_users > 0

def is_ping_message(message: discord.Message) -> bool:
    content = extract_text_from_message(message)
    if message.author.id == P2Assistant:
        has_mentions = bool(message.mentions or message.role_mentions or re.search(r'<@[!&]?\d+>', content))
        has_pokemon = extract_pokemon(content) is not None
        has_active = has_active_users(content, message)
        return bool(has_mentions and has_pokemon and has_active)
    elif message.author.id == Pokename:
        has_user_pings = bool(message.mentions or re.search(r'<@!?\d+>|\b\d{15,20}\b', content))
        has_active = has_active_users(content, message)
        return bool(has_user_pings and has_active)
    return False

def get_pokemon_category(pokemon_name: str) -> str:
    pokemon_lower = pokemon_name.lower()
    for list_name, pokemon_set in POKEMON_LISTS.items():
        if pokemon_lower in pokemon_set:
            return list_name
    return 'collection'


# --- Channel workflow ---

async def find_or_create_category(guild: discord.Guild, base_keyword: str) -> Optional[discord.CategoryChannel]:
    for category in guild.categories:
        if base_keyword.lower() in category.name.lower():
            channel_count = len([c for c in guild.channels if c.category_id == category.id])
            if channel_count < 50:
                return category
    max_num = 0
    for cat in guild.categories:
        if base_keyword.lower() in cat.name.lower():
            match = re.search(r'\d+', cat.name)
            if match:
                max_num = max(max_num, int(match.group()))
    next_num = max_num + 1
    try:
        return await guild.create_category(f'{base_keyword} {next_num}')
    except Exception as e:
        print(f'Failed to create category: {e}')
        return None

async def move_channel(channel: discord.TextChannel, pokemon_name: str, category_keyword: str):
    if channel.id in workflow_locks:
        return
    workflow_locks.add(channel.id)

    try:
        sanitized_name = re.sub(r'[^a-z0-9\s-]', '', pokemon_name.lower())
        sanitized_name = re.sub(r'\s+', '-', sanitized_name).strip('-')[:100] or 'pokemon'

        try:
            await channel.clone(name=channel.name)
        except Exception as e:
            print(f'Clone failed: {e}')
            return

        try:
            await channel.edit(name=sanitized_name)
        except Exception as e:
            print(f'Rename failed: {e}')
            return

        try:
            await asyncio.sleep(1)
            await channel.send('<@716390085896962058> redirect 1 2 3 4 5 6 7 8 9 10', delete_after=2)
        except Exception:
            pass

        target_category = await find_or_create_category(channel.guild, category_keyword)
        if not target_category:
            print(f'No category found for {category_keyword}')
            return

        try:
            await channel.edit(category=target_category, sync_permissions=True)
        except discord.HTTPException as e:
            if 'maximum number of channels' in str(e).lower():
                max_num = 0
                for cat in channel.guild.categories:
                    if category_keyword.lower() in cat.name.lower():
                        m = re.search(r'\d+', cat.name)
                        if m:
                            max_num = max(max_num, int(m.group()))
                try:
                    new_cat = await channel.guild.create_category(f'{category_keyword} {max_num + 1}')
                    await channel.edit(category=new_cat, sync_permissions=True)
                except Exception as overflow_e:
                    print(f'Overflow category failed: {overflow_e}')
            else:
                print(f'Move failed: {e}')

    finally:
        workflow_locks.discard(channel.id)


# --- Spam task ---

@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    if channel is None:
        print(f"Could not find channel with ID {spam_id}")
        return
    message_content = ''.join(random.sample(['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'], 7) * 5)
    try:
        await channel.send(message_content)
    except discord.errors.HTTPException as e:
        if e.status == 429:
            print("Rate limit exceeded. Waiting and retrying...")
            await asyncio.sleep(5)
        else:
            print(f"Error sending message: {e}. Retrying in 60 seconds...")
            await asyncio.sleep(60)
    except discord.errors.DiscordServerError as e:
        print(f"Error sending message: {e}. Retrying in 60 seconds...")
        await asyncio.sleep(60)
        await spam_recursive(channel, message_content, 1)

async def spam_recursive(channel, message_content, attempt):
    if attempt <= 3:
        try:
            await channel.send(message_content)
        except discord.errors.DiscordServerError as e:
            print(f"Attempt {attempt} failed. Error: {e}. Retrying in {60 * 2 ** (attempt - 1)} seconds...")
            await asyncio.sleep(60 * 2 ** (attempt - 1))
            await spam_recursive(channel, message_content, attempt + 1)
    else:
        print("All attempts failed. Giving up.")

@spam.before_loop
async def before_spam():
    await client.wait_until_ready()


# --- Timezone ping loop ---

@tasks.loop(hours=12)
async def timezone_ping_loop():
    for guild_id, guild_data in timezone_config.items():
        if not guild_data.get("enabled", False):
            continue
        channel_id = guild_data.get("channel_id")
        location1 = guild_data.get("location1")
        location2 = guild_data.get("location2")
        last_location = guild_data.get("last_location", "location2")
        if not all([channel_id, location1, location2]):
            continue
        channel = client.get_channel(int(channel_id))
        if not channel:
            continue
        next_location = location1 if last_location == "location2" else location2
        try:
            await channel.send(f"<@716390085896962058> tz {next_location}")
            timezone_config[guild_id]["last_location"] = "location1" if next_location == location1 else "location2"
            save_timezone_config()
        except Exception as e:
            print(f"Error sending timezone ping: {e}")

@timezone_ping_loop.before_loop
async def before_timezone_ping_loop():
    await client.wait_until_ready()


# --- on_ready ---

@client.event
async def on_ready():
    print(f'*'*30)
    print(f'Logged in as {client.user.name} ✅:')
    print(f'With ID: {client.user.id}')
    print(f'*'*30)
    print(f'Poketwo Auto Collection {version}')
    print(f'Created by PlayHard')
    print(f'*'*30)
    load_timezone_config()
    timezone_ping_loop.start()
    spam.start()


# --- on_message ---

CATEGORY_KEYWORD_MAP = {
    'event': 'Event',
    'rare': 'Rare',
    'regional': 'Regional',
    'gmax': 'Gmax',
    'paradox': 'Paradox',
    'collection': 'Collection',
}

# Per-channel workflow lock — prevents double triggers from P2 Assistant + Pokename
workflow_locks: set = set()

@client.event
async def on_message(message):
    channel = client.get_channel(message.channel.id)
    in_spawn = channel and channel.category and 'spawn' in channel.category.name.lower()

    # Poketwo catch detection — runs in any channel
    if message.author.id == poketwo:
        content = message.content
        if 'These colors seem unusual...' in content:
            print("Shiny pokemon detected.")
            await message.channel.send("Shiny Pokemon detected.")
        elif 'Gigantamax Factor...' in content:
            print("Gigantamax Factor detected.")
            await message.channel.send("Gigantamax Factor detected.")
        elif 'Congratulations' in content:
            if 'These colors seem unusual...' not in content and 'Gigantamax Factor...' not in content:
                if channel and channel.category and channel.category.name.lower() == "spawn channels":
                    print("Channel not deleted (blacklisted category).")
                else:
                    try:
                        current_time = time.time()
                        future_time = current_time + 15
                        await message.channel.send(f'This channel will be deleted <t:{int(future_time)}:R>')
                        await asyncio.sleep(15)
                        await message.channel.delete()
                        print("Channel deleted.")
                    except discord.errors.NotFound:
                        print("Channel not found or inaccessible.")
            else:
                print("Channel not deleted due to special conditions.")
        return

    # Only do spawn channel logic below this point
    if not in_spawn:
        await client.process_commands(message)
        return

    # P2 Assistant or Pokename ping detection
    if message.author.id in (P2Assistant, Pokename):
        if is_ping_message(message):
            text = extract_text_from_message(message)
            pokemon = extract_pokemon(text)
            if pokemon:
                category_key = get_pokemon_category(pokemon)
                category_keyword = CATEGORY_KEYWORD_MAP.get(category_key, 'Collection')
                asyncio.create_task(move_channel(channel, pokemon, category_keyword))
        return

    # Manual hint trigger — user types 'h' or '@Pokétwo h' in a spawn channel
    content_stripped = message.content.strip()
    is_hint_trigger = (
        content_stripped.lower() == 'h' or
        re.match(r'^<@!?\d+>\s*h$', content_stripped, re.IGNORECASE)
    )
    if is_hint_trigger and message.author.id not in (P2Assistant, Pokename, poketwo):
        try:
            await asyncio.sleep(3)
            found_pokemon = None
            async for hint_msg in message.channel.history(limit=15):
                if hint_msg.created_at.timestamp() <= message.created_at.timestamp():
                    continue
                if hint_msg.author.id not in (P2Assistant, Pokename):
                    continue

                # Check plain text content
                hint_text = hint_msg.content

                # P2 Assistant hint format
                match = re.search(r'possible\s+(?:pok[eé]mon|pokemon):\s*([^,\n\r]+)', hint_text, re.IGNORECASE)
                if match:
                    found_pokemon = match.group(1).strip()
                    found_pokemon = re.sub(r'\s*\([^)]*\).*$', '', found_pokemon).strip()

                # Pokename hint format — top result (plain text or bold)
                if not found_pokemon:
                    match = re.search(r'\*{0,2}1\)\s*([^(*\n]+?)\s*\(\d+(?:\.\d+)?%\)\*{0,2}', hint_text)
                    if match:
                        found_pokemon = match.group(1).strip()

                # Also check embeds
                if not found_pokemon and hint_msg.embeds:
                    for embed in hint_msg.embeds:
                        embed_text = ''
                        if embed.description:
                            embed_text += embed.description + '\n'
                        for field in embed.fields:
                            embed_text += field.value + '\n'
                        match = re.search(r'\*{0,2}1\)\s*([^(*\n]+?)\s*\(\d+(?:\.\d+)?%\)\*{0,2}', embed_text)
                        if match:
                            found_pokemon = match.group(1).strip()
                            break

                if found_pokemon:
                    break

            if found_pokemon:
                category_key = get_pokemon_category(found_pokemon)
                category_keyword = CATEGORY_KEYWORD_MAP.get(category_key, 'Collection')
                asyncio.create_task(move_channel(channel, found_pokemon, category_keyword))
        except Exception as e:
            print(f'Manual hint trigger error: {e}')
        return

    await client.process_commands(message)


# --- Commands ---

@client.command(aliases=['Say'])
@commands.has_permissions(administrator=True)
async def say(ctx, *, args):
    await ctx.send(args)
    await ctx.message.delete()
    print(f'user command deleted ✅')

@client.command()
@commands.has_permissions(administrator=True)
async def start(ctx):
    spam.start()
    await ctx.send('Started Spammer!')
    print(f'Started Spammer! ✅:')

@client.command()
@commands.has_permissions(administrator=True)
async def stop(ctx):
    spam.cancel()
    await ctx.send('Stopped Spammer!')
    print(f'Stopped Spammer! ✅:')

@client.command()
async def delete(ctx):
    await ctx.channel.delete()
    print(f'Channel Deleted ✅:')

@client.command()
async def move(ctx, *, new_category_name: str):
    new_category_name_lower = new_category_name.lower()
    for category in ctx.guild.categories:
        if category.name.lower() == new_category_name_lower:
            channel = ctx.channel
            await channel.edit(category=category)
            await ctx.send(f"Moved {channel.mention} to category '{category.name}'.")
            return
    await ctx.send(f"Category '{new_category_name}' not found.")

@move.error
async def move_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required permissions to move channels.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide the name of the new category.")
    else:
        await ctx.send(f"An error occurred: {error}")

@client.command()
async def sync_all(ctx, category_name: str):
    category = discord.utils.get(ctx.guild.categories, name=category_name)
    if not category:
        await ctx.send(f"Category '{category_name}' not found.")
        return
    for channel in category.channels:
        await channel.edit(sync_permissions=True)
        await asyncio.sleep(1)
    await ctx.send(f"**```js\nAll channels in category '{category_name}' have been synced.```**\n")

@sync_all.error
async def sync_all_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required permissions to sync channels.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide the name of the category.")
    else:
        await ctx.send(f"An error occurred: {error}")

@client.command()
async def cat(ctx, *, name):
    await ctx.guild.create_category(name)
    await ctx.send("successfully created")

@client.command()
async def move_channels(ctx, channel_name, category_name):
    guild = ctx.guild
    category = discord.utils.get(guild.categories, name=category_name)
    if category:
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel) and channel.name == channel_name:
                if channel.category != category:
                    await channel.edit(category=category)
                    print(f'Moved channel "{channel_name}" to the category "{category_name}".')
                    await asyncio.sleep(1)
        await ctx.send(f'Moved all channels with the name "{channel_name}" to the category "{category_name}".')
    else:
        await ctx.send(f'Category "{category_name}" not found.')

@client.command()
async def rename(ctx, new_name: str):
    channel = ctx.channel
    await channel.edit(name=new_name)
    await ctx.send(f"Channel successfully renamed to '{new_name}'.")

@rename.error
async def rename_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required permissions to rename channels.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide the new name for the channel.")
    else:
        await ctx.send(f"An error occurred: {error}")

@client.command()
@commands.has_permissions(manage_channels=True)
async def rename_all(ctx, category_name: str, new_name: str):
    category = discord.utils.get(ctx.guild.categories, name=category_name.lower())
    if not category:
        await ctx.send(f"Category '{category_name}' not found.")
        return
    for channel in category.channels:
        try:
            await channel.edit(name=new_name)
            print(f"Renamed channel '{channel.name}' to '{new_name}'.")
        except Exception as e:
            print(f"Error renaming channel '{channel.name}': {e}")
    await ctx.send(f"All channels in category '{category_name}' renamed to '{new_name}'.")

@client.command()
async def count_channels(ctx):
    text_channels = sum(1 for channel in ctx.guild.channels if isinstance(channel, discord.TextChannel))
    voice_channels = sum(1 for channel in ctx.guild.channels if isinstance(channel, discord.VoiceChannel))
    category_channels = sum(1 for channel in ctx.guild.channels if isinstance(channel, discord.CategoryChannel))
    await ctx.send(f"Text Channels: {text_channels}\nVoice Channels: {voice_channels}\nCategories: {category_channels}")

@client.command()
async def list_channels(ctx):
    channel_counts = {}
    blacklist_category_name = "Spawn Channels"
    blacklist_category = discord.utils.get(ctx.guild.categories, name=blacklist_category_name)
    blacklist_channel_ids = [channel.id for channel in blacklist_category.channels] if blacklist_category else []
    for channel in ctx.guild.channels:
        if isinstance(channel, discord.TextChannel) and channel.id not in blacklist_channel_ids:
            channel_name = channel.name
            if channel_name in channel_counts:
                channel_counts[channel_name] += 1
            else:
                channel_counts[channel_name] = 1
    if not channel_counts:
        await ctx.send("There are no text channels in the server or none outside the specified category.")
    else:
        sorted_channels = sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)
        channels_list = '\n'.join([f"{channel_name}: {count}" for channel_name, count in sorted_channels])
        await ctx.send(f"Channels and their counts (sorted by count):\n```{channels_list}```")

@client.command()
async def pokemon(ctx, *channel_names):
    total_message = "**```js\n"
    char_count = 0
    for channel_name in channel_names:
        channels = ctx.guild.channels
        count = sum(1 for channel in channels if channel.name.lower() == channel_name.lower().strip(","))
        message = f"channels named, {channel_name.strip(',')}: {count}\n"
        if char_count + len(total_message) + len(message) >= 2000:
            total_message += "```**"
            await ctx.send(total_message)
            total_message = "**```js\n"
            char_count = 0
        total_message += message
        char_count += len(message)
    total_message += "```**"
    await ctx.send(total_message)

@client.command()
async def tz_setup(ctx, location1: str, location2: str):
    guild_id = str(ctx.guild.id)
    if guild_id not in timezone_config:
        timezone_config[guild_id] = {}
    timezone_config[guild_id]["channel_id"] = ctx.channel.id
    timezone_config[guild_id]["location1"] = location1
    timezone_config[guild_id]["location2"] = location2
    timezone_config[guild_id]["last_location"] = "location2"
    save_timezone_config()
    await ctx.send(f"Timezone ping configured:\nLocation 1: {location1}\nLocation 2: {location2}\nChannel: {ctx.channel.mention}")

@client.command()
async def tz_enable(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id not in timezone_config:
        await ctx.send("Please use `.tz_setup <location1> <location2>` first.")
        return
    timezone_config[guild_id]["enabled"] = True
    save_timezone_config()
    await ctx.send("Timezone ping enabled. Will send messages every 12 hours.")

@client.command()
async def tz_disable(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id not in timezone_config:
        await ctx.send("No timezone configuration found.")
        return
    timezone_config[guild_id]["enabled"] = False
    save_timezone_config()
    await ctx.send("Timezone ping disabled.")

@client.command()
async def tz_status(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id not in timezone_config:
        await ctx.send("No timezone configuration found.")
        return
    guild_data = timezone_config[guild_id]
    channel = client.get_channel(guild_data.get("channel_id"))
    enabled = guild_data.get("enabled", False)
    location1 = guild_data.get("location1", "Not set")
    location2 = guild_data.get("location2", "Not set")
    last_location = guild_data.get("last_location", "None")
    start_time = guild_data.get("start_time", "Not set")
    status_msg = f"**Timezone Ping Status:**\n"
    status_msg += f"Enabled: {enabled}\n"
    status_msg += f"Channel: {channel.mention if channel else 'Unknown'}\n"
    status_msg += f"Location 1: {location1}\n"
    status_msg += f"Location 2: {location2}\n"
    status_msg += f"Last sent: {last_location}\n"
    status_msg += f"Start time: {start_time}\n"
    await ctx.send(status_msg)

@client.command()
async def tz_time(ctx, hour: int, minute: int = 0):
    if not (0 <= hour <= 23):
        await ctx.send("Hour must be between 0 and 23.")
        return
    if not (0 <= minute <= 59):
        await ctx.send("Minute must be between 0 and 59.")
        return
    guild_id = str(ctx.guild.id)
    if guild_id not in timezone_config:
        await ctx.send("Please use `.tz_setup <location1> <location2>` first.")
        return
    timezone_config[guild_id]["start_time"] = f"{hour:02d}:{minute:02d}"
    save_timezone_config()
    await ctx.send(f"Timezone ping will start at {hour:02d}:{minute:02d} UTC and repeat every 12 hours.")

@client.command()
async def delete_category(ctx, *, category_name: str):
    category = discord.utils.get(ctx.guild.categories, name=category_name)
    if not category:
        await ctx.send(f"Category '{category_name}' not found.")
        return
    channel_count = len(category.channels)
    confirm_msg = await ctx.send(
        f"Are you sure you want to delete the category '{category_name}' and all {channel_count} channels inside it?\n"
        f"React with ✅ to confirm or ❌ to cancel. (30s timeout)"
    )
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
    try:
        reaction, user = await client.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "❌":
            await ctx.send("Category deletion cancelled.")
            return
        if str(reaction.emoji) == "✅":
            status_msg = await ctx.send(f"Deleting {channel_count} channels from category '{category_name}'...")
            for channel in category.channels:
                try:
                    await channel.delete()
                    await asyncio.sleep(1)
                except discord.Forbidden:
                    await ctx.send(f"Missing permissions to delete {channel.name}")
                except discord.HTTPException as e:
                    await ctx.send(f"Failed to delete {channel.name}: {e}")
                    await asyncio.sleep(2)
            try:
                await category.delete()
                await status_msg.edit(content=f"Successfully deleted category '{category_name}' and all its channels.")
            except discord.Forbidden:
                await ctx.send(f"Missing permissions to delete category '{category_name}'")
            except discord.HTTPException as e:
                await ctx.send(f"Failed to delete category: {e}")
    except asyncio.TimeoutError:
        await ctx.send("Confirmation timed out. Category deletion cancelled.")

@client.command()
async def delete_all(ctx, *, channel_name: str):
    matching_channels = [
        channel for channel in ctx.guild.channels
        if isinstance(channel, discord.TextChannel) and channel.name.lower() == channel_name.lower()
    ]
    if not matching_channels:
        await ctx.send(f"No channels named '{channel_name}' found.")
        return
    channel_count = len(matching_channels)
    confirm_msg = await ctx.send(
        f"Found {channel_count} channels named '{channel_name}' across all categories.\n"
        f"Are you sure you want to delete all of them?\n"
        f"React with ✅ to confirm or ❌ to cancel. (30s timeout)"
    )
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
    try:
        reaction, user = await client.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "❌":
            await ctx.send("Bulk channel deletion cancelled.")
            return
        if str(reaction.emoji) == "✅":
            status_msg = await ctx.send(f"Deleting {channel_count} channels named '{channel_name}'...")
            deleted_count = 0
            failed_count = 0
            for channel in matching_channels:
                try:
                    await channel.delete()
                    deleted_count += 1
                    await asyncio.sleep(3)
                except discord.Forbidden:
                    await ctx.send(f"Missing permissions to delete {channel.mention}")
                    failed_count += 1
                    await asyncio.sleep(1)
                except discord.HTTPException as e:
                    await ctx.send(f"Failed to delete {channel.name}: {e}")
                    failed_count += 1
                    await asyncio.sleep(2)
            await status_msg.edit(
                content=f"Deletion complete.\nDeleted: {deleted_count}\nFailed: {failed_count}"
            )
    except asyncio.TimeoutError:
        await ctx.send("Confirmation timed out. Bulk channel deletion cancelled.")

@client.command()
async def cmd(ctx):
    help_message = (
        "**Command List:**\n\n"
        "`.say [message]` - Make the bot say a message\n"
        "`.start` - Start the spammer\n"
        "`.stop` - Stop the spammer\n"
        "`.delete` - Delete the current channel\n"
        "`.move [new_category_name]` - Move the current channel to a new category\n"
        "`.sync_all [category_name]` - Sync permissions for all channels in a category\n"
        "`.cat [name]` - Create a new category\n"
        "`.move_channels [channel_name] [category_name]` - Move channels to a specified category\n"
        "`.rename [new_name]` - Rename the current channel\n"
        "`.count_channels` - Count the number of text channels, voice channels, and categories\n"
        "`.list_channels` - List all text channels and their counts\n"
        "`.pokemon [channel_names]` - Count and display channels matching the given names\n"
        "`.tz_setup [location1] [location2]` - Configure timezone ping locations\n"
        "`.tz_time [hour] [minute]` - Set the time when timezone pings start (UTC)\n"
        "`.tz_enable` - Enable automatic timezone pings every 12 hours\n"
        "`.tz_disable` - Disable automatic timezone pings\n"
        "`.tz_status` - Check timezone ping configuration and status\n"
        "`.delete_category [category_name]` - Delete a category and all its channels\n"
        "`.delete_all [channel_name]` - Delete all channels with the specified name\n"
    )
    await ctx.send(help_message)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Invalid command. Use `.cmd` or `.help` for the list of available commands.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required permissions to execute this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument. Use `.cmd` or `.help` for command syntax.")
    else:
        await ctx.send(f"An error occurred: {error}")

client.run(user_token)