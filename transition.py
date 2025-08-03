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
    device = 'mps' if torch.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
    sources = apply_model(model, wav.unsqueeze(0), device=device)
    os.makedirs(output_dir, exist_ok=True)
    for stem, name in zip(sources[0], ['drums', 'bass', 'other', 'vocals']):
        output_path = os.path.join(output_dir, f"{name}.wav")
        torchaudio.save(output_path, stem, rate)
        print(f"Saved {name} to {output_path}")

def build_instrumental(bass, drums, other):
    return bass.overlay(drums).overlay(other)

def get_beat_times(audio_segment):
    samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32)
    if audio_segment.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)
    y = samples / np.max(np.abs(samples))  # normalize
    sr = audio_segment.frame_rate
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beats, sr=sr)
    return beat_times

def match_bpm(current_song, transition_song):
    source_audio, sr = librosa.load(current_song, sr=None)
    target_audio, _ = librosa.load(transition_song, sr=sr)

    source_bpm = librosa.feature.tempo(y=source_audio, sr=sr)[0]
    target_bpm = librosa.feature.tempo(y=target_audio, sr=sr)[0]
    stretch_ratio = source_bpm / target_bpm

    y, stem_sr = librosa.load(transition_song, sr=None)
    y_stretched = librosa.effects.time_stretch(y, rate=stretch_ratio)
    y_stretched = librosa.util.normalize(y_stretched)

    stem_path = os.path.splitext(transition_song)[0] + "_matched.wav"
    sf.write(stem_path, y_stretched, stem_sr)

    return stem_path

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

    # Get beat times
    beats_current = get_beat_times(song_current)
    beats_transition = get_beat_times(song_transition)
    crossfade_beats = 4

    # Desired minimum time before transition in seconds (e.g., 12 seconds)
    min_time_before_transition = 12

    # Find the beat index closest to min_time_before_transition
    start_beat_idx = 0
    for i, beat_time in enumerate(beats_current):
        if beat_time >= min_time_before_transition:
            start_beat_idx = i
            break

    fade_start_time_current = beats_current[start_beat_idx]
    fade_end_time_current = beats_current[start_beat_idx + crossfade_beats]
    fade_start_time_transition = beats_transition[8]

    # Convert to milliseconds
    vocals_current_down = int(fade_start_time_current * 1000)
    vocals_transition_in = int(fade_end_time_current * 1000)
    transition_start_time = int(fade_start_time_transition * 1000)
    transition_start_other = vocals_current_down

    if transition_type == "crossfade":
        crossfade_duration = vocals_transition_in - vocals_current_down

        # Part 1: Intro from current song
        full_current = song_current[:vocals_current_down]

        # Part 2: Crossfade section
        current_fade_out = instrumental_current[vocals_current_down:vocals_transition_in].fade_out(crossfade_duration)
        current_fade_out = current_fade_out.overlay(vocals_current[vocals_current_down:vocals_transition_in].fade_out(int(crossfade_duration * 0.6)))
        current_fade_out = current_fade_out.overlay(instrumental_transition[transition_start_time:transition_start_time+crossfade_duration].fade_in(crossfade_duration))

        # Part 3: Bring in vocals from transition
        transition_vocals_fade_in = vocals_transition[transition_start_time+crossfade_duration:transition_start_time+2*crossfade_duration].fade_in(crossfade_duration)
        transition_vocals_fade_in = transition_vocals_fade_in.overlay(instrumental_transition[transition_start_time+crossfade_duration:])

        # Part 4: Remainder of transition
        transition_remainder = vocals_transition[transition_start_time+2*crossfade_duration:].overlay(instrumental_transition[transition_start_time+2*crossfade_duration:])

        # Final song
        final_transition = full_current + current_fade_out + transition_vocals_fade_in + transition_remainder
        output_file = songs_dir + "/dj_transition.mp3"

    elif transition_type == "scratch":
        scratch_start = transition_start_other
        full_current = song_current[:scratch_start]

        scratch_loop = AudioSegment.from_file('transitions' + "/scratch_loop.wav")[:600]

        final_transition = full_current + scratch_loop + song_transition
        output_file = songs_dir + "/dj_transition.mp3"

    elif transition_type == "crazy_scratch":
        scratch_start = transition_start_other

        # Full song A
        full_current = song_current[:scratch_start]

        # Scratching
        scratch_loop = AudioSegment.from_file('transitions' + "/crazy_scratch_loop.wav")

        # Full transition
        final_transition = full_current + scratch_loop + song_transition
        output_file = songs_dir + "/dj_transition.mp3"
    
    elif transition_type == "vocals_tease":
        match_bpm(songs_dir + "/current_song/vocals.wav", songs_dir + "/transition_song/vocals.wav")

        matched_vocals_path = os.path.join(songs_dir, "/transition_song/vocals_matched.wav")
        vocals_b_matched = AudioSegment.from_file(matched_vocals_path)

        # On Beat?
        start_time_ms = transition_start_other
        tease_duration_ms = 30_000

        # PART 1: Song A
        part1 = song_current[:start_time_ms]

        # PART 2: Song A instrumental + Song B vocals
        a_instr_tease = instrumental_current[start_time_ms:start_time_ms + tease_duration_ms]
        b_vocals_tease = vocals_b_matched[:tease_duration_ms].fade_in(2000).fade_out(2000)
        part2 = a_instr_tease.overlay(b_vocals_tease)

        # PART 3: Back to Song A
        part3 = song_current[start_time_ms + tease_duration_ms:]

        final_transition = part1 + part2 + part3
        output_file = songs_dir + "/dj_transition.mp3"
    
    else:
        raise ValueError(f"Unsupported transition type: {transition_type}")

    final_transition.export(output_file, format="mp3")
    print(f"{transition_type.title()} DJ Transition created!")