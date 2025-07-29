import pandas as pd
from analyze import analyze_song

def compatible_camelot_keys(camelot):
    num = int(camelot[:-1])
    letter = camelot[-1]
    adjacent = [(num - 1) % 12 or 12, num, (num + 1 - 1) % 12 + 1]
    other_letter = 'B' if letter == 'A' else 'A'
    return [f"{n}{letter}" for n in adjacent] + [f"{num}{other_letter}"]

def transition_score(source, target):
    camelot_penalty = 0 if target['camelot_key'] in compatible_camelot_keys(source['camelot_key']) else 10
    bpm_diff = abs(source['bpm'] - target['bpm'])
    loudness_diff = abs(source['loudness'] - target['loudness'])
    return camelot_penalty + bpm_diff * 0.3 + loudness_diff * 0.1

def is_too_similar(song1, song2, bpm_thresh=0.5, loudness_thresh=0.5):
    same_key = song1['camelot_key'] == song2['camelot_key']
    bpm_close = abs(song1['bpm'] - song2['bpm']) < bpm_thresh
    loudness_close = abs(song1['loudness'] - song2['loudness']) < loudness_thresh
    return same_key and bpm_close and loudness_close

def find_best_transition(current_song_data, csv_path):
    df = pd.read_csv(csv_path)

    candidates = df.copy()

    candidates['bpm'] = pd.to_numeric(candidates['bpm'], errors='coerce')
    candidates['loudness'] = pd.to_numeric(candidates['loudness'], errors='coerce')
    candidates = candidates.dropna(subset=['bpm', 'loudness', 'camelot_key'])

    candidates = candidates[~candidates.apply(lambda row: is_too_similar(current_song_data, row), axis=1)]

    if candidates.empty:
        candidates = df.copy()
        candidates['bpm'] = pd.to_numeric(candidates['bpm'], errors='coerce')
        candidates['loudness'] = pd.to_numeric(candidates['loudness'], errors='coerce')
        candidates = candidates.dropna(subset=['bpm', 'loudness', 'camelot_key'])

    candidates['score'] = candidates.apply(lambda row: transition_score(current_song_data, row), axis=1)
    best_match = candidates.sort_values(by='score').iloc[0]

    print(candidates.sort_values(by='score'))

    return best_match['filename']