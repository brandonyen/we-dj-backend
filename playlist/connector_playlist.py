import os
import pandas as pd
from transition_playlist import create_full_mix
import uuid
from search_playlist import search_all

def main():
    playlist = ["track1", "track2", "track3"]
    folder_uuid = str(uuid.uuid4())
    uuid_folder = os.path.join("playlist", folder_uuid)
    os.makedirs(uuid_folder, exist_ok=True)
    search_all(playlist, uuid_folder, 'cookies.txt')
    create_full_mix(uuid_folder, transition_type="vocals_crossover", output_file=uuid_folder+"/test.mp3")