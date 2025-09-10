# Multimodal-Search-and-RAG
This repo contains two standalone scripts you can run from PyCharm on Windows:
Part A — Invoice → JSON (Gemini): send an image (e.g., an invoice PNG/JPG) to Google’s Gemini API and get back clean JSON with line items.
Part B — Multimodal Search (Weaviate Embedded): build a local vector DB that indexes images and videos using Google’s multimodal embeddings
, then run similarity search via text, image, or video queries.


Quick start

1)Clone / open the project in PyCharm.

2)Create a file named .env next to your Python files (do not commit this file).

3)Install the required packages (PyCharm → Terminal):

python -m pip install -U google-generativeai google-api-core python-dotenv Pillow
python -m pip install -U "weaviate-client[embedded]" python-dotenv Pillow requests (part B)

4)Add your API keys to .env 

GOOGLE_API_KEY=AIza...<your_gemini_api_key>...

5)Run each script from PyCharm (Run → Run '... '). See the per-part sections below.

Note: API keys come from Google AI Studio (https://ai.google.dev → API keys). Do not use GCP/Vertex-only keys.
