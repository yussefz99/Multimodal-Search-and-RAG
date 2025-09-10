import warnings
import os
import textwrap
import PIL.Image

warnings.filterwarnings("ignore")


from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")

import google.generativeai as genai
from google.api_core.client_options import ClientOptions
genai.configure(
    api_key=GOOGLE_API_KEY,
    transport="rest",
    client_options=ClientOptions(
        api_endpoint=os.getenv("GOOGLE_API_BASE"),
    )
)


def call_LMM(image_path: str, prompt: str) -> str:
    img = PIL.Image.open(image_path)

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([prompt, img], stream=False)
    response.resolve()
    return response.text


from pathlib import Path
IMG = Path(__file__).resolve().parent / "invoice_sample.png"

result=call_LMM(str(IMG),
    """Identify items on the invoice, Make sure you output 
    JSON with quantity, description, unit price and ammount.""")

print(result)  # <-- this actually prints to the Run consol




