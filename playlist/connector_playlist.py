import os
import pandas as pd
from transition_playlist import create_full_mix
import uuid
from search_playlist import search_all
from analyze_playlist import analyze_song_list, order_songs_for_transition

if __name__ == '__main__':
    playlist = ["the less i know the better", "californication", "sicko mode", "god's plan", "part of me", "one more time", "sweet child o mine", "location playboi carti"]
    folder_uuid = str(uuid.uuid4())
    uuid_folder = os.path.join("playlist", "temp", folder_uuid)
    os.makedirs(uuid_folder, exist_ok=True)
    song_paths = search_all(playlist, uuid_folder, 'cookies.txt')
    df = analyze_song_list(song_paths)
    ordered_paths = order_songs_for_transition(df)
    # create_full_mix(uuid_folder, ordered_paths, transition_type="crossfade", output_file=uuid_folder+"/playlist_transition.mp3")