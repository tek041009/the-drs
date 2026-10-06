from gradio_client import Client
c=Client("ChopperBlu/ltx-2-5-demo")
print(c.view_api(return_format="dict"))
