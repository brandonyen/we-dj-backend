from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import os
from connector import search_download, transition_songs
import tempfile
import uuid
import asyncio
import shutil
import urllib.parse
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from typing import List
from supabase import create_client, Client
from playlist.connector_playlist import connector_playlist

app = FastAPI()
load_dotenv()

FRONTEND_URL = os.environ.get('FRONTEND_URL')
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')

supabase: Client = create_client(url, key)

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
async def search_song(query: str, transition_type='crossfade'):
    return await asyncio.to_thread(_search_and_transition, query, transition_type)

def extract_thumbnail(mp3_path, output_image_path):
    audio = MP3(mp3_path, ID3=ID3)

    if audio.tags is None:
        print("No ID3 tags found.")
        return

    for tag in audio.tags.values():
        if isinstance(tag, APIC):
            with open(output_image_path, 'wb') as img:
                img.write(tag.data)
            print(f"Thumbnail saved to {output_image_path}")
            return
    
    print("No embedded thumbnail found.")

def _search_and_transition(query: str, transition_type: str):
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
        transition_songs(temp_dir, transition_type)

        folder_uuid = str(uuid.uuid4())
        uuid_folder = os.path.join("temp", folder_uuid)
        os.makedirs(uuid_folder, exist_ok=True)

        extract_thumbnail(current_dir + "/song.mp3", os.path.join(uuid_folder, "current.jpg"))
        extract_thumbnail(transition_dir + "/song.mp3", os.path.join(uuid_folder, "transition.jpg"))

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
    return FileResponse(
        path=f'temp/{song_uuid}/dj_transition.mp3',
        media_type="audio/mpeg",
        filename="dj_transition.mp3"
    )

@app.get('/api/get_thumbnail')
def get_thumbnail(song_uuid: str, thumbnail_type: str):
    return FileResponse(f'temp/{song_uuid}/{thumbnail_type}.jpg', media_type="image/jpeg")

@app.get('/api/get_all_songs')
def get_all_songs():
    response = supabase.table("songs").select("filename").execute()
    filenames = [item["filename"] for item in response.data]
    return filenames

@app.post('/api/delete_songs')
async def delete_songs(request: Request):
    data = await request.json()
    song_ids: List[str] = data.get("song_ids", [])

    not_deleted = []

    for song_id in song_ids:
        file_path = os.path.join('songs', song_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                not_deleted.append(song_id)
        else:
            not_deleted.append(song_id)

    for sid in song_ids:
        supabase.table("songs").delete().eq("filename", sid).execute()

    return {"not_deleted": not_deleted}

@app.post('/api/create_playlist')
async def create_playlist(request: Request):
    data = await request.json()
    tracks: List[str] = data.get("songs", [])
    return connector_playlist(tracks)

@app.get('/api/get_playlist')
async def get_playlist(playlist_uuid: str):
    return FileResponse(
        path=f'playlist/temp/{playlist_uuid}/playlist_transition.mp3',
        media_type="audio/mpeg",
        filename="playlist_transition.mp3"
    )