from pytubefix import YouTube
import subprocess, os
url="https://www.youtube.com/watch?v=7aFDHEC5D8g"
yt=YouTube(url,use_oauth=False,allow_oauth_cache=False)
s=yt.streams.filter(progressive=True,file_extension="mp4").order_by("resolution").desc().first()
print("title",yt.title,"len",yt.length,"stream",s.resolution if s else None,flush=True)
if not s: raise RuntimeError("no progressive mp4")
s.download(filename="reference.mp4")
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","reference.mp4",
    "-vf","fps=1/5,scale=270:-2,tile=3x3","-frames:v","1","reference_contact.jpg"
],check=True)
# audio-only 15s sample for voice comparison
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","reference.mp4","-t","15",
    "-vn","-c:a","pcm_s16le","reference_audio.wav"
],check=True)
print(os.path.getsize("reference.mp4"))
