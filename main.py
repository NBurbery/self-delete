import re
import os
import asyncio
import random
import string
import discord
print(discord.__version__)
import time
from discord.ext import commands, tasks

user_token = os.environ['token']
spam_id = os.environ['spam_id']
version = 'v2.1'
prefix = "."

P2Assistant = 854233015475109888
poketwo = 716390085896962058
Pokename = 874910942490677270
authorized_ids = [Pokename, poketwo, P2Assistant]
client = commands.Bot(command_prefix=prefix)
intervals = [3.6, 2.8, 3.0, 3.2, 3.4]

@client.event
async def on_ready():
    print(f'*'*30)
    print(f'Logged in as {client.user.name} ✅:')
    print(f'With ID: {client.user.id}')
    print(f'*'*30)
    print(f'Poketwo Auto Collection {version}')
    print(f'Created by PlayHard')
    print(f'*'*30)

@tasks.loop(seconds=random.choice(intervals))
async def spam():
    channel = client.get_channel(int(spam_id))
    message_content = ''.join(random.sample(['1','2','3','4','5','6','7','8','9','0'], 7) * 5)
    try:
        await channel.send(message_content)
    except discord.errors.HTTPException as e:
        if e.status == 429:  # Check if it's a rate limit error
            print(f"Rate limit exceeded. Waiting and retrying...")
            await asyncio.sleep(5)  # Wait for 5 seconds before retrying
            await spam()  # Retry sending the message
        else:
            print(f"Error sending message: {e}. Retrying in 60 seconds...")
            await asyncio.sleep(60)  # Wait for 60 seconds before retrying
            await spam()  # Retry sending the message
    except discord.errors.DiscordServerError as e:
        print(f"Error sending message: {e}. Retrying in 60 seconds...")
        await asyncio.sleep(60)  # Wait for 60 seconds before the first retry
        print(f"Retrying...")
        await spam_recursive(channel, message_content, 1)

async def spam_recursive(channel, message_content, attempt):
    if attempt <= 3:  # Maximum 3 attempts
        try:
            await channel.send(message_content)
        except discord.errors.DiscordServerError as e:
            print(f"Attempt {attempt} failed. Error: {e}. Retrying in {60 * 2 ** (attempt - 1)} seconds...")
            await asyncio.sleep(60 * 2 ** (attempt - 1))  # Exponential backoff
            await spam_recursive(channel, message_content, attempt + 1)
    else:
        print("All attempts failed. Giving up.")
    
@spam.before_loop
async def before_spam():
    await client.wait_until_ready()
spam.start()

def solve(message, file_name):
    hint = []
    for i in range(15, len(message) - 1):
        if message[i] != '\\':
            hint.append(message[i])
    hint_string = ''
    for i in hint:
        hint_string += i
    hint_replaced = hint_string.replace('_', '.')
    with open(f"{file_name}", "r") as f:
        solutions = f.read()
    solution = re.findall('^' + hint_replaced + '$', solutions, re.MULTILINE)
    if len(solution) == 0:
        return None
    return solution

@client.event
async def on_message(message):
    channel = client.get_channel(message.channel.id)
    
    # Logic for Pokename
    if message.author.id == Pokename or message.author.id == P2Assistant:
        content = message.content
        
        if channel.category and channel.category.name.lower() == "spawn channels":
            if 'Rare Ping' in content or 'Rare ping' in content:
                await message.channel.send('<@716390085896962058> h')
                return
            
            elif 'Regional Ping' in content or 'Regional ping' in content:
                await message.channel.send(f'<@716390085896962058> h')
                return

            elif 'Collection Pings' in content and "@" in content or 'Collection pings' in content and "@" in content:
                await message.channel.send(f'<@716390085896962058> h')
                return 

            elif 'Shiny Hunt Pings' in content or 'Shiny hunt pings' in content:
                await message.channel.send(f'<@716390085896962058> h')     
                return

    else:
        content = message.content
        solution = None

    if 'The pokémon is ' in content: ##event pokemon
        solution = solve(content, 'event.txt') 
        if solution:
                await channel.clone()
                category_name = 'Event 1'
                new_category = discord.utils.get(message.guild.categories, name=category_name)
                if new_category is None:
                    new_category = await message.guild.create_category(category_name)
                print(f"In Server:{channel.guild.name} category:{category_name} have {len(new_category.channels)} now! 🎉")
                if len(new_category.channels) <= 48:
                    print(f"{category_name} category is not full. Adding to {new_category.name}.")
                    await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category)
                else:
                    for i in range(2, 100):  # Assuming the maximum category number won't exceed 100
                        next_category_name = f"Event {i}"
                        new_category = discord.utils.get(message.guild.categories, name=next_category_name)
                        if new_category is None:
                            new_category = await message.guild.create_category(next_category_name)
                            print(f"Created new category: {next_category_name}")
                            break

                        if len(new_category.channels) < 50:
                            print(f"Using existing category: {next_category_name}")
                            break

                    if new_category:
                        await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category)
                    else:
                        print("No available category found.")
                await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 7 8 9 10')
                await asyncio.sleep(1)
                await channel.edit(sync_permissions=True)

        if not solution: ##collection pokemon
            solution = solve(content, 'collection.txt')
            if solution:
                await channel.clone()
                category_name = 'Collection 1'
                new_category = discord.utils.get(message.guild.categories, name=category_name)
                if new_category is None:
                    new_category = await message.guild.create_category(category_name)
                print(f"In Server:{channel.guild.name} category:{category_name} have {len(new_category.channels)} now! 🟢")
                if len(new_category.channels) <= 48:
                    print(f"{category_name} category is not full. Adding to {new_category.name}.")
                    await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category)
                else:
                    for i in range(2, 100):  # Assuming the maximum category number won't exceed 100
                        next_category_name = f"Collection {i}"
                        new_category = discord.utils.get(message.guild.categories, name=next_category_name)
                        if new_category is None:
                            new_category = await message.guild.create_category(next_category_name)
                            print(f"Created new category: {next_category_name}")
                            break

                        if len(new_category.channels) < 50:
                            print(f"Using existing category: {next_category_name}")
                            break

                    if new_category:
                        await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category)
                    else:
                        print("No available category found.")
                await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 7 8 9 10')
                await asyncio.sleep(1)
                await channel.edit(sync_permissions=True)
       
        if not solution: ##rare pokemon
            solution = solve(content, 'rare.txt')
            if solution:
                await channel.clone()
                category_name = 'Rare 1'
                new_category = discord.utils.get(message.guild.categories, name=category_name)
                if new_category is None:
                    new_category = await message.guild.create_category(category_name)
                print(f"In Server:{channel.guild.name} category:{category_name} have {len(new_category.channels)} now! 🟠")
                if len(new_category.channels) <= 48:
                    print(f"{category_name} category is not full. Adding to {new_category.name}.")
                    await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category)
                else:
                    for i in range(2, 100):  # Assuming the maximum category number won't exceed 100
                        next_category_name = f"Rare {i}"
                        new_category = discord.utils.get(message.guild.categories, name=next_category_name)
                        if new_category is None:
                            new_category = await message.guild.create_category(next_category_name)
                            print(f"Created new category: {next_category_name}")
                            break

                        if len(new_category.channels) < 50:
                            print(f"Using existing category: {next_category_name}")
                            break

                    if new_category:
                        await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category)
                    else:
                        print("No available category found.")
                await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 7 8 9 10')
                await asyncio.sleep(1)
                await channel.edit(sync_permissions=True)
                    
        if not solution: ##regional pokemon
            solution = solve(content, 'regional.txt')
            if solution:
                await channel.clone()
                category_name = 'Regional 1'
                new_category = discord.utils.get(message.guild.categories, name=category_name)
                if new_category is None:
                    new_category = await message.guild.create_category(category_name)
                print(f"In Server:{channel.guild.name} category:{category_name} have {len(new_category.channels)} now! 🔵")
                if len(new_category.channels) <= 48:
                    print(f"{category_name} category is not full. Adding to {new_category.name}.")
                    await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category)
                else:
                    for i in range(2, 100):  # Assuming the maximum category number won't exceed 100
                        next_category_name = f"Regional {i}"
                        new_category = discord.utils.get(message.guild.categories, name=next_category_name)
                        if new_category is None:
                            new_category = await message.guild.create_category(next_category_name)
                            print(f"Created new category: {next_category_name}")
                            break

                        if len(new_category.channels) < 50:
                            print(f"Using existing category: {next_category_name}")
                            break

                    if new_category:
                        await channel.edit(name=solution[0].lower().replace(' ', '-'), category=new_category)
                    else:
                        print("No available category found.")
                await channel.send(f'<@716390085896962058> redirect 1 2 3 4 5 6 7 8 9 10')
                await asyncio.sleep(1)
                await channel.edit(sync_permissions=True)
    
            if not solution:  ## normal pokemon
                solution = solve(content, 'pokemon.txt')
                if solution:
                    # await message.channel.send(f'c {solution[0]}
                    await asyncio.sleep(1)
        
    # auto delete caught pokemon
    if message.author.id == poketwo:
        content = message.content
        
        if 'These colors seem unusual...' not in content and 'Congratulations' in content:
            channel = message.channel
            # blacklist add categories to the blacklist so channel dont get deleted "spawn channels"
            if channel.category and channel.category.name.lower() == "spawn channels":
                print("Channel not deleted (blacklisted category).")
            else:
                try:
                    current_time = time.time()
                    future_time = current_time + 15
                    countdown_message = await channel.send(f'This channel will be deleted <t:{int(future_time)}:R>')
                    await asyncio.sleep(15)
                    await channel.delete()
                    print("Channel deleted.")
                except discord.errors.NotFound:
                    print("Channel not found or inaccessible.")
        elif 'These colors seem unusual...' in content:
            print("Shiny pokemon detected.")
            await message.channel.send("Shiny Pokemon detected.")


    if not message.author.bot:
       await client.process_commands(message)

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
        await asyncio.sleep(1)  # Adjust the sleep time according to your needs
    
    await ctx.send(f"**```js\nAll channels in category '{category_name}' have been synced.```**\n")

@sync_all.error
async def sync_all_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required permissions to sync channels.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide the name of the category.")
    else:
        await ctx.send(f"An error occurred: {error}")

@client.command()#Creates a new category 
async def cat(ctx, *, name):
    await ctx.guild.create_category(name)
    await ctx.send("successfully created")

@client.command()
async def move_channels(ctx, channel_name, category_name):
    guild = ctx.guild

    # Get the category by name
    category = discord.utils.get(guild.categories, name=category_name)

    if category:
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel) and channel.name == channel_name:
                if channel.category != category:  # Check if channel is not already in the specified category
                    await channel.edit(category=category)
                    print(f'Moved channel "{channel_name}" to the category "{category_name}".')
                    await asyncio.sleep(1)  # Add a 1-second delay
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
async def count_channels(ctx):
    text_channels = sum(1 for channel in ctx.guild.channels if isinstance(channel, discord.TextChannel))
    voice_channels = sum(1 for channel in ctx.guild.channels if isinstance(channel, discord.VoiceChannel))
    category_channels = sum(1 for channel in ctx.guild.channels if isinstance(channel, discord.CategoryChannel))
    
    await ctx.send(f"Text Channels: {text_channels}\nVoice Channels: {voice_channels}\nCategories: {category_channels}")

@client.command()
async def list_channels(ctx):
    channel_counts = {}
    blacklist_category_name = "Spawn Channels"  # Adjust this to the name of your blacklist category
    
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
        # Check if adding the message exceeds 2000 characters
        if char_count + len(total_message) + len(message) >= 2000:
            total_message += "```**"
            await ctx.send(total_message)
            total_message = "**```js\n"
            char_count = 0
        
        total_message += message
        char_count += len(message)
    
    total_message += "```**"
    
    await ctx.send(total_message)

@client.remove_command('help')  # Remove the built-in help command

# Create a Help command
@client.command()
@commands.has_permissions(manage_channels=True)
async def help(ctx):
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
        "`.count_channels` - Count the number of text channels, voice channels, and categories in the server\n"
        "`.list_channels` - List all text channels and their counts (excluding the blacklist category)\n"
        "`.pokemon [channel_names]` - Count and display channels matching the given names\n"
    )
    await ctx.send(help_message)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Invalid command. Use `!help` for the list of available commands.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required permissions to execute this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument. Use `.help` for command syntax.")
    else:
        await ctx.send(f"An error occurred: {error}")

client.run(user_token)