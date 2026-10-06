from gradio_client import Client
c=Client("hugging-apps/ltx25-multi-subject-reference")
print(c.view_api(return_format="dict"))
