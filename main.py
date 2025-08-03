from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from connector import search_download, transition_songs
import tempfile
import base64
import asyncio
import random
import shutil

app = FastAPI()
load_dotenv()

FRONTEND_URL = os.environ.get('FRONTEND_URL')

cookie_path = 'cookies.txt'

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
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
        transition_song_name = f"{transition_song_name}.mp3"
        current_song_name = f"{current_song_name}.mp3"

        transition_song = os.path.join('songs', transition_song_name)
        transition_path = os.path.join(transition_dir, "song.mp3")
        with open(transition_path, "wb") as f:
            f.write(response)
        

        # Transition Type Selection
        transition_songs(temp_dir, 'crossfade')

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
