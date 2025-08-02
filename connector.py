import os
from search import search_and_download_youtube_song
from analyze import analyze_song
from find_best_transition import find_best_transition
from transition import extract_chorus, split_audio, create_transition, match_bpm

def search_download(query, path, cookie_path):
    current_song_name = search_and_download_youtube_song(query, path + '/current_song', cookie_path)
    bpm, camelot, loudness, energy = analyze_song(path + '/current_song/song.mp3')
    current_song_data = {
        'bpm': bpm,
        'camelot_key': camelot,
        'loudness': loudness,
        'energy': energy
    }
    print(bpm, camelot, loudness, energy)
    transition_song_name = find_best_transition(current_song_data, 'song_metadata.csv')
    return current_song_name, transition_song_name

def transition_songs(output_dir, transition_type):
    extract_chorus(output_dir + "/current_song/song.mp3", output_dir + "/current_song/chorus.mp3")
    split_audio(output_dir + '/current_song/chorus.mp3', output_dir + '/current_song')
    extract_chorus(output_dir + "/transition_song/song.mp3", output_dir + "/transition_song/chorus.mp3")
    split_audio(output_dir + '/transition_song/chorus.mp3', output_dir + '/transition_song')
    create_transition(output_dir, transition_type)