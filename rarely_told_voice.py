import urllib.request, soundfile as sf, subprocess, os
from kokoro_onnx import Kokoro

def dl(url, fn):
    req=urllib.request.Request(url,headers={"User-Agent":"RarelyTold/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as w:
        while True:
            c=r.read(1024*1024)
            if not c: break
            w.write(c)

model="kokoro-v1.0.int8.onnx"; voices="voices-v1.0.bin"
if not os.path.exists(model):
    dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",model)
if not os.path.exists(voices):
    dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",voices)

script=("In 1925, one man managed to sell the Eiffel Tower. Not a souvenir. The actual tower. "
        "His name was Victor Lustig, and he had a talent for making impossible lies sound completely reasonable. "
        "Then, one morning in Paris, he noticed a newspaper story complaining about how expensive the Eiffel Tower was becoming to maintain. "
        "Most people would have read it and moved on. Lustig saw something else: an opportunity.")

k=Kokoro(model,voices)
a,sr=k.create(script,voice="bm_george",speed=1.06,lang="en-gb")
sf.write("voice_raw.wav",a,sr)
dur=len(a)/sr
if dur>29.2:
    factor=dur/29.2
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i","voice_raw.wav","-filter:a",f"atempo={factor:.6f}","rarely_told_voice.wav"],check=True)
else:
    os.replace("voice_raw.wav","rarely_told_voice.wav")
