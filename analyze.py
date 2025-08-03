import numpy as np
import essentia
import essentia.standard as es

MUSICKEY_TO_CAMELOT = {
    'C': '8B', 'C#': '3B', 'D': '10B', 'D#': '5B', 'E': '12B', 'F': '7B',
    'F#': '2B', 'G': '9B', 'G#': '4B', 'A': '11B', 'A#': '6B', 'B': '1B',
    'Cm': '5A', 'C#m': '12A', 'Dm': '7A', 'D#m': '2A', 'Em': '9A', 'Fm': '4A',
    'F#m': '11A', 'Gm': '6A', 'G#m': '1A', 'Am': '8A', 'A#m': '3A', 'Bm': '10A'
}

def normalize_key(key):
    flats_to_sharps = {
        'Db': 'C#',
        'Eb': 'D#',
        'Gb': 'F#',
        'Ab': 'G#',
        'Bb': 'A#'
    }
    return flats_to_sharps.get(key, key)

def camelot_from_key(key_name, scale):
    key = normalize_key(key_name)
    if scale.lower() == 'minor':
        key += 'm'
    return MUSICKEY_TO_CAMELOT.get(key, "Unknown")

def analyze_song(audio_path):
    # Load audio (mono)
    loader = es.MonoLoader(filename=audio_path)
    audio = loader()

    # Tempo (BPM)
    rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
    bpm, _, _, _, _ = rhythm_extractor(audio)

    # Key & scale
    key_extractor = es.KeyExtractor()
    key_str, scale, _ = key_extractor(audio)
    camelot = camelot_from_key(key_str, scale)

    # Loudness (dB)
    replay_gain = es.ReplayGain()
    loudness = replay_gain(audio)

    # Energy (normalized)
    energy = np.sum(audio ** 2)
    normalized_energy = energy / len(audio)

    return round(bpm, 2), camelot, round(loudness, 2), normalized_energy