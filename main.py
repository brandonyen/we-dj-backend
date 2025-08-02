from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from supabase import create_client, Client
from connector import search_download, transition_songs
import tempfile
import base64
import asyncio
import random

app = FastAPI()
load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

cookie_b64 = supabase.storage.from_('transition-songs').download('cookies.b64')
cookie_path = "/tmp/youtube_cookies.txt"
with open(cookie_path, "wb") as f:
    f.write(base64.b64decode(cookie_b64))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://we-dj-proxy-production.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "We-DJ backend is running!"}

@app.get('/api/search_song')
async def search_song(query: str):
    return await asyncio.to_thread(_search_and_transition, query)

def _search_and_transition(query: str):
    with tempfile.TemporaryDirectory(prefix="transition_") as temp_dir:
        current_dir = os.path.join(temp_dir, "current_song")
        transition_dir = os.path.join(temp_dir, "transition_song")
        os.makedirs(current_dir, exist_ok=True)
        os.makedirs(transition_dir, exist_ok=True)

        current_song_name, transition_song_name = search_download(query, temp_dir, cookie_path)

        response = supabase.storage.from_('transition-songs').download(transition_song_name)
        transition_path = os.path.join(transition_dir, "song.mp3")
        with open(transition_path, "wb") as f:
            f.write(response)
        
        # Transition Type Random Selection
        def choose_weighted_transition(prob_dict):
            transitions = list(prob_dict.keys())
            weights = list(prob_dict.values())
            chosen_transition = random.choices(transitions, weights=weights, k=1)[0]
            return chosen_transition
        
        transitions_prob_dict = {
            'crossfade': 0.6,
            'scratch': 0.25,
            'crazy_scratch': 0.1,
            'steve': 0.05
        }
        transition_songs(temp_dir, choose_weighted_transition(transitions_prob_dict))

        final_mp3 = os.path.join(temp_dir, "dj_transition.mp3")

        final_temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        final_temp_path.close()
        os.rename(final_mp3, final_temp_path.name)

    response = FileResponse(
        path=final_temp_path.name,
        media_type="audio/mpeg",
        filename="dj_transition.mp3"
    )
        
    response.headers['X-Current-Song'] = current_song_name
    response.headers['X-Transition-Song'] = transition_song_name

    return response