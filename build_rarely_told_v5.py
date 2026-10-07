import os, shutil, subprocess, time, urllib.request
from gradio_client import Client
import soundfile as sf
from kokoro_onnx import Kokoro

SPACE="ChopperBlu/ltx-2-5-demo"
client=Client(SPACE)

STYLE=(
"Current-generation 2026 cinematic stylized 3D animated feature-film quality. "
"Polished realistic proportions, stable anatomy and hands, coherent faces, detailed skin and cloth, rich materials, "
"physically believable weight and contact, smooth deliberate camera motion, soft global illumination, atmospheric depth, "
"cinematic depth of field, authentic 1920s Paris production design, crisp coherent geometry, natural secondary motion. "
"No on-screen text, no subtitles, no watermark, no logos. "
)

VICTOR=(
"Victor Lustig is the same recurring character in every shot: a handsome European man in his late thirties, slim build, "
"narrow oval face, neat dark pencil moustache, dark brown hair beneath a charcoal fedora, tailored charcoal 1920s three-piece suit, "
"cream shirt, muted gold tie, polished black shoes. "
)

PROMPTS={
1: STYLE+(
"Wide establishing shot of Paris in 1925 at golden hour. The Eiffel Tower dominates the skyline beyond a lively Haussmann boulevard. "
"Authentic 1920s cars roll through traffic, pedestrians cross naturally, cafe awnings and coats move subtly in the breeze, warm light glints off damp stone. "
"The camera performs a smooth slow crane-and-dolly forward toward the Eiffel Tower. Grand, intriguing, richly detailed and grounded."
),
2: STYLE+VICTOR+(
"Victor walks confidently toward camera down a lively Paris boulevard. Period cars move naturally behind him, pedestrians weave around him, "
"shop windows glow and the Eiffel Tower sits softly in the distant haze. The camera tracks backward smoothly at chest height. "
"His face stays stable and detailed; his coat hem and tie move naturally; feet contact the pavement correctly; his expression is calm and self-assured."
),
3: STYLE+VICTOR+(
"Inside an opulent 1920s Paris hotel lounge, Victor calmly charms two wealthy businessmen in tailored suits. "
"He uses measured natural hand gestures while they listen closely, then gives a restrained knowing half-smile. "
"Marble, brass, art deco lamps and polished floors; background guests move naturally. Slow elegant circular camera move around the group."
),
4: STYLE+VICTOR+(
"Medium close tracking shot of Victor leaving the grand hotel and moving through an upscale Paris crowd. "
"He adjusts one cuff with practiced confidence, briefly studies the people around him and gives a faint knowing smile. "
"Elegant facades and warm shop windows slide by in deep parallax. Smooth lateral dolly, stable face, believable walking motion."
),
5: STYLE+VICTOR+(
"Morning in an elegant Paris cafe beside a large rain-streaked window. Victor sits alone at a small wooden table with an espresso. "
"A waiter enters frame and places a folded French newspaper onto the table. Victor reaches for it naturally. "
"Outside, pedestrians and 1920s cars move through soft morning rain. Intimate cinematic dolly-in with realistic object contact."
),
6: STYLE+VICTOR+(
"Close cinematic shot at Victor's cafe table. Victor unfolds a large 1920s newspaper and scans the page carefully. "
"His finger pauses on one important article. The paper flexes and folds realistically in his hands, coffee steam curls beside it, "
"and background patrons move softly out of focus. Slow camera push from the newspaper toward Victor's focused eyes. No readable newspaper text."
),
7: STYLE+VICTOR+(
"Tight close-up on Victor at the cafe. His expression changes almost imperceptibly from casual interest to focused calculation. "
"His eyes lift from the newspaper toward the rain-streaked window where the Eiffel Tower is visible in the distance. "
"A restrained half-smile begins. Very slow dramatic push-in, nuanced facial animation, stable identity and natural eye movement."
),
8: STYLE+VICTOR+(
"Over-the-shoulder cinematic shot from behind Victor at the cafe table. The Eiffel Tower is framed through the rain-streaked window beyond him. "
"Victor lowers the newspaper slightly, studies the tower, then glances back to the paper and gives the tiniest calculating smile as the idea lands. "
"Camera glides gently from the newspaper toward the tower and settles on Victor's profile. End on intrigue, not a conclusion."
),
}

def save_result(result,out):
    src=result[0] if isinstance(result,(tuple,list)) else result
    if isinstance(src,dict):
        src=src.get("path") or src.get("url")
    if not src:
        raise RuntimeError(f"No path returned: {result}")
    if str(src).startswith("http"):
        urllib.request.urlretrieve(src,out)
    else:
        shutil.copy2(src,out)

def generate(idx):
    # Same deterministic seed across Victor shots helps stabilise the recurring character.
    seed=1925 if idx >= 2 else 1907
    last=None
    for attempt in range(1,4):
        try:
            print(f"Generating story shot {idx}, attempt {attempt}",flush=True)
            result=client.predict(
                PROMPTS[idx],
                None,
                1024,
                576,
                4.0,
                False,
                seed,
                False,
                "diffusion",
                api_name="/generate_video",
            )
            save_result(result,f"raw_{idx}.mp4")
            return
        except Exception as e:
            last=e
            print(f"Shot {idx} attempt {attempt} failed: {e}",flush=True)
            # Respect explicit quota/capacity errors; don't hammer or evade them.
            msg=str(e).lower()
            if "quota" in msg or "maximum allowed" in msg or "subscribe" in msg:
                raise
            if attempt < 3:
                time.sleep(25*attempt)
    raise last

for idx in range(1,9):
    generate(idx)

# Normalize the eight 4-second AI-generated shots.
for idx in range(1,9):
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-i",f"raw_{idx}.mp4",
        "-vf","scale=1280:720:flags=lanczos,fps=24",
        "-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","160k","-ar","48000","-ac","2",
        f"shot_{idx}.mp4"
    ],check=True)

with open("concat.txt","w",encoding="utf-8") as f:
    for idx in range(1,9):
        f.write(f"file '{os.path.abspath(f'shot_{idx}.mp4')}'\n")

subprocess.run([
    "ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i","concat.txt",
    "-t","30","-c:v","copy","-c:a","aac","-b:a","160k","visual_ambient.mp4"
],check=True)

# Free local Kokoro narrator.
def dl(url,fn):
    req=urllib.request.Request(url,headers={"User-Agent":"RarelyTold/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as w:
        while True:
            c=r.read(1024*1024)
            if not c: break
            w.write(c)

model="kokoro-v1.0.int8.onnx"
voices="voices-v1.0.bin"
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
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-i","voice_raw.wav",
        "-filter:a",f"atempo={factor:.6f}","voice.wav"
    ],check=True)
else:
    shutil.copy2("voice_raw.wav","voice.wav")

# Retain a little native generated ambience beneath the already-approved narrator.
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","visual_ambient.mp4","-i","voice.wav",
    "-filter_complex",
    "[0:a]volume=0.13[amb];[1:a]highpass=f=70,lowpass=f=15500,volume=1.05[vo];[amb][vo]amix=inputs=2:duration=first:dropout_transition=0[a]",
    "-map","0:v:0","-map","[a]","-t","30",
    "-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",
    "Rarely_Told_AI_First_30s_V5_CurrentGen.mp4"
],check=True)

print(subprocess.check_output([
    "ffprobe","-v","error","-show_entries","format=duration,size","-of","default=nw=1",
    "Rarely_Told_AI_First_30s_V5_CurrentGen.mp4"
]).decode())
