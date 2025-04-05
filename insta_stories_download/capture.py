import sys
import json
import argparse
from InstaStory import InstaStory
from speech_recon import transcrever_video
import os

def process_video(path):
    """Helper function to handle speech recognition for videos"""
    transcription = None
    if path and os.path.exists(path):
        print(f"Processing speech recognition for {path}", file=sys.stderr)
        transcription = transcrever_video(path)
        if transcription:
            txt_path = os.path.splitext(path)[0] + ".txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(transcription)
            print(f"Saved transcription to {txt_path}", file=sys.stderr)
    return transcription

def main(username, cookies):
    # Download stories
    story_obj = InstaStory()
    story_obj.cookies = cookies
    story_obj.username = username
    stories = story_obj.story_download()
    
    processed_stories = []
    if stories and stories.get(username, {}).get('Story Data'):
        for item in stories[username]['Story Data']:
            if item['Link'].endswith('.mp4'):
                item['transcription'] = process_video(item['Link'])
            processed_stories.append(item)
    
    # Output JSON to stdout
    print(json.dumps(processed_stories))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--cookies", type=json.loads, required=True)
    args = parser.parse_args()
    
    main(args.username, args.cookies)