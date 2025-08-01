from pydub import AudioSegment
import librosa
import numpy as np
import os
from demucs.pretrained import get_model
from demucs.apply import apply_model
import torch
import torchaudio
import soundfile as sf

def extract_chorus(input_file, output_path, duration=15):
    if os.path.exists(output_path):
        print(f"{output_path} already exists. Skipping extraction.")
        return
    
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
    expected_files = [os.path.join(output_dir, f"{name}.wav") for name in ['drums', 'bass', 'other', 'vocals']]
    if all(os.path.exists(f) for f in expected_files):
        print(f"All output files already exist in {output_dir}. Skipping splitting.")
        return
    
    model = get_model('htdemucs')
    wav, rate = torchaudio.load(input_file)
    device = 'mps' if torch.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
    sources = apply_model(model, wav.unsqueeze(0), device=device)
    os.makedirs(output_dir, exist_ok=True)
    for stem, name in zip(sources[0], ['drums', 'bass', 'other', 'vocals']):
        output_path = os.path.join(output_dir, f"{name}.wav")
        torchaudio.save(output_path, stem, rate)
        print(f"Saved {name} to {output_path}")

def build_instrumental(bass, drums, other):
    return bass.overlay(drums).overlay(other)

def match_bpm(current_song, transition_song):
    source_audio, sr = librosa.load(os.path.join(current_song, "song.mp3"), sr=None)
    target_audio, _ = librosa.load(os.path.join(transition_song, "song.mp3"), sr=sr)

    source_bpm = librosa.feature.tempo(y=source_audio, sr=sr)[0]
    target_bpm = librosa.feature.tempo(y=target_audio, sr=sr)[0]
    stretch_ratio = source_bpm / target_bpm

    for stem in ['bass', 'drums', 'other', 'vocals']:
        stem_path = os.path.join(transition_song, f"{stem}.wav")
        y, stem_sr = librosa.load(stem_path, sr=None)

        y_stretched = librosa.effects.time_stretch(y, rate=stretch_ratio)
        y_stretched = librosa.util.normalize(y_stretched)

        sf.write(stem_path, y_stretched, stem_sr)
    
    return source_bpm, target_bpm

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
        output_file = songs_dir + "/dj_transition.mp3"

    elif transition_type == "scratch":
        scratch_start = 15000
        full_current = song_current[:scratch_start]

        scratch_loop = AudioSegment.from_file('transitions' + "/scratch_loop.wav")[:600]

        final_transition = full_current + scratch_loop + song_transition
        output_file = songs_dir + "/sdj_transition.mp3"

    elif transition_type == "crazy_scratch":
        scratch_start = 12500

        # Full song A
        full_current = song_current[:scratch_start]

        # Scratching
        scratch_loop = AudioSegment.from_file('transitions' + "/crazy_scratch_loop.wav")

        # Full transition
        final_transition = full_current + scratch_loop + song_transition
        output_file = songs_dir + "/crazy_sdj_transition.mp3"
    
    elif transition_type == "steve":
        bpm1, bpm2 = match_bpm(songs_dir + "/current_song" + "/vocals.wav", songs_dir + "/transition_song" + "/vocals.wav")
        scratch = AudioSegment.from_file('transitions' + "/scratch.wav")[:60000 / (bpm1*2)]
        vocals_a_matched = AudioSegment.from_file(songs_dir + "/current_song" + "/vocals.wav")
        silence = AudioSegment.silent(duration=60000 / (bpm2 * 2))

        instrument_fade = 8500
        scratch_sound = 15000
        instrument_new = 15500
        full_new = 22000

        full_current = song_current[:instrument_fade]

        a_instrument_fade = vocals_current[instrument_fade:scratch_sound]
        a_instrument_fade = a_instrument_fade.overlay(instrumental_current[instrument_fade:scratch_sound].apply_gain(-120))

        scratch_time = vocals_current[scratch_sound:instrument_new]
        scratch_loop = scratch + scratch
        scratch_time = scratch_time.overlay(scratch_loop)

        b_fade = instrumental_transition[:full_new - instrument_new]
        b_fade = b_fade.overlay(vocals_a_matched[instrument_new * (bpm2 / bpm1):full_new * (bpm2 / bpm1)].fade_out(full_new-instrument_new))

        b_instrumental = instrumental_transition[full_new - instrument_new:]
        full_b = b_instrumental.overlay(vocals_transition[full_new - instrument_new:].fade_in(3000))

        final_transition = full_current + a_instrument_fade + scratch_loop + silence + b_fade + full_b
        output_file = songs_dir + "/steve_transition.mp3"
    
    else:
        raise ValueError(f"Unsupported transition type: {transition_type}")

    final_transition.export(output_file, format="mp3")
    print(f"{transition_type.title()} DJ Transition created!")