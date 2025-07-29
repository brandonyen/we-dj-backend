import essentia.standard as es

MUSICKEY_TO_CAMELOT = {
    'C': '8B', 'C#': '3B', 'D': '10B', 'D#': '5B', 'E': '12B', 'F': '7B',
    'F#': '2B', 'G': '9B', 'G#': '4B', 'A': '11B', 'A#': '6B', 'B': '1B',
    'Cm': '5A', 'C#m': '12A', 'Dm': '7A', 'D#m': '2A', 'Em': '9A', 'Fm': '4A',
    'F#m': '11A', 'Gm': '6A', 'G#m': '1A', 'Am': '8A', 'A#m': '3A', 'Bm': '10A'
}

def camelot_from_key(key_name, scale):
    """Convert Essentia key name and scale to Camelot notation."""
    key = key_name.upper()
    if scale == 'minor':
        key += 'm'
    return MUSICKEY_TO_CAMELOT.get(key, "Unknown")

def analyze_song(audio_path):
    loader = es.MonoLoader(filename=audio_path)
    audio = loader()

    rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
    bpm, _, _, _, _ = rhythm_extractor(audio)

    key_extractor = es.KeyExtractor()
    key, scale, strength = key_extractor(audio)

    camelot = camelot_from_key(key, scale)

    loudness = es.Loudness()
    loudness_val = loudness(audio)

    return {
        'bpm': round(bpm, 2),
        'key': key,
        'scale': scale,
        'camelot_key': camelot,
        'loudness': round(loudness_val, 2)
    }