import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="playlist-read-private"
))

# Get current user's playlists
playlists = sp.current_user_playlists()
while playlists:
    playlist = {}
    for playlist in playlists["items"]:
        print(playlist["name"])
        tracks=[]
        results = sp.playlist_items(playlist['uri'])
        break
        while results: 
            tracks.extend(results['items'])
            results = sp.next(results) if results["next"] else None

        playlist['']
        
    playlists = sp.next(playlists) if playlists['next'] else None

