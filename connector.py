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
from transition import extract_chorus, split_audio, create_transition

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
            'bpm': bpm,
            'camelot_key': camelot,
            'loudness': loudness,
            'energy': energy
        }, on_conflict="filename").execute()

        song_path = os.path.join(path, "current_song", "song.mp3")
        write_path = os.path.join('songs', f"{safe_name}.mp3")
        shutil.copyfile(song_path, write_path)

    return safe_name, transition_song_name

def transition_songs(output_dir: str, transition_type: str):
    extract_chorus(output_dir + "/current_song/song.mp3", output_dir + "/current_song/chorus.mp3")
    split_audio(output_dir + '/current_song/chorus.mp3', output_dir + '/current_song')

    extract_chorus(output_dir + "/transition_song/song.mp3", output_dir + "/transition_song/chorus.mp3")
    split_audio(output_dir + '/transition_song/chorus.mp3', output_dir + '/transition_song')

    create_transition(output_dir, transition_type)
