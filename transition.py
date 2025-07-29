from pydub import AudioSegment
import librosa
import numpy as np
import os
from demucs.pretrained import get_model
from demucs.apply import apply_model
import torch
import torchaudio

def extract_chorus(input_file, output_path, duration=15):
    audio = AudioSegment.from_mp3(input_file)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    if audio.channels == 2:
        samples = samples.reshape((-1, 2))
        samples = samples.mean(axis=1)

    sr = audio.frame_rate
    onset_env = librosa.onset.onset_strength(y=samples, sr=sr)
    hop_length = 512
    frames_per_sec = sr / hop_length
    window_length = int(duration * frames_per_sec)
    energy = np.convolve(onset_env, np.ones(window_length), 'valid')
    max_pos = np.argmax(energy)
    start_time_sec = max_pos * hop_length / sr
    start_ms = int(start_time_sec * 1000)
    end_ms = start_ms + int(duration * 1000)
    chorus = audio[start_ms:end_ms]
    chorus.export(output_path, format="mp3")

def split_audio(input_file, output_dir):
    model = get_model('htdemucs')
    wav, rate = torchaudio.load(input_file)
    device = 'mps' if torch.mps.is_available() else 'cpu'
    sources = apply_model(model, wav.unsqueeze(0), device=device)
    os.makedirs(output_dir, exist_ok=True)
    for stem, name in zip(sources[0], ['drums', 'bass', 'other', 'vocals']):
        output_path = os.path.join(output_dir, f"{name}.wav")
        torchaudio.save(output_path, stem, rate)
        print(f"Saved {name} to {output_path}")

def build_instrumental(bass, drums, other):
    return bass.overlay(drums).overlay(other)

from pydub import AudioSegment

def create_transition(songs_dir, transition_type="crossfade"):
    # Load stems for current song
    vocals_current = AudioSegment.from_file(songs_dir + "/current_song" + "/vocals.wav")
    bass_current   = AudioSegment.from_file(songs_dir + "/current_song" + "/bass.wav")
    drums_current  = AudioSegment.from_file(songs_dir + "/current_song" + "/drums.wav")
    other_current  = AudioSegment.from_file(songs_dir + "/current_song" + "/other.wav")

    # Load stems for transition song
    vocals_transition = AudioSegment.from_file(songs_dir + "/transition_song" + "/vocals.wav")
    bass_transition   = AudioSegment.from_file(songs_dir + "/transition_song" + "/bass.wav")
    drums_transition  = AudioSegment.from_file(songs_dir + "/transition_song" + "/drums.wav")
    other_transition  = AudioSegment.from_file(songs_dir + "/transition_song" + "/other.wav")

    # Build instrumentals
    instrumental_current = build_instrumental(bass_current, drums_current, other_current)
    instrumental_transition = build_instrumental(bass_transition, drums_transition, other_transition)

    # Combine vocals with instrumentals
    song_current = instrumental_current.overlay(vocals_current)
    song_transition = instrumental_transition.overlay(vocals_transition)

    if transition_type == "crossfade":
        vocals_current_down = 10000
        vocals_transition_in = 15000
        crossfade_duration = 5000

        # Part 1: start of current song
        full_current = song_current[:vocals_current_down]

        # Part 2: current fades out, transition instruments fade in
        current_fade_out = instrumental_current[vocals_current_down:vocals_transition_in].fade_out(crossfade_duration)
        current_fade_out = current_fade_out.overlay(vocals_current[vocals_current_down:vocals_transition_in].fade_out(3000))
        current_fade_out = current_fade_out.overlay(instrumental_transition[0:].fade_in(crossfade_duration))

        # Part 3: vocals from transition fade in
        transition_vocals_fade_in = vocals_transition[5000:10000].fade_in(crossfade_duration)
        transition_vocals_fade_in = transition_vocals_fade_in.overlay(instrumental_transition[5000:])

        # Part 4: rest of transition song
        transition_remainder = vocals_transition[10000:].overlay(instrumental_transition[10000:])

        final_transition = full_current + current_fade_out + transition_vocals_fade_in + transition_remainder
        output_file = songs_dir + "/crossfade_dj_transition.mp3"

    elif transition_type == "scratch":
        scratch_start = 15000
        full_current = song_current[:scratch_start]

        scratch_loop = AudioSegment.from_file('transitions' + "/scratch_loop.wav")[:600]

        final_transition = full_current + scratch_loop + song_transition
        output_file = songs_dir + "/scratch_dj_transition.mp3"

    else:
        raise ValueError(f"Unsupported transition type: {transition_type}")

    final_transition.export(output_file, format="mp3")
    print(f"{transition_type.title()} DJ Transition created!")

extract_chorus('./temp/current_song/song.mp3', './temp/current_song/chorus.mp3')
split_audio('./temp/current_song/chorus.mp3', './temp/current_song')
extract_chorus('./temp/transition_song/song.mp3', './temp/transition_song/chorus.mp3')
split_audio('./temp/transition_song/chorus.mp3', './temp/transition_song')
create_transition('./temp', 'scratch')