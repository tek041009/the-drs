from gradio_client import Client
spaces=[
    "Lightricks/LTX-2-Video-Fast",
    "Wan-AI/Wan2.1",
]
for s in spaces:
    print("\\nSPACE",s)
    try:
        c=Client(s)
        print(c.view_api(return_format="dict"))
    except Exception as e:
        print("ERR",repr(e))
