import asyncio
import os
import re
import json
from typing import Any, Dict, Optional
import dotenv
import disnake
import yt_dlp as youtube_dl
from disnake.ext import commands
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
dotenv.load_dotenv()

youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Load stored track URLs
with open("data.json", "r") as file:
    store_track_urls = json.load(file)

# Initialize Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="playlist-read-private"
))

def clean_string(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def get_youtube_url(track_name):
    search_query = f"ytsearch:{track_name} official audio"
    ydl_opts = {"quiet": True, "default_search": "ytsearch", "noplaylist": True, "extract_flat": True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(search_query, download=False)
        return result["entries"][0]["url"] if "entries" in result and result["entries"] else None

def get_playlist_details():
    playlist_tracks = {}
    playlists = sp.current_user_playlists()
    while playlists:
        for playlist in playlists["items"]:
            tracks = []
            results = sp.playlist_items(playlist['uri'])
            while results:
                tracks.extend(results['items'])
                results = sp.next(results) if results["next"] else None
            playlist_tracks[clean_string(playlist['name'])] = [track['track']['name'] for track in tracks]
        playlists = sp.next(playlists) if playlists['next'] else None
    return playlist_tracks

playlist_details = get_playlist_details()

class YTDLSource(disnake.PCMVolumeTransformer):
    def __init__(self, source: disnake.AudioSource, *, data: Dict[str, Any], volume: float = 0.5):
        super().__init__(source, volume)
        self.title = data.get("title")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if "entries" in data:
            data = data["entries"][0]
        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(disnake.FFmpegPCMAudio(filename, options="-vn"), data=data)

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queue = []
        self.playing = False

    @commands.command()
    async def join(self, ctx, *, channel: disnake.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    @commands.command()
    async def stream(self, ctx, *, url: str):
        await self._play_url(ctx, url=url, stream=True)

    async def _play_url(self, ctx, *, url: str, stream: bool):
        await self.ensure_voice(ctx)
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=stream)
            ctx.voice_client.play(
                player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
            )
        await ctx.send(f"Now playing: {player.title}")

    @commands.command()
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()

    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")


    @commands.command()
    async def playlist(self, ctx, playlist_name: str):
        try:    
            print("E")
            formatted_name = clean_string(playlist_name)
            track_names = playlist_details.get(formatted_name, [])
            track_urls =[]
            for track in track_names:
                if track not in store_track_urls.keys():
                    track_urls.append(get_youtube_url(track))
                else:
                    track_urls.append(store_track_urls[track])
            random.shuffle(track_urls)  
            self.queue.extend(track_urls)
            await ctx.send(f"Loaded {len(track_urls)} tracks into the queue.")
            if not self.playing:
                self.playing = True
                await self.play_next(ctx)
        except Exception as e:
            await ctx.send("Error loading playlist.")
            print("Error:", e)

    async def play_next(self, ctx):
        if not self.queue:
            self.playing = False
            return
        url = self.queue.pop(0)
        print(url)
        try:
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(
                player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
            )
            await ctx.send(f"Now playing: {player.title}")
        except Exception as e:
            print(f"Error playing next track: {e}")
            await ctx.send("Error playing the next track.")
            self.playing = False

    @commands.command()
    async def show_queue(self, ctx):
        await ctx.send("Queue is empty." if not self.queue else "\n".join(self.queue[:5]))

    
    @commands.command()
    async def next(self, ctx):
        """Skips the current song and plays the next one in the queue."""
        if ctx.voice_client is None or not ctx.voice_client.is_playing():
            return await ctx.send("No song is currently playing.")
        
        ctx.voice_client.stop()  # This triggers play_next() automatically
        await ctx.send("Skipping to the next track...")

    @commands.command()
    async def pause(self, ctx):
        """Pauses the currently playing song."""
        if ctx.voice_client is None or not ctx.voice_client.is_playing():
            return await ctx.send("No song is currently playing.")
        
        ctx.voice_client.pause()
        await ctx.send("Playback paused. ")

    @commands.command()
    async def resume(self, ctx):
        """Resumes the paused song."""
        if ctx.voice_client is None or not ctx.voice_client.is_paused():
            return await ctx.send("There is no paused song to resume.")
        
        ctx.voice_client.resume()
        await ctx.send("Playback resumed. ")

    @commands.command()
    async def queue(self, ctx):
        """Displays the current music queue."""
        if not self.queue:
            return await ctx.send("The queue is empty. ")

        queue_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(self.queue[:10])])
        await ctx.send(f" **Current Queue:**\n{queue_list}")

bot = commands.Bot(command_prefix=commands.when_mentioned, description="Music bot")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})\n------")

bot.add_cog(Music(bot))

if __name__ == "__main__":
    bot.run(os.getenv("BOT_TOKEN"))