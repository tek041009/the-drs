from gradio_client import Client
import os, shutil

client=Client("ChopperBlu/ltx-2-5-demo")
prompt=(
"High-end 2026 cinematic stylized 3D animated feature-film shot set in Paris, 1925. "
"Victor Lustig is a handsome European man in his late thirties with a slim build, narrow oval face, neat dark pencil moustache, dark brown hair beneath a charcoal fedora, tailored charcoal 1920s three-piece suit, cream shirt, muted gold tie and polished black shoes. "
"He walks confidently toward camera down a lively Paris boulevard. Authentic 1920s cars move naturally behind him, pedestrians cross around him, warm shop windows glow, and the Eiffel Tower sits softly in the hazy distance. "
"The camera tracks backward smoothly at chest height as he walks. His face remains stable and detailed, coat and tie move naturally, feet contact the pavement correctly, hands remain anatomically coherent. "
"Premium theatrical 3D animation, rich materials, realistic proportions, nuanced expression, soft global illumination, atmospheric depth, cinematic depth of field, crisp coherent geometry, physically believable motion, no text, no watermark."
)
result=client.predict(
    prompt,
    None,
    1024,
    576,
    4.0,
    False,
    1925,
    False,
    "diffusion",
    api_name="/generate_video",
)
print("RESULT",result)
video=result[0]
if isinstance(video, dict):
    path=video.get("path") or video.get("url")
else:
    path=video
if not path:
    raise RuntimeError("no video path returned")
if str(path).startswith("http"):
    import urllib.request
    urllib.request.urlretrieve(path,"Rarely_Told_V5_Shot1.mp4")
else:
    shutil.copy2(path,"Rarely_Told_V5_Shot1.mp4")
print("saved",os.path.getsize("Rarely_Told_V5_Shot1.mp4"))
