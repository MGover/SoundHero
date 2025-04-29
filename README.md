# SoundHero
Ever wanted to play a sound on discord but you hit the upload sound limit?
Or maybe you thought it'd be funny to have a door-bell sound play everytime you enter the voice channel?
Well look no further, because this is the bot for you!
This bot interfaces with an online database of sounds and allows you to choose sounds to play at command, or schedule to play when you enter or join a voice channel
Continue reading for info on how you can host and get started!

## Features
- Play sounds on command
- Schedule sounds for when you leave or join a channel
- Stream audio from youtube via youtube links
- Steam youtube playlists

## Requirements
- [FFMpeg](https://www.ffmpeg.org/)
- [Python](https://www.python.org/)
- [A Discord Bot](https://discord.com/developers/applications)

## Python Dependences
Open up your OS Terminal and PIP Install the following libraries:
```
pip install discord
pip install requests
pip install dotenv
pip install python-dotenv
```

(TODO: Add these into a python environment)

## Installation
1. Clone this repo. Run the following in your OS Terminal:
   
   ```
   git clone https://github.com/MGover/SoundHero.git
   ```

5. Configure Environment Variables
   - There is a single .envexample file. Fill the values in as shown farther below this page. Then rename to file .env
   - See below on how to configure these values
  
## Usage
Run the following in the project root:

```
python sound-hero.py
```

If you get "Logged in as <BotNameHere> then you got everything right so far

## Commands
|Command|Description|
|---------|---------|
|/setsound <soundtype> <soundname>| Set a soundtype (exit or enter) sound that will play when you enter or exit a discord voice channel|
|/playsound <searchterm>| Provide a searchterm to the online sound database. Listen to that sound immediately|
|/checksound <user>| Check the sound attached to a user in the server|
|/clearsound <soundtype>| Remove an attached sound of soundtype (enter or exit) from yourself|
|/join| tell the bot to join your current voice channel|
|/leave| boot the bot out of it's current voice channel|
|/play <url>| stream audio in your current voice channel, provide a a YouTube video or playlist URL|
|/skip| skip the current song in the playlist (if one is playing)|
|/search| stream audio in your current voice channel, provide a search term to query YouTube|
|/stop| tell the bot to stop streaming audio immediately|
|/help| prints a help message of these commands available|

## Configuration
Reanme .env.example file to .env

/./.env

```
  DISCORD_BOT_TOKEN = "xxxxxxxxxxxxxxxxxsecretxxxxxxxxxxx"
  MAX_PLAY_DURATION = 3   // I like to keep this short because long sounds are annoying

  // DO NOT MESS WITH THESE UNLESS YOU UNDERSTAND THE CODE IN THIS REPO
  API_URL = "https://www.myinstants.com"
  FFMPEG_OPTS = {'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}
  YTDL_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # Bind to IPv4 since IPv6 addresses cause issues sometimes
    'extract_flat': True,  # Ensures we get URLs from playlists
    'playlistend': 20  # Limit to 20 videos (change as needed)
}
  
```

DISCORD_BOT_TOKEN is the token from your OFFICIAL discord bot. This bot needs [application.commands permission](https://discord.com/developers/docs/topics/permissions) for the slash commands to work. 

MAX_PLAY_DURATION is the length sounds will play for.

API_URL is the url to access the online sounds database. This shouldn't be changed unless you know how to fix the python code for it. This repo is only configured to work with the API provided by myinstants

FFMPEG_OPTS is a way to change the options used to configure the FFMPEG library. FFMPEG is used to play the audio.

YTDL_OPTS is a way to change the options used to confige YTDL. YTDL is a library for streaming YouTube audio

- Pull Requests are encouraged. So are Issues. If you see improvements that can be made, point it out.
  
