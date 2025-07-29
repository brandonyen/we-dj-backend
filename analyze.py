import librosa
import numpy as np
from pydub import AudioSegment

MUSICKEY_TO_CAMELOT = {
    'C': '8B', 'C#': '3B', 'D': '10B', 'D#': '5B', 'E': '12B', 'F': '7B',
    'F#': '2B', 'G': '9B', 'G#': '4B', 'A': '11B', 'A#': '6B', 'B': '1B',
    'Cm': '5A', 'C#m': '12A', 'Dm': '7A', 'D#m': '2A', 'Em': '9A', 'Fm': '4A',
    'F#m': '11A', 'Gm': '6A', 'G#m': '1A', 'Am': '8A', 'A#m': '3A', 'Bm': '10A'
}

def normalize_key(key):
    flats_to_sharps = {
        'DB': 'C#',
        'EB': 'D#',
        'GB': 'F#',
        'AB': 'G#',
        'BB': 'A#'
    }
    key = key.upper()
    return flats_to_sharps.get(key, key)

def camelot_from_key(key_name, scale):
    key = normalize_key(key_name)
    if scale.lower() == 'minor':
        key += 'm'
    return MUSICKEY_TO_CAMELOT.get(key, "Unknown")

def detect_key_and_scale(y, sr):
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)

    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                              2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                              2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    keys = ['C', 'C#', 'D', 'D#', 'E', 'F',
            'F#', 'G', 'G#', 'A', 'A#', 'B']
    max_corr = -np.inf
    best_key = "C"
    best_mode = "major"

    for i in range(12):
        corr_major = np.corrcoef(np.roll(major_profile, i), chroma_mean)[0, 1]
        corr_minor = np.corrcoef(np.roll(minor_profile, i), chroma_mean)[0, 1]

        if corr_major > max_corr:
            max_corr = corr_major
            best_key = keys[i]
            best_mode = "major"

        if corr_minor > max_corr:
            max_corr = corr_minor
            best_key = keys[i]
            best_mode = "minor"

    return best_key, best_mode

def analyze_song(audio_path):
    y, sr = librosa.load(audio_path, mono=True)

    # Tempo (BPM)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(tempo[0]) if hasattr(tempo, "__getitem__") else float(tempo)

    # Key & scale
    key, scale = detect_key_and_scale(y, sr)
    camelot = camelot_from_key(key, scale)

    # Loudness (dBFS)
    audio_segment = AudioSegment.from_file(audio_path)
    loudness_val = audio_segment.dBFS

    # Energy
    energy_val = np.sum(y ** 2)
    normalized_energy = energy_val / len(y)

    return round(tempo, 2), camelot, round(loudness_val, 2), normalized_energy