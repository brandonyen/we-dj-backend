import os
import re
import shutil
import unicodedata
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from search import search_and_download_youtube_song
from analyze import analyze_song
from find_best_transition import find_best_transition
from transition_playlist import create_full_mix
load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def make_safe_filename(name: str) -> str:
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[\\/:"*?<>|]', '_', name)

def search_download(query: str, path: str, cookie_path: str):
    current_song_name = search_and_download_youtube_song(query, path + '/current_song', cookie_path)
    bpm, camelot, loudness, energy = analyze_song(path + '/current_song/song.mp3')

    current_song_data = {
        'bpm': bpm,
        'camelot_key': camelot,
        'loudness': loudness,
        'energy': energy
    }

    response = supabase.table('songs').select('*').execute()
    df = pd.DataFrame(response.data or [])

    transition_song_name = find_best_transition(current_song_data, df)

    safe_name = make_safe_filename(current_song_name)
    if safe_name not in df['filename'].values:
        supabase.table('songs').upsert({
            'filename': safe_name,
            'bpm': float(bpm),
            'camelot_key': camelot,
            'loudness': float(loudness),
            'energy': float(energy)
        }, on_conflict="filename").execute()

        song_path = os.path.join(path, "current_song", "song.mp3")
        write_path = os.path.join('songs', f"{safe_name}.mp3")
        shutil.copyfile(song_path, write_path)

    return safe_name, transition_song_name


def transition_songs(song_list, output_path="output/final_mix.mp3", transition_type="crossfade"):
    """
    Given a list of MP3 song filenames, creates a single mix with transitions.
    """
    # Add path prefix if songs are in the 'songs' folder
    song_paths = [os.path.join("songs", f"{name}.mp3") for name in song_list]

    # Create full mix from song list
    create_full_mix(song_paths, transition_type=transition_type, output_file=output_path)

def main():
    playlist = ["track1", "track2", "track3"]
    transition_songs(playlist, output_path="my_mix.mp3", transition_type="vocals_crossover")
