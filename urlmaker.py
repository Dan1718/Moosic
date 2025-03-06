import asyncio
import os
from typing import Any, Dict, Optional
import dotenv
import disnake
import yt_dlp as youtube_dl
import subprocess
from disnake.ext import commands
dotenv.load_dotenv()
# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ""
import json


def get_youtube_url(track_name):
    search_query = f"ytsearch:{track_name} official audio"
    ydl_opts = {
        "quiet": True,
        "default_search": "ytsearch",
        "noplaylist": True,
        "extract_flat": True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(search_query, download=False)
        if "entries" in result and result["entries"]:
            return result["entries"][0]["url"]  # First search result
        else:
            return None  # No results found
        
        
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
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import re 
load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="playlist-read-private"
))
track_urls ={}
def clean_string(s):
    s = s.lower()  # Convert to lowercase
    s = re.sub(r'[^a-z0-9]', '', s)  # Remove everything except letters and numbers
    return s
track_names_master =[]
def get_playlist_details():
    playlist_tracks = {}
    # Get current user's playlists
    playlists = sp.current_user_playlists()

    while playlists:

        for playlist in playlists["items"]:

            tracks=[]
            results = sp.playlist_items(playlist['uri'])
            
            while results: 
                tracks.extend(results['items'])
                results = sp.next(results) if results["next"] else None
            track_names=[]
            for track in tracks:
                track_name = track['track']['name']
                if track_name not in track_names_master:
                    track_names_master.append(track_name)
                track_names.append(track_name)
                
            playlist_name = playlist['name']
            playlist_name_true=clean_string(playlist_name)
            playlist_tracks[playlist_name_true] = track_names
            
        playlists = sp.next(playlists) if playlists['next'] else None
        

    return playlist_tracks

playlist_details = get_playlist_details()
print("First part done")

def get_track_urls():
    for track in track_names_master:
        url = get_youtube_url(track)
        track_urls[track]=url
        print(track)
get_track_urls()
    
with open("data.json", "w") as file:
    json.dump(track_urls, file, indent=4) 