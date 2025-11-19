import discord
import sqlite3
import os
from discord import FFmpegPCMAudio
from discord import app_commands
import asyncio
import requests
import json
import re
import yt_dlp as youtube_dl
import parser
from pathlib import Path
from collections import deque
from youtubesearchpython import VideosSearch, Suggestions
from dotenv import load_dotenv # type: ignore

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAX_PLAY_DURATION = int(os.getenv("MAX_PLAY_DURATION"))  # Maximum playback duration in seconds
SOUND_FOLDER = "sounds/"  # Folder where MP3 files are stored
API_URL = os.getenv("API_URL")
API_JSON_RETURN = {}
GLOBAL_LIST = []

# Database setup for storing user sound settings
conn = sqlite3.connect("soundboard_sounds.db")
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS sounds (
        user_id INTEGER PRIMARY KEY,
        join_sound TEXT,
        leave_sound TEXT
    )
""")
conn.commit()

# youtube stuff
# Ensure ffmpeg is installed and accessible
FFMPEG_OPTIONS = os.getenv("FFMPEG_OPTS")

# Options for yt-dlp
ytdl_format_options = os.getenv("YTDL_FORMAT_OPTS")
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
audio_queue = deque()  # Stores queued songs

async def play_next(voice_client):
    """Plays the next song in the queue."""
    if audio_queue:
        next_audio = audio_queue.popleft()
        voice_client.play(next_audio, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(voice_client), bot.loop))
    else:
        await voice_client.disconnect()  # Leave voice if queue is empty

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)
    
    @classmethod
    async def from_search_term(cls, query, *, loop=None, stream=True):
        # Perform the search
        videos_search = VideosSearch(query, limit=1)
        results = videos_search.result()

        link = results['result'][0]['link']
        print(f"Link found at {link}")
        return await cls.from_url(url=link, loop=loop, stream=stream)
    
    @classmethod
    async def get_urls(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        for entry in data['entries']:
            GLOBAL_LIST.append(entry["url"])

def log(data):
    with open("log.txt", "a") as f:
        f.write(str(data))

def search_youtube(query, max_results=20):
    # Perform the search
    suggestions = Suggestions(language='en', region='US')
    videos = suggestions.get(query)['result']
    return videos

# Bot setup
intents = discord.Intents.all()
intents.voice_states = True
intents.messages = True
intents.guilds = True
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

def sanitize_filename(filename):
    """
    Sanitizes a filename to make it compatible with Linux filesystems.

    :param filename: The original filename.
    :return: A sanitized filename.
    """
    # Replace invalid characters with an underscore (_)
    sanitized = re.sub(r'[\/\0<>:"|?*\n\r\t]', '_', filename)

    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    
    # Remove leading/trailing spaces and dots (not allowed as filenames)
    sanitized = sanitized.strip('. ')
    
    # Replace multiple consecutive underscores with a single one
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Ensure the filename is not empty
    if not sanitized:
        sanitized = "unnamed_file"
    
    return sanitized

def get_available_sounds(search_term):
    """Returns a list of sound names from API_URL"""
    API_JSON_RETURN = json.loads(parser.search(search_term))
    return [sound['name'] for sound in API_JSON_RETURN if sound['name']][:24]

def get_user_sounds(user_id):
    c.execute("SELECT join_sound, leave_sound FROM sounds WHERE user_id=?", (user_id,))
    return c.fetchone()

def set_user_sounds(user_id, join_sound, leave_sound):
    c.execute("INSERT INTO sounds (user_id, join_sound, leave_sound) VALUES (?, ?, ?) \
               ON CONFLICT(user_id) DO UPDATE SET join_sound=?, leave_sound= ?", 
               (user_id, join_sound, leave_sound, join_sound, leave_sound))
    conn.commit()

def clear_user_sound(user_id, sound_type):
    if sound_type == "join":
        c.execute("UPDATE sounds SET join_sound=NULL WHERE user_id=?", (user_id,))
    elif sound_type == "leave":
        c.execute("UPDATE sounds SET leave_sound=NULL WHERE user_id=?", (user_id,))
    conn.commit()

async def play_sound(vc, sound_name, duration=MAX_PLAY_DURATION):
    """Plays an MP3 file from the sounds/ folder."""
    if vc.is_playing():
        vc.stop()
    sound_name = sanitize_filename(sound_name)
    file_path = os.path.join(SOUND_FOLDER, f"{sound_name}.mp3")
    if os.path.exists(file_path):
        vc.play(FFmpegPCMAudio(file_path), after=lambda e: print(f"Finished playing {sound_name}"))
        await asyncio.sleep(duration)
        if vc.is_playing():
            vc.stop()
    else:
        print(f"File not found: {file_path}")

async def play_yt_sound(vc, player):
    if vc.is_playing():
        vc.stop()
    vc.play(player, after=lambda e: print(f'Done playing: {player.title}'))

def get_sound_url(sound_name):
    """Search GLOBAL BASE URL for sound_name. Returns"""
    API_JSON_RETURN = json.loads(parser.search(sound_name))
    return [sound["url"][sound["url"].find('/'):sound["url"].find('\'')] for sound in API_JSON_RETURN if sound["name"] == sound_name][0]

# Purge unused sounds (run from host machine only)
def purge_unused_sounds():
    used_sounds = set()
    c.execute("SELECT join_sound, leave_sound FROM sounds")
    for row in c.fetchall():
        used_sounds.update(filter(None, row))

    unused_sounds = set([file.stem for file in Path(SOUND_FOLDER).iterdir() if file.is_file()])
    for sound in used_sounds:
        sound = sanitize_filename(sound)
        unused_sounds.remove(sound)

    for sound in unused_sounds:
        file_path = os.path.join(SOUND_FOLDER, f"{sound}.mp3")
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted unused sound: {sound}")

def download_sound(sound_url, sound_name):
    """"Downloads the sound from sound_url"""
    try:
        # Send a GET request to the URL
        sound_name = sanitize_filename(sound_name)
        sound_url = API_URL + sound_url
        response = requests.get(sound_url, stream=True)
        response.raise_for_status()  # Raise an error for bad status codes (4xx or 5xx)
        file_path = os.path.join(SOUND_FOLDER, f"{sound_name}.mp3")

        # Write the content to the file
        os.makedirs(os.path.dirname(SOUND_FOLDER), exist_ok=True)
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        print(f"File downloaded successfully and saved to: {file_path}")

    except requests.exceptions.RequestException as e:
        print(f"Failed to download the file: {e}")

def users_with_sounds_in_vc(vc):
    for member in vc.channel.members:
        if not member.bot:
            user_sounds = get_user_sounds(member.id)
            if user_sounds and (user_sounds[0] or user_sounds[1]):
                return True
    return False

#autocomplete functions
async def sound_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=s, value=s) for s in get_available_sounds(current.lower()) if current.lower() in s.lower()]
async def soundtype_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=s, value=s) for s in ["leave", "join"] if current.lower() in s.lower()]
async def search_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=s, value=s) for s in search_youtube(current.lower()) if current.lower() in s.lower()]

# Slash Commands
@tree.command(name="playsound", description="Play a sound in your voice channel.")
@app_commands.describe(sound_name="The name of the sound to play.")
@app_commands.autocomplete(sound_name=sound_autocomplete)
async def playsound(interaction: discord.Interaction, sound_name: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You need to be in a voice channel!", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    bot_vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if not bot_vc:
        bot_vc = await channel.connect()
    elif bot_vc.channel != channel:
        await bot_vc.move_to(channel)

    sound_url = get_sound_url(sound_name)
    download_sound(sound_url, sound_name)
    await interaction.response.send_message(f"🔊 Playing `{sound_name}`!", ephemeral=True)
    await play_sound(bot_vc, sound_name, 15)
    purge_unused_sounds()

@tree.command(name="setsound", description="Set a leave or join sound for yourself")
@app_commands.describe(sound_type="Join or Leave sound specification")
@app_commands.describe(sound_name="The name of the sound to play.")
@app_commands.autocomplete(sound_type=soundtype_autocomplete)
@app_commands.autocomplete(sound_name=sound_autocomplete)
async def setsound(interaction: discord.Interaction, sound_type: str, sound_name: str):
    """Assign a soundboard sound as your join/leave sound."""
    available_sounds = get_available_sounds(sound_name)
    if sound_name not in available_sounds:
        await interaction.response.send_message(f"❌ Sound `{sound_name}` not found! Available sounds: {', '.join(available_sounds)}", ephemeral=True)
        return
    
    if ((sound_type != "join") and (sound_type != "leave")):
        await interaction.response.send_message("❌Invalid type! Use `join` or `leave`.", ephemeral=True)
        return
    await interaction.response.send_message(f"✅ Set yor {sound_type} sound to {sound_name}!", ephemeral=True)
    user_id = interaction.user.id
    user_sounds = get_user_sounds(user_id) or (None, None)

    sound_url = get_sound_url(sound_name)
    download_sound(sound_url, sound_name)

    if sound_type == "join":
        set_user_sounds(user_id, sound_name, user_sounds[1])
    elif sound_type == "leave":
        set_user_sounds(user_id, user_sounds[0], sound_name)
    purge_unused_sounds()

@tree.command(name="checksound", description="Check what sounds you or someone else are using")
@app_commands.describe(member="@ a user")
async def checksound(interaction: discord.Interaction, member: discord.Member = None):
    """Check the join/leave sound of a user."""
    member = member or interaction.user.id
    user_sounds = get_user_sounds(member.id)

    if user_sounds:
        join_sound = user_sounds[0] or "None"
        leave_sound = user_sounds[1] or "None"
        await interaction.response.send_message(f"{member.mention}'s sounds:\n- **Join**: {join_sound}\n- **Leave**: {leave_sound}", ephemeral=True)
    else:
        await interaction.response.send_message(f"{member.mention} has no assigned sounds.", ephemeral=True)

@tree.command(name="clearsound", description="Clear tied join or leave sound for current user")
@app_commands.describe(sound_type="Specify whether to clear join or leave sound")
@app_commands.autocomplete(sound_type=soundtype_autocomplete)
async def clearsound(interaction: discord.Interaction, sound_type: str):
    if sound_type not in ["join", "leave"]:
        await interaction.response.send_message("❌ Invalid sound type. Choose 'join' or 'leave'.", ephemeral=True)
        return

    clear_user_sound(interaction.user.id, sound_type)
    await interaction.response.send_message(f"✅ Cleared {sound_type} sound for {interaction.user.display_name}.", ephemeral=True)
    purge_unused_sounds()

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # Ignore mute/unmute and deafen/undeafen events
    if (before.channel == after.channel) and (before.self_mute != after.self_mute or before.self_deaf != after.self_deaf or before.self_video != after.self_video or before.self_stream != after.self_stream):
        return  # Ignore self-mute/unmute changes
    
    
    guild_id = member.guild.id
    guild = bot.get_guild(guild_id)
    if not guild:
        return
    
    user_sounds = get_user_sounds(member.id) or (None, None)
    join_sound = user_sounds[0]
    leave_sound = user_sounds[1]

    if join_sound or leave_sound:
        voice_channel = after.channel if after.channel else before.channel
        if not voice_channel:
            return
        bot_vc = discord.utils.get(bot.voice_clients, guild=guild)

    if (not join_sound and leave_sound) and not user_sounds:
        return
    
    if after.channel and not bot_vc:  # Someone joined, bot not in VC
        print("joining vc")
        vc = await after.channel.connect()
        if join_sound:
            await play_sound(vc, join_sound)
    elif after.channel and bot_vc and bot_vc.channel != after.channel:
        print("moving vc's")
        await bot_vc.move_to(after.channel)
        if join_sound:
            await play_sound(bot_vc, join_sound)
    elif ((after.channel) and (bot_vc.channel == after.channel)): #someone joined, bot is already in that channel
        print("already in vc")
        if join_sound:
            await play_sound(bot_vc, join_sound)

    if before.channel and not after.channel:  # Someone left
        if not bot_vc:
            bot_vc = await before.channel.connect()
        if leave_sound:
            await play_sound(bot_vc, leave_sound)
        if bot_vc and not users_with_sounds_in_vc(bot_vc):  # Only bot left
            await bot_vc.disconnect()

@tree.command(name="join", description="Bot will join the current user's VC")
async def join(interaction: discord.Interaction):
    print("Join command triggered")
    """Command to make the bot join the user's voice channel."""
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        await channel.connect()
        await interaction.response.send_message("🔊 Joined voice channel!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ You need to be in a voice channel", ephemeral=True)

@tree.command(name="leave", description="Leaves the user's current VC")
async def leave(interaction: discord.Interaction):
    """Command to make the bot leave the voice channel."""
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Left the voice channel!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ I' not in a voice channel!", ephermal=True)

@tree.command(name='play', description='Plays audio from a YouTube URL')
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        return
    
    channel = interaction.user.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    if 'playlist' in url:
        await interaction.response.send_message(f'Loading playlist....', ephemeral=False)
        if not voice_client:
            voice_client = await channel.connect()

        await YTDLSource.get_urls(url)
        for curr_url in urls:
            player = await YTDLSource.from_url(curr_url, loop=bot.loop, stream=True)
            await interaction.followup.send(f'Now playing: {player.title}')
            await play_yt_sound(voice_client, player)
        return

    global GLOBAL_LIST 
    GLOBAL_LIST = []
    player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
    await interaction.response.send_message(f'Now playing: {player.title}', ephemeral=False)
    
    if not voice_client:
        voice_client = await channel.connect()

    await play_yt_sound(voice_client, player)

@tree.command(name='search', description='Search for a youtube video and play the audio')
@app_commands.describe(video_name="Search term to find video")
@app_commands.autocomplete(video_name=search_autocomplete)
async def search(interaction: discord.Interaction, video_name: str):
    if not interaction.user.voice:
        await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        return
    
    await interaction.response.send_message(f'Now playing: {video_name}', ephemeral=False)
    
    channel = interaction.user.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    player = await YTDLSource.from_search_term(query=video_name, loop=bot.loop, stream=True)
    
    if not voice_client:
        voice_client = await channel.connect()

    if isinstance(player, list):
        audio_queue.extend(player)
        play_next(voice_client)
        return

    await play_yt_sound(voice_client, player)

@tree.command(name='stop', description='Stops the current audio and disconnects')
async def stop(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message("Disconnected from voice channel.", ephemeral=True)
    else:
        await interaction.response.send_message("I'm not in a voice channel!", ephemeral=True)

# Help Command
@tree.command(name="help", description="Show available bot commands.")
async def help(interaction: discord.Interaction):
    print("This command was triggered")
    help_text = (
        "📜 **Bot Commands:**\n"
        "`/join` - Make the bot join your current voice channel.\n"
        "`/leave` - Make the bot leave the current voice channel.\n"
        "`/playsound <sound_name>` - Play a specific sound in your voice channel.\n"
        "`/setsound <join/leave> <sound_name>` - Attach a join or leave sound to your account\n"
        "`/checksound <@user>` - See what sounds are already attached to an account\n"
        "`/clearsound <join/leave>` - Remove the join or leave sound for yourself\n"
        "`/play <url> - Start streaming audio from a YouTube URL. Video or playlist\n"
        "`/skip - Skip current playlist audio item if any\n"
        "`/search <searchterm> - Query YouTube with your searchterm and stream the audio from the result\n"
        "`/stop - Stop playing the currently streaming audio immediately"
        "`/help` - Display this help message."
    )
    await interaction.response.send_message(help_text, ephemeral=True)

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("❌ Command not found. Use `/help` to see available commands.", ephemeral=True)
    elif isinstance(error, app_commands.MissingRequiredArgument):
        await interaction.response.send_message("❌ Missing arguments. Check the command usage with `/help`.", ephemeral=True)
    elif isinstance(error, app_commands.BadArgument):
        await interaction.response.send_message("❌ Invalid argument provided. Please check your input.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ An unexpected error occurred: {str(error)}", ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    x = await tree.fetch_commands()
    print(f"Commands found: {x}")
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)
