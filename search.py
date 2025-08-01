import yt_dlp
import os

def search_and_download_youtube_song(query, output_dir, cookie_path):
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
    song_title = first_result.get('title', 'Unknown Title')

    download_opts = {
        'cookiefile': cookie_path,
        'format': 'bestaudio/best',
        'outtmpl': f'{output_dir}/song.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'quiet': False,
    }

    with yt_dlp.YoutubeDL(download_opts) as ydl:
        ydl.download([youtube_url])
    
    return song_title