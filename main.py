from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from supabase import create_client, Client
from connector import search_download, transition_songs

app = FastAPI()
load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/api/search_song')
async def search_song(query: str):
    os.makedirs('temp/current_song', exist_ok=True)
    os.makedirs('temp/transition_song', exist_ok=True)
    current_song_name, transition_song_name = search_download(query)
    response = supabase.storage.from_('transition-songs').download(transition_song_name)
    with open('temp/transition_song/song.mp3', "wb") as f:
        f.write(response)
    transition_songs('./temp')