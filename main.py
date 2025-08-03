from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from connector import search_download, transition_songs
import tempfile
import uuid
import asyncio
import random
import shutil
import urllib.parse

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
        shutil.copyfile(transition_song, transition_path)
        
        # Transition Type Selection
        transition_songs(temp_dir, 'crossfade')

        folder_uuid = str(uuid.uuid4())
        uuid_folder = os.path.join("temp", folder_uuid)
        os.makedirs(uuid_folder, exist_ok=True)

        final_mp3 = os.path.join(temp_dir, "dj_transition.mp3")
        output_path = os.path.join(uuid_folder, "dj_transition.mp3")
        shutil.move(final_mp3, output_path)

    response = JSONResponse(content={
        "folder": folder_uuid,
        "current-song": urllib.parse.quote(current_song_name),
        "transition-song": urllib.parse.quote(transition_song_name)
    })
    
    return response

@app.get('/api/get_song')
def get_song(song_uuid: str):
    response = FileResponse(
        path=f'temp/{uuid}/dj_transition.mp3',
        media_type="audio/mpeg",
        filename="dj_transition.mp3"
    )

    return response