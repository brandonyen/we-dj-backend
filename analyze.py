import essentia.standard as es

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
    if key in flats_to_sharps:
        return flats_to_sharps[key]
    return key

def camelot_from_key(key_name, scale):
    key = normalize_key(key_name)
    if scale.lower() == 'minor':
        key += 'm'
    return MUSICKEY_TO_CAMELOT.get(key, "Unknown")

def analyze_song(audio_path):
    loader = es.MonoLoader(filename=audio_path)
    audio = loader()

    rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
    bpm, _, _, _, _ = rhythm_extractor(audio)

    key_extractor = es.KeyExtractor()
    key, scale, _ = key_extractor(audio)

    camelot = camelot_from_key(key, scale)

    loudness = es.Loudness()
    loudness_val = loudness(audio)

    energy = es.Energy()
    energy_val = energy(audio)
    normalized_energy = energy_val / len(audio)

    return round(bpm, 2), camelot, round(loudness_val, 2), normalized_energy