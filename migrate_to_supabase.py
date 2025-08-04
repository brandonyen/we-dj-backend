import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(url, key)

df = pd.read_csv("song_metadata.csv")
rows = df.to_dict(orient="records")

for row in rows:
    data = {
        "filename": row.get("filename"),
        "bpm": row.get("bpm"),
        "camelot_key": row.get("camelot_key"),
        "loudness": row.get("loudness"),
        "energy": row.get("energy")
    }
    supabase.table("songs").upsert(data, on_conflict="filename").execute()
