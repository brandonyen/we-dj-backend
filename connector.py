import os
from search import search_and_download_youtube_song
from analyze import analyze_song

def search_download_transition(query):
    os.makedirs('temp/current_song', exist_ok=True)
    os.makedirs('temp/transition_song', exist_ok=True)
    current_song_name = search_and_download_youtube_song(query, 'temp/current_song')
    bpm, camelot, loudness = analyze_song('./temp/current_song/song.mp3')
    print(bpm, camelot, loudness)