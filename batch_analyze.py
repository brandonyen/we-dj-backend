import os
import csv
import sys
from analyze import analyze_song

def analyze_folder(folder_path, output_csv):
    results = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
                print(f"Analyzing {file_path}...")
                try:
                    features = analyze_song(file_path)
                    # Remove key and scale if present
                    features.pop('key', None)
                    features.pop('scale', None)
                    features['filename'] = file
                    results.append(features)
                except Exception as e:
                    print(f"Error processing {file}: {e}")

    with open(output_csv, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['filename', 'bpm', 'camelot_key', 'loudness'])
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"\nAnalysis complete. Results saved to {output_csv}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python batch_analyze_to_csv.py <folder_path> <output_csv>")
        sys.exit(1)

    folder = sys.argv[1]
    csv_out = sys.argv[2]
    analyze_folder(folder, csv_out)
