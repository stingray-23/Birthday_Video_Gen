from flask import Flask, request, jsonify
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
import os
import tempfile
import uuid
import random
import requests
import smtplib
from email.message import EmailMessage

app = Flask(__name__, static_url_path='/videos', static_folder='videos')

# Email credentials (secure with environment variables on Render)
EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

os.makedirs("videos", exist_ok=True)
os.makedirs("mp3s", exist_ok=True)

@app.route("/")
def home():
    return "🎉 Birthday Video Generator is Live!"

@app.route("/webhook", methods=["POST"])
def make_video():
    print("Request received:", request.json)
    try:
        print("=== Received /webhook call ===")
        print("Raw data:", request.data)
        print("JSON data:", request.json)

        data = request.json

        # Extract form data
        nickname = data.get("nickname", "Friend")
        song = data.get("songChoice")
        photo_urls = data.get("photoURLs", "").split(",")
        meeting_place = data.get("meetingPlace", "")
        movie_title = data.get("movieTitle", "")
        color = data.get("colorChoice", "white")
        emoji = data.get("emoji", "🎉")
        bond_word = data.get("bondWord", "Bestie")
        recipient_email = data.get("email")
        
        if not song or not photo_urls or photo_urls == [""]:
            return jsonify({"error": "Missing song or photos"}), 400

        clips = []

        min_total_duration = 45  # seconds
        num_images = len(photo_urls)
        duration_per_image = max(4, min(8, min_total_duration // max(num_images, 1)))

        for i, url in enumerate(photo_urls):
            response = requests.get(url)
            if response.status_code != 200:
                return jsonify({"error": f"Failed to fetch image: {url}"}), 400

            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            temp_img.write(response.content)
            temp_img.close()

            img_clip = ImageClip(temp_img.name).set_duration(duration_per_image).resize(width=720)

            txt_overlays = []

            # First image → Intro message
            if i == 0:
                text = f"Happy Birthday {nickname} {emoji}"
                txt = TextClip(text, fontsize=60, color=color, font="Arial-Bold")
                txt = txt.set_position(("center", "bottom")).set_duration(duration_per_image)
                txt_overlays.append(txt)

            # Second image → Meeting place
            if i == 1 and meeting_place:
                txt = TextClip(f"Where we met: {meeting_place}", fontsize=40, color=color, font="Arial")
                txt = txt.set_position(("center", "top")).set_duration(duration_per_image)
                txt_overlays.append(txt)

            # Last image → Movie title
            if i == len(photo_urls) - 1 and movie_title:
                txt = TextClip(movie_title, fontsize=50, color=color, font="Arial-Italic")
                txt = txt.set_position(("center", "center")).set_duration(duration_per_image)
                txt_overlays.append(txt)

            # Emoji on every image
            emoji_txt = TextClip(emoji, fontsize=40, color=color)
            emoji_txt = emoji_txt.set_position(("right", "bottom")).set_duration(duration_per_image)
            txt_overlays.append(emoji_txt)

            comp = CompositeVideoClip([img_clip] + txt_overlays)
            clips.append(comp.crossfadein(random.uniform(0.8, 1.2)))


        # Final birthday message
        final_text = f"You’ll always be my {bond_word} ❤️"
        txt_clip = TextClip(final_text, fontsize=60, color=color, font="Arial-Bold")
        txt_clip = txt_clip.set_position("center").set_duration(3)
        final_clip = CompositeVideoClip([txt_clip.on_color(size=(720, 480), color=(0, 0, 0))])
        clips.append(final_clip)

        final_video = concatenate_videoclips(clips, method="compose")

        # Add music
        audio_path = f"mp3s/{song}.mp3"
        if not os.path.exists(audio_path):
            return jsonify({"error": f"Song '{song}.mp3' not found in mp3s folder."}), 404

        audio = AudioFileClip(audio_path).subclip(0, final_video.duration)
        final_video = final_video.set_audio(audio)

        # Export video
        output_path = f"videos/output_{uuid.uuid4().hex}.mp4"
        video_url = f"https://birthday-video-gen.onrender.com/{output_path}"
        final_video.write_videofile(output_path, fps=24, audio_codec="aac")

        if recipient_email:
            send_email(recipient_email, nickname, video_url)

        return jsonify({
            "status": "success",
            "video_url": video_url
        })


    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
def send_email(to_email, nickname, video_url):
    msg = EmailMessage()
    msg['Subject'] = "🎉 Your Personalized Birthday Video!"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email

    msg.set_content(f"""
Hi {nickname}! 💖

Your personalized birthday surprise video is ready!

🎬 Watch it here: {video_url}

We hope it brings a smile to your face. Enjoy your special day! 🎂🎁
""")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

