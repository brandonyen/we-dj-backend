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
    energy_diff = abs(source['energy'] - target['energy'])
    return camelot_penalty ** 2 * 10 + bpm_diff ** 2 * 5 + loudness_diff ** 2 * 10 + energy_diff ** 2 * 200

def find_best_transition(current_song_data, csv_path):
    df = pd.read_csv(csv_path)

    candidates = df.copy()

    candidates['bpm'] = pd.to_numeric(candidates['bpm'], errors='coerce')
    candidates['loudness'] = pd.to_numeric(candidates['loudness'], errors='coerce')
    candidates['energy'] = pd.to_numeric(candidates['energy'], errors='coerce')
    candidates = candidates.dropna(subset=['bpm', 'loudness', 'camelot_key'])

    if candidates.empty:
        candidates = df.copy()
        candidates['bpm'] = pd.to_numeric(candidates['bpm'], errors='coerce')
        candidates['loudness'] = pd.to_numeric(candidates['loudness'], errors='coerce')
        candidates = candidates.dropna(subset=['bpm', 'loudness', 'camelot_key'])

    candidates['score'] = candidates.apply(lambda row: transition_score(current_song_data, row), axis=1)
    candidates = candidates[candidates['score'] >= 0.01]
    best_match = candidates.sort_values(by='score').iloc[0]

    print(candidates.sort_values(by='score'))

    return best_match['filename']