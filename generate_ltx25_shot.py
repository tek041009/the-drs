from gradio_client import Client
import os, shutil

client=Client("ChopperBlu/ltx-2-5-demo")
prompt=(
"High-end 2026 cinematic stylized 3D animation, 1925 Paris at golden hour. "
"A wide establishing shot reveals the Eiffel Tower above a lively boulevard with authentic 1920s cars, pedestrians, cafe awnings, soft atmospheric haze and warm sunlight. "
"The camera performs a smooth slow crane-and-dolly forward toward the tower. "
"Everything has physically believable motion and weight: cars roll naturally, people walk with stable anatomy, fabric and awnings move subtly in the breeze, realistic shadows and reflections. "
"Premium feature-film quality, rich materials, crisp facial and environmental detail, coherent geometry, cinematic depth of field, no text, no watermark."
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
