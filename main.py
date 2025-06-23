from flask import Flask, request, jsonify
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
import os
import tempfile
import uuid
import requests

app = Flask(__name__)

# Ensure necessary folders exist
os.makedirs("videos", exist_ok=True)
os.makedirs("mp3s", exist_ok=True)

@app.route("/")
def index():
    return "🎉 Birthday Video Generator is Live!"

@app.route("/webhook", methods=["POST"])
def make_video():
    try:
        data = request.json

        nickname = data.get("nickname", "Friend")
        song = data.get("song")
        photo_urls = data.get("photoURLs", "").split(",")
        bond_word = data.get("bondWord", "Bestie")

        if not song or not photo_urls:
            return jsonify({"error": "Missing song or photos"}), 400

        # Create image clips
        clips = []
        for url in photo_urls:
            response = requests.get(url)
            if response.status_code != 200:
                return jsonify({"error": f"Failed to fetch image: {url}"}), 400

            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            temp_img.write(response.content)
            temp_img.close()
            clip = ImageClip(temp_img.name).set_duration(4).resize(width=720)
            clips.append(clip)

        # Concatenate and add audio
        final_video = concatenate_videoclips(clips, method="compose")

        audio_path = f"mp3s/{song}.mp3"
        if not os.path.exists(audio_path):
            return jsonify({"error": f"Song '{song}.mp3' not found in mp3s folder."}), 404

        audio = AudioFileClip(audio_path).subclip(0, final_video.duration)
        final_video = final_video.set_audio(audio)

        # Output file path with unique name
        output_filename = f"videos/output_{uuid.uuid4().hex}.mp4"
        final_video.write_videofile(output_filename, fps=24, audio_codec='aac')

        return jsonify({
            "status": "success",
            "nickname": nickname,
            "bondWord": bond_word,
            "video_path": output_filename
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

