from pydub import AudioSegment
import librosa
import numpy as np
import os
from demucs.pretrained import get_model
from demucs.apply import apply_model
import torch
import torchaudio
import soundfile as sf
import essentia
import essentia.standard as es
import numpy as np
import os
import soundfile as sf
import pyrubberband as pyrb
import uuid
import shutil

def extract_chorus(input_file, output_path, duration=60):
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

def get_beat_times_essentia(audio_path):
    loader = es.MonoLoader(filename=audio_path)
    audio = loader()

    rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
    _, beats, _, _, _ = rhythm_extractor(audio)

    return beats

def get_bpm_essentia(audio, sr):
    rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
    bpm, _, _, _, _ = rhythm_extractor(audio)
    return bpm

def match_bpm(songs_dir, target_path):
    # Create two independent loader instances
    loader1 = es.MonoLoader(filename=os.path.join(songs_dir, "current_song/song.mp3"))
    source_audio = loader1()

    # It's important NOT to reuse loader1 here
    loader2 = es.MonoLoader(filename=os.path.join(songs_dir, "transition_song/song.mp3"))
    target_audio = loader2()

    sr = 44100
    source_bpm = get_bpm_essentia(source_audio, sr)
    target_bpm = get_bpm_essentia(target_audio, sr)

    stretch_ratio = source_bpm / target_bpm

    # Load stereo audio using soundfile for processing
    y, stem_sr = sf.read(target_path)
    y_stretched = pyrb.time_stretch(y, stem_sr, stretch_ratio)
    y_stretched /= np.max(np.abs(y_stretched))

    stem_path = os.path.splitext(target_path)[0] + "_matched.wav"
    sf.write(stem_path, y_stretched, stem_sr)

    print(f"CURRENT BPM: {source_bpm:.2f}")
    print(f"TRANSITION BPM: {target_bpm:.2f}")

    return stem_path, stretch_ratio

def create_transition(songs_dir, vticf, transition_type="crossfade"):
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
    instrumental_current.export(songs_dir + "/current_song/instrumentals.wav", format="wav")
    instrumental_transition.export(songs_dir + "/transition_song/instrumentals.wav", format="wav")

    # Combine vocals with instrumentals
    song_current = instrumental_current.overlay(vocals_current)
    song_transition = instrumental_transition.overlay(vocals_transition)

    song_current_path = os.path.join(songs_dir, "current_song", "full_mix.wav")
    song_transition_path = os.path.join(songs_dir, "transition_song", "full_mix.wav")

    song_current.export(song_current_path, format="wav")
    song_transition.export(song_transition_path, format="wav")

    beats_current = get_beat_times_essentia(song_current_path)
    beats_transition = get_beat_times_essentia(song_transition_path)
    crossfade_beats = 4

    # Desired minimum time before transition in seconds
    min_time_before_transition = 45

    # Find the beat index closest to min_time_before_transition
    start_beat_idx = next((i for i, t in enumerate(beats_current) if t >= min_time_before_transition), 0)

    fade_start_time_current = beats_current[start_beat_idx]
    fade_end_time_current = beats_current[start_beat_idx + crossfade_beats]
    fade_start_time_transition = beats_transition[8]  # you can also randomize or select more meaningfully

    # Convert to milliseconds
    vocals_current_down = int(fade_start_time_current * 1000)
    vocals_transition_in = int(fade_end_time_current * 1000)
    transition_start_time = int(fade_start_time_transition * 1000)
    transition_start_other = vocals_current_down

    # Convert to milliseconds
    vocals_current_down = int(fade_start_time_current * 1000)
    vocals_transition_in = int(fade_end_time_current * 1000)
    transition_start_time = int(fade_start_time_transition * 1000)
    transition_start_other = vocals_current_down
    
    a_cut = 60000-vticf
    b_cut = vticf

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

        vticf = transition_start_time+2*crossfade_duration

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
        scratch_loop = AudioSegment.from_file('transitions' + "/crazy_scratch_loop.wav")[:750]

        # Full transition
        final_transition = full_current + scratch_loop + song_transition
        output_file = songs_dir + "/dj_transition.mp3"
    
    elif transition_type == "vocals_crossover":
        matched_vocals_path, ratio1 = match_bpm(songs_dir, songs_dir + "/transition_song/vocals.wav")
        tease_duration_ms = 10000

        vocals_b_matched = AudioSegment.from_file(matched_vocals_path)
        crossfade_duration = 3000

        # PART 1: Song A
        part1 = vocals_current[:vocals_current_down-crossfade_duration]
        part1 = part1.overlay(instrumental_current[:vocals_current_down-crossfade_duration])

        # PART 1.5: Vocals Switch
        part1_5 = vocals_current[vocals_current_down-crossfade_duration:vocals_current_down].fade_out(crossfade_duration)
        part1_5 = part1_5.overlay(instrumental_current[vocals_current_down-crossfade_duration:vocals_current_down])
        part1_5 = part1_5.overlay(vocals_b_matched[vocals_transition_in-crossfade_duration:vocals_transition_in].fade_in(crossfade_duration))
        
        # PART 2: Song A instrumental + Song B vocals
        a_instr_tease = instrumental_current[vocals_current_down:vocals_current_down + tease_duration_ms]
        b_vocals_tease = vocals_b_matched[vocals_transition_in:vocals_transition_in + tease_duration_ms]
        part2 = a_instr_tease.overlay(b_vocals_tease)

        # PART 2.5: Instrumental Switch
        a_instr_tease = instrumental_current[vocals_current_down + tease_duration_ms:vocals_current_down + tease_duration_ms + crossfade_duration].fade_out(crossfade_duration)
        b_vocals_tease = vocals_b_matched[vocals_transition_in + tease_duration_ms:vocals_transition_in + tease_duration_ms + crossfade_duration]
        part2_5 = a_instr_tease.overlay(b_vocals_tease)
        part2_5 = part2_5.overlay(instrumental_transition[int((vocals_transition_in+tease_duration_ms) * ratio1):int((vocals_transition_in+tease_duration_ms+crossfade_duration) * ratio1)].fade_in(crossfade_duration))

        # PART 3: Song B continued
        part3 = vocals_transition[int((vocals_transition_in+tease_duration_ms + crossfade_duration) * ratio1):]
        part3 = part3.overlay(instrumental_transition[int((vocals_transition_in+tease_duration_ms+ crossfade_duration) * ratio1):])

        final_transition = part1 + part1_5 + part2 + part2_5 + part3
        output_file = songs_dir + "/dj_transition.mp3"

        vticf = vocals_transition_in + tease_duration_ms + crossfade_duration
        print(vticf)
    
    else:
        raise ValueError(f"Unsupported transition type: {transition_type}")

    final_transition.export(output_file, format="mp3")
    print(f"{transition_type.title()} DJ Transition created!")

    return a_cut, b_cut, vticf


def create_full_mix(uuid_folder, song_paths, output_file, transition_type="none"):
    temp_root = os.path.join(uuid_folder, "temp_songs")
    assert len(song_paths) >= 2, "Need at least two songs for transitions."

    final_mix = AudioSegment.silent(duration=0)
    os.makedirs(temp_root, exist_ok=True)

    vticf = 0

    for i in range(len(song_paths) - 1):
        song_a = song_paths[i]
        song_b = song_paths[i + 1]
        transition_dir = os.path.join(temp_root, f"transition_{i}_{uuid.uuid4().hex[:6]}")
        os.makedirs(transition_dir, exist_ok=True)

        # Create subfolders expected by your pipeline
        current_song_dir = os.path.join(transition_dir, "current_song")
        transition_song_dir = os.path.join(transition_dir, "transition_song")
        os.makedirs(current_song_dir, exist_ok=True)
        os.makedirs(transition_song_dir, exist_ok=True)

        # Extract chorus from A starting at the offset
        chorus_a_path = os.path.join(current_song_dir, "chorus.mp3")
        chorus_b_path = os.path.join(transition_song_dir, "chorus.mp3")

        # Extract full chorus
        extract_chorus(song_a, chorus_a_path)
        extract_chorus(song_b, chorus_b_path)

        # Rename to song.mp3 for processing
        chorus_a_renamed = os.path.join(current_song_dir, "song.mp3")
        chorus_b_renamed = os.path.join(transition_song_dir, "song.mp3")
        shutil.move(chorus_a_path, chorus_a_renamed)
        shutil.move(chorus_b_path, chorus_b_renamed)

        # Stem separation
        split_audio(chorus_a_renamed, current_song_dir)
        split_audio(chorus_b_renamed, transition_song_dir)

        # Create transition
        if transition_type == "none":
            matched_vocals_path, ratio = match_bpm(transition_dir, transition_dir + "/transition_song/vocals.wav")
            if 0.97 <= ratio <= 1.03:
                a_cut, b_cut, new_vticf = create_transition(transition_dir, vticf, transition_type='vocals_crossover')
            else:
                a_cut, b_cut, new_vticf = create_transition(transition_dir, vticf, transition_type='crossfade')
        else:
            a_cut, b_cut, new_vticf = create_transition(transition_dir, vticf, transition_type=transition_type)
        
        vticf = new_vticf

        # Load transition audio
        transition_audio_path = os.path.join(transition_dir, "dj_transition.mp3")
        transition_audio = AudioSegment.from_file(transition_audio_path)

        transition_audio = transition_audio[b_cut:]
        final_mix = final_mix[:-max(0, a_cut)]
        final_mix += transition_audio

        # Clean up
        shutil.rmtree(transition_dir)

    final_mix.export(output_file, format="mp3")
    print(f"✅ Final mix saved to {output_file}")
