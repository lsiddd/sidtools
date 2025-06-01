# insta_stories_download/

This directory contains Python scripts for downloading Instagram stories and performing optional speech recognition on video stories. The core functionality involves fetching story data using provided authentication cookies and saving the media locally.

## Contents:

*   `InstaStory.py`: Defines the core class for handling the process of fetching and downloading Instagram story media and metadata. It requires cookie data for authentication.
*   `capture.py`: A command-line script that utilizes the `InstaStory` class to download stories for a specified user and optionally processes video stories to transcribe audio using the `speech_recon.py` module. It outputs processed story data, including local file paths and transcriptions, as JSON.
*   `speech_recon.py`: A helper module that extracts audio from video files and uses a speech recognition service (Google Speech Recognition by default) to generate a text transcription.

## Dependencies:

*   `InstaStory.py` depends on: `requests`, `lxml`, `pytz`, `datetime`, `json`, `os`.
*   `capture.py` depends on: `InstaStory`, `speech_recon`, `sys`, `json`, `argparse`, `os`.
*   `speech_recon.py` depends on: `speech_recognition`, `moviepy`, `sys`, `os`.

You will need to install these Python libraries using pip:

```bash
pip install requests lxml pytz speech_recognition moviepy
# moviepy might require additional system dependencies like ffmpeg
```

## Usage:

The primary entry point for command-line use is `capture.py`. It requires the target Instagram username and authentication cookies.

```bash
python insta_stories_download/capture.py <username> --cookies '<cookies_json_string>'
```

*   `<username>`: The Instagram username to fetch stories for.
*   `'<cookies_json_string>'`: A string containing your Instagram cookies, typically as a JSON object. This is **required** for successful downloads, especially for private accounts. Example: `'{"sessionid": "YOUR_SESSION_ID", "ds_user_id": "YOUR_USER_ID", ...}'`.

The `capture.py` script will download stories to a `./story/<username>/` directory and print the story data (including paths to downloaded media and video transcriptions) as a JSON array to standard output. Status and error messages are printed to standard error.

The `InstaStory.py` and `speech_recon.py` files can also be imported and used as modules in other Python scripts.

