from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from supabase import create_client, Client
from connector import search_download, transition_songs
import tempfile

app = FastAPI()
load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
if SUPABASE_URL is None:
    raise RuntimeError("SUPABASE_URL is not set!")
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
    with tempfile.TemporaryDirectory(prefix="transition_") as temp_dir:
        current_dir = os.path.join(temp_dir, "current_song")
        transition_dir = os.path.join(temp_dir, "transition_song")
        os.makedirs(current_dir, exist_ok=True)
        os.makedirs(transition_dir, exist_ok=True)

        current_song_name, transition_song_name = search_download(query, temp_dir)

        response = supabase.storage.from_('transition-songs').download(transition_song_name)
        transition_path = os.path.join(transition_dir, "song.mp3")
        with open(transition_path, "wb") as f:
            f.write(response)

        transition_songs(temp_dir, 'crossfade')

        final_mp3 = os.path.join(temp_dir, "dj_transition.mp3")

        # Copy the file to a temp path outside the context manager
        # because FileResponse streams the file *after* returning
        final_temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        final_temp_path.close()
        os.rename(final_mp3, final_temp_path.name)

    return FileResponse(
        path=final_temp_path.name,
        media_type="audio/mpeg",
        filename="dj_transition.mp3"
    )