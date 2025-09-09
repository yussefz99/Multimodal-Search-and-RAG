import warnings
import os

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