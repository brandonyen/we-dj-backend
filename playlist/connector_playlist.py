import os
from playlist.transition_playlist import create_full_mix
import uuid
from playlist.search_playlist import search_all
from playlist.analyze_playlist import analyze_song_list, order_songs_for_transition
from typing import List

def connector_playlist(song_list: List[str]):
    folder_uuid = str(uuid.uuid4())
    uuid_folder = os.path.join("playlist", "temp", folder_uuid)
    os.makedirs(uuid_folder, exist_ok=True)
    song_paths = search_all(song_list, uuid_folder, 'cookies.txt')
    df = analyze_song_list(song_paths)
    ordered_paths = order_songs_for_transition(df)
    create_full_mix(uuid_folder, ordered_paths, output_file=uuid_folder+"/playlist_transition.mp3", transition_type='vocals_crossover')
    return folder_uuid