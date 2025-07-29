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

extract_chorus('./temp/current_song/song.mp3', './temp/current_song/chorus.mp3')
split_audio('./temp/current_song/chorus.mp3', './temp/current_song')