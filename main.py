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
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
import traceback

@app.get('/api/search_song')
async def search_song(query: str, request: Request):
    try:
        print("⏳ Starting download/transition")
        with tempfile.TemporaryDirectory(prefix="transition_") as temp_dir:
            current_dir = os.path.join(temp_dir, "current_song")
            transition_dir = os.path.join(temp_dir, "transition_song")
            os.makedirs(current_dir, exist_ok=True)
            os.makedirs(transition_dir, exist_ok=True)

            print(f"🔍 Searching for: {query}")
            current_song_name, transition_song_name = search_download(query, temp_dir)
            print(f"🎶 Songs found: {current_song_name}, {transition_song_name}")

            response = supabase.storage.from_('transition-songs').download(transition_song_name)
            transition_path = os.path.join(transition_dir, "song.mp3")
            with open(transition_path, "wb") as f:
                f.write(response)

            print("🎛️ Transitioning songs...")
            transition_songs(temp_dir, 'crossfade')
            final_mp3 = os.path.join(temp_dir, "dj_transition.mp3")

            final_temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            final_temp_path.close()
            os.rename(final_mp3, final_temp_path.name)

        file_response = FileResponse(
            path=final_temp_path.name,
            media_type="audio/mpeg",
            filename="dj_transition.mp3"
        )
        file_response.headers['X-Current-Song'] = current_song_name
        file_response.headers['X-Transition-Song'] = transition_song_name
        return file_response

    except Exception as e:
        print("🔥 Error in /api/search_song")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))