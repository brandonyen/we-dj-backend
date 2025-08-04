import yt_dlp
import os
from typing import List

def search_and_download(query, output_dir, cookie_path):
    search_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,
    }

    with yt_dlp.YoutubeDL(search_opts) as ydl:
        search_query = f"ytsearch1:{query}"
        info = ydl.extract_info(search_query, download=False)
        if not info or not info.get('entries'):
            print(f"No results found for query: {query}")
            return
        first_result = info['entries'][0]

    youtube_url = f"https://www.youtube.com/watch?v={first_result.get('id')}"

    download_opts = {
        'cookiefile': cookie_path,
        'format': 'bestaudio/best',
        'outtmpl': output_dir,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            },
        ],
        'prefer_ffmpeg': True,
        'quiet': False,
    }

    with yt_dlp.YoutubeDL(download_opts) as ydl:
        ydl.download([youtube_url])

def search_all(queries: List[str], output_path: str, cookie_path: str):
    paths = []

    for index, query in enumerate(queries):
        query = query + " official audio"
        song_path = os.path.join(output_path, str(index))
        search_and_download(query, song_path, cookie_path)
        paths.append(song_path + ".mp3")

    return paths