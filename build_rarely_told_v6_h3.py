import os, shutil, subprocess, time, urllib.request
from gradio_client import Client, handle_file
import soundfile as sf
from kokoro_onnx import Kokoro

SPACE="amisima/Minimax-H3-Studio-Turbo"
client=Client(SPACE)

STYLE=(
"Premium 2026 AI animated film quality. Natural cinematic human movement with stable anatomy and hands, "
"highly consistent face, detailed skin and fabric, physically believable weight and contact, rich materials, "
"soft global illumination, atmospheric depth, authentic 1920s Paris production design, cinematic lensing and camera motion. "
"No on-screen text, no subtitles, no watermark, no spoken dialogue; only natural period ambience and foley. "
)
VICTOR=(
"Victor Lustig: handsome European man in his late thirties, slim build, narrow oval face, neat dark pencil moustache, "
"dark brown hair beneath a charcoal fedora, tailored charcoal 1920s three-piece suit, cream shirt, muted gold tie, polished black shoes. "
)

PROMPTS=[
STYLE+VICTOR+(
"Fourteen-second continuous cinematic sequence in Paris, 1925. Begin on a gorgeous golden-hour boulevard with the Eiffel Tower framed between elegant Haussmann buildings, "
"authentic period cars and pedestrians moving naturally. The camera glides forward through traffic, then discovers Victor Lustig walking confidently toward camera. "
"The camera settles into a smooth backward tracking shot at chest height as he walks, his coat hem and tie moving in the breeze. "
"Finish by drifting into a refined three-quarter close-up as Victor gives a restrained, knowing half-smile. Natural city ambience, footsteps, distant engines."
),
STYLE+VICTOR+(
"Fourteen-second continuous cinematic sequence inside an elegant Paris cafe on a rainy morning in 1925. Victor sits alone at a small table beside a tall rain-streaked window, espresso steaming beside him. "
"A waiter enters naturally and places a folded French newspaper on the table. Victor reaches for it, unfolds it with realistic paper physics, scans the page, then his finger stops on an article about the Eiffel Tower's expensive maintenance. "
"The camera slowly dollies from a medium shot into a close-up across the newspaper toward his face. His expression changes almost imperceptibly from casual interest to focused calculation. "
"Outside the window, period cars and pedestrians move in the rain. Natural cafe ambience, paper rustle, porcelain clink, rain, no dialogue."
),
STYLE+VICTOR+(
"Two-second final close-up in the same Paris cafe. Victor looks from the maintenance article toward the Eiffel Tower visible beyond the rain-streaked window. "
"His eyes sharpen and a tiny calculating smile forms as the idea lands. Extremely stable identity, nuanced facial animation, very slow dramatic camera push-in. "
"End on intrigue, not a conclusion. Quiet cafe and rain ambience, no dialogue."
)
]

TURBO="larryvrh/MiniMax-H3-Turbo-Lora/minimax_h3_turbo_v4_step600_ema.safetensors"

def result_path(result):
    src=result[0] if isinstance(result,(tuple,list)) else result
    if isinstance(src,dict):
        src=src.get("path") or src.get("url")
    if not src:
        raise RuntimeError(f"No video returned: {result}")
    return src

def save_result(result,out):
    src=result_path(result)
    if str(src).startswith("http"):
        urllib.request.urlretrieve(src,out)
    else:
        shutil.copy2(src,out)

def generate(prompt, seconds, seed, out, identity=None):
    args=[
        prompt, None, None, "960x544 · 16:9 fast", float(seconds), 4, int(seed), False,
        TURBO, 1.0, "", 0.5, "", 0.5, "", 0.5, "", 0.5,
        handle_file(identity) if identity else None,
        "H3 first-frame identity", 0.65,
    ]
    last=None
    for attempt in range(1,4):
        try:
            print(f"Generating {out}, attempt {attempt}",flush=True)
            r=client.predict(*args,api_name="/generate")
            save_result(r,out)
            return
        except Exception as e:
            last=e
            print(f"Attempt failed: {e}",flush=True)
            if "quota" in str(e).lower():
                raise
            time.sleep(30*attempt)
    raise last

# Clip 1 establishes Victor.
generate(PROMPTS[0],14,1925,"clip1.mp4")

# Extract an identity portrait automatically; no human curation.
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-ss","10.0","-i","clip1.mp4",
    "-frames:v","1","-vf","crop=iw*0.50:ih*0.92:iw*0.25:ih*0.04,scale=768:-2",
    "-q:v","2","victor_identity.jpg"
],check=True)

# Clips 2 and 3 reuse the same identity reference.
generate(PROMPTS[1],14,2046,"clip2.mp4","victor_identity.jpg")
generate(PROMPTS[2],2,2171,"clip3.mp4","victor_identity.jpg")

# Normalize and join visual + generated ambience.
for i in (1,2,3):
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-i",f"clip{i}.mp4",
        "-vf","scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=24",
        "-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","160k","-ar","48000","-ac","2",
        f"norm{i}.mp4"
    ],check=True)

with open("concat.txt","w",encoding="utf-8") as f:
    for i in (1,2,3):
        f.write(f"file '{os.path.abspath(f'norm{i}.mp4')}'\n")
subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i","concat.txt","-t","30","-c","copy","visual_ambient.mp4"],check=True)

# Free Kokoro voice, already accepted as the Rarely Told narrator.
def dl(url,fn):
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

narration=(
"In 1925, one man managed to sell the Eiffel Tower. Not a souvenir. The actual tower. "
"His name was Victor Lustig, and he had a gift for making impossible lies sound completely reasonable. "
"One morning in Paris, he opened a newspaper and found a story complaining about the cost of maintaining the tower. "
"Most people would have read it and moved on. Lustig didn't."
)
k=Kokoro(model,voices)
v,sr=k.create(narration,voice="bm_george",speed=1.03,lang="en-gb")
sf.write("voice_raw.wav",v,sr)
duration=len(v)/sr
if duration>29.35:
    factor=duration/29.35
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i","voice_raw.wav","-filter:a",f"atempo={factor:.6f}","voice.wav"],check=True)
else:
    shutil.copy2("voice_raw.wav","voice.wav")

# Duck H3's native ambience beneath narration, preserving foley and environment.
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","visual_ambient.mp4","-i","voice.wav",
    "-filter_complex",
    "[0:a]volume=0.16[amb];[1:a]highpass=f=70,lowpass=f=15500,volume=1.05[vo];[amb][vo]amix=inputs=2:duration=first:dropout_transition=0[a]",
    "-map","0:v:0","-map","[a]","-t","30","-c:v","copy","-c:a","aac","-b:a","192k",
    "-movflags","+faststart","Rarely_Told_AI_First_30s_V6_H3.mp4"
],check=True)

print(subprocess.check_output([
    "ffprobe","-v","error","-show_entries","format=duration,size","-of","default=nw=1",
    "Rarely_Told_AI_First_30s_V6_H3.mp4"
]).decode())
