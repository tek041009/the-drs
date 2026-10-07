import json, os, urllib.request
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

def dl(url,fn):
    if os.path.exists(fn): return
    req=urllib.request.Request(url,headers={"User-Agent":"RarelyTold/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as w:
        while True:
            c=r.read(1024*1024)
            if not c: break
            w.write(c)

model="kokoro-v1.0.int8.onnx"
voices="voices-v1.0.bin"
dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",model)
dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",voices)

lines=[
"In 1925, a con man convinced a businessman to buy the Eiffel Tower for scrap.",
"Victor Lustig had read reports that the tower was expensive to maintain.",
"So he posed as a French government official, forged ministry stationery, and summoned Paris scrap dealers to a luxury hotel.",
"He told them the government planned to dismantle the tower — but the sale had to stay secret.",
"One dealer, André Poisson, believed him. He paid.",
"Lustig took the money and fled Paris.",
"And when no one reported the scam, he came back and tried to sell the Eiffel Tower again."
]

k=Kokoro(model,voices)
parts=[]
marks=[]
cursor=0.0
sr_ref=None
gap=0.16
for i,line in enumerate(lines):
    v,sr=k.create(line,voice="bm_george",speed=1.07,lang="en-gb")
    sr_ref=sr
    start=cursor
    end=start+len(v)/sr
    marks.append({"index":i+1,"text":line,"start":round(start,3),"end":round(end,3)})
    parts.append(v.astype(np.float32))
    if i < len(lines)-1:
        silence=np.zeros(int(gap*sr),dtype=np.float32)
        parts.append(silence)
        cursor=end+gap
    else:
        cursor=end

mix=np.concatenate(parts)
sf.write("Rarely_Told_Eiffel_Voice.wav",mix,sr_ref)
with open("voice_timing.json","w",encoding="utf-8") as f:
    json.dump({"duration":round(len(mix)/sr_ref,3),"segments":marks},f,indent=2,ensure_ascii=False)
print(json.dumps({"duration":len(mix)/sr_ref,"segments":marks},ensure_ascii=False))
