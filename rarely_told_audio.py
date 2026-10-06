import os, urllib.request, subprocess
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

def dl(url,fn):
    req=urllib.request.Request(url,headers={"User-Agent":"RarelyTold/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as w:
        while True:
            c=r.read(1024*1024)
            if not c: break
            w.write(c)

model="kokoro-v1.0.int8.onnx"; voices="voices-v1.0.bin"
if not os.path.exists(model): dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",model)
if not os.path.exists(voices): dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",voices)

script=("In 1925, one man managed to sell the Eiffel Tower. Not a souvenir. The actual tower. "
"His name was Victor Lustig, and he had a talent for making impossible lies sound completely reasonable. "
"Then, one morning in Paris, he noticed a newspaper story complaining about how expensive the Eiffel Tower was becoming to maintain. "
"Most people would have read it and moved on. Lustig saw something else: an opportunity.")

k=Kokoro(model,voices)
v,sr=k.create(script,voice="bm_george",speed=1.03,lang="en-gb")
sf.write("voice.wav",v,sr)
N=sr*30; t=np.arange(N)/sr
rng=np.random.default_rng(11)
# cinematic but subtle original score
bed=(.008*np.sin(2*np.pi*49*t)+.005*np.sin(2*np.pi*73.5*t)+.0025*np.sin(2*np.pi*98*t)).astype(np.float32)
bed*=.55+.45*np.sin(2*np.pi*.045*t+.4)**2
mix=bed
for sec in [0,5.0,9.0,18.8,27.0]:
    i=int(sec*sr); L=min(int(.65*sr),N-i); tt=np.arange(L)/sr
    mix[i:i+L]+=0.045*np.sin(2*np.pi*42*tt)*np.exp(-5.5*tt)
for sec in [6.2,10.8,18.6,22.0]:
    i=int(sec*sr); L=min(int(.35*sr),N-i); tt=np.arange(L)/sr
    who=rng.normal(0,1,L)*np.sin(np.pi*np.clip(tt/.35,0,1))**2*.012
    mix[i:i+L]+=who
vv,vsr=sf.read("voice.wav",dtype="float32")
if vsr!=sr: raise RuntimeError("sr mismatch")
if len(vv)>N:
    sf.write("voice_tmp.wav",vv,sr)
    factor=len(vv)/(N-.15*sr)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i","voice_tmp.wav","-filter:a",f"atempo={factor:.6f}","voice_fit.wav"],check=True)
    vv,_=sf.read("voice_fit.wav",dtype="float32")
mix[:min(len(vv),N)]+=vv[:N]*.96
mx=np.max(np.abs(mix))
if mx>.97: mix*=.97/mx
sf.write("mix.wav",mix,sr)
