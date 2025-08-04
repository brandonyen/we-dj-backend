import os
import numpy as np
import pandas as pd
import essentia.standard as es

# Key to Camelot conversion map
MUSICKEY_TO_CAMELOT = {
    'C': '8B', 'C#': '3B', 'D': '10B', 'D#': '5B', 'E': '12B', 'F': '7B',
    'F#': '2B', 'G': '9B', 'G#': '4B', 'A': '11B', 'A#': '6B', 'B': '1B',
    'Cm': '5A', 'C#m': '12A', 'Dm': '7A', 'D#m': '2A', 'Em': '9A', 'Fm': '4A',
    'F#m': '11A', 'Gm': '6A', 'G#m': '1A', 'Am': '8A', 'A#m': '3A', 'Bm': '10A'
}

def normalize_key(key):
    flats_to_sharps = {
        'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'
    }
    return flats_to_sharps.get(key, key)

def camelot_from_key(key_name, scale):
    key = normalize_key(key_name)
    if scale.lower() == 'minor':
        key += 'm'
    return MUSICKEY_TO_CAMELOT.get(key, "Unknown")

def analyze_song(audio_path):
    loader = es.MonoLoader(filename=audio_path)
    audio = loader()

    # Tempo (BPM)
    bpm, _, _, _, _ = es.RhythmExtractor2013(method="multifeature")(audio)

    # Musical key
    key_str, scale, _ = es.KeyExtractor()(audio)
    camelot = camelot_from_key(key_str, scale)

    # Loudness (in dB)
    loudness = es.ReplayGain()(audio)

    # Energy (normalized)
    energy = np.sum(audio ** 2) / len(audio)

    return round(bpm, 2), camelot, round(loudness, 2), energy

def analyze_song_list(song_paths: list) -> pd.DataFrame:
    metadata = []
    for path in song_paths:
        try:
            bpm, camelot_key, loudness, energy = analyze_song(path)
            metadata.append({
                'filename': os.path.basename(path),
                'filepath': path,
                'bpm': bpm,
                'camelot_key': camelot_key,
                'loudness': loudness,
                'energy': energy
            })
        except Exception as e:
            print(f"Failed to analyze {path}: {e}")
    return pd.DataFrame(metadata)

def compatible_camelot_keys(camelot: str) -> list:
    try:
        num = int(camelot[:-1])
        letter = camelot[-1]
        adjacent = [(num - 1) % 12 or 12, num, (num % 12) + 1]
        other_letter = 'B' if letter == 'A' else 'A'
        return [f"{n}{letter}" for n in adjacent] + [f"{num}{other_letter}"]
    except Exception:
        return []

def transition_score(source, target):
    # Penalize transitions with non-compatible Camelot keys
    camelot_penalty = 0 if target['camelot_key'] in compatible_camelot_keys(source['camelot_key']) else 10
    bpm_diff = abs(source['bpm'] - target['bpm'])
    loudness_diff = abs(source['loudness'] - target['loudness'])
    energy_diff = abs(source['energy'] - target['energy'])

    # Weighted score
    return (
        camelot_penalty**2 * 10 +
        bpm_diff**2 * 5 +
        loudness_diff**2 * 10 +
        energy_diff**2 * 200
    )

def find_best_transition(current_song_data: dict, df: pd.DataFrame) -> str:
    if df.empty:
        raise ValueError("No transition candidates available.")

    candidates = df.copy()

    for col in ['bpm', 'loudness', 'energy']:
        candidates[col] = pd.to_numeric(candidates[col], errors='coerce')

    candidates = candidates.dropna(subset=['bpm', 'loudness', 'energy', 'camelot_key'])

    if candidates.empty:
        raise ValueError("No valid candidates after filtering.")

    candidates['score'] = candidates.apply(lambda row: transition_score(current_song_data, row), axis=1)

    # Optional: discard very poor transitions
    candidates = candidates[candidates['score'] >= 0.01]

    if candidates.empty:
        raise ValueError("No transition candidates scored above threshold.")

    best_match = candidates.sort_values(by='score').iloc[0]
    return best_match['filename']

def order_songs_for_transition(df: pd.DataFrame) -> list:
    if df.empty:
        raise ValueError("No song metadata available.")

    ordered = []
    remaining = df.copy()
    current = remaining.iloc[0]
    ordered.append(current)
    remaining = remaining.drop(index=current.name)

    while not remaining.empty:
        try:
            next_filename = find_best_transition(current.to_dict(), remaining)
            next_row = remaining[remaining['filename'] == next_filename].iloc[0]
            ordered.append(next_row)
            current = next_row
            remaining = remaining.drop(index=next_row.name)
        except ValueError:
            print("No valid transition found for remaining songs.")
            break

    return [row['filepath'] for _, row in pd.DataFrame(ordered).iterrows()]
