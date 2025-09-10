import warnings, os, json, base64, sys, subprocess
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from weaviate.classes.config import Configure
import weaviate
import requests

warnings.filterwarnings("ignore")

# ---------------- ENV & PATHS ----------------
# Load .env reliably from this file's folder
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(find_dotenv(usecwd=True))  # also loads if you run from project root
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

EMBEDDING_API_KEY = (os.getenv("EMBEDDING_API_KEY") or "").strip().strip('"').strip("'")
if not EMBEDDING_API_KEY:
    raise RuntimeError("EMBEDDING_API_KEY missing. Add it to .env next to main.py")

BACKUP_DIR = (BASE_DIR / "backups")
BACKUP_DIR.mkdir(exist_ok=True)

IMG_DIR = BASE_DIR / "source" / "image"
VID_DIR = BASE_DIR / "source" / "video"
TEST_DIR = BASE_DIR / "test"
IMG_DIR.mkdir(parents=True, exist_ok=True)
VID_DIR.mkdir(parents=True, exist_ok=True)
TEST_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- CLIENT (EMBEDDED) ----------------
# Use Windows-friendly backup path; enable multi2vec-palm module
client = weaviate.connect_to_embedded(
    version="1.24.21",
    environment_variables={
        "ENABLE_MODULES": "backup-filesystem,multi2vec-palm",
        "BACKUP_FILESYSTEM_PATH": str(BACKUP_DIR.as_posix()),
    },
    headers={
        "X-PALM-Api-Key": EMBEDDING_API_KEY,
    }
)

if not client.is_ready():
    raise RuntimeError("Weaviate embedded failed to start or isn't ready.")

# Clean up old collection if present
if client.collections.exists("Animals"):
    client.collections.delete("Animals")

# Create collection with multimodal vectorizer (image+video fields)
client.collections.create(
    name="Animals",
    vectorizer_config=Configure.Vectorizer.multi2vec_palm(
        image_fields=["image"],
        video_fields=["video"],
        project_id="semi-random-dev",
        location="us-central1",
        model_id="multimodalembedding@001",
        dimensions=1408,
    )
)
animals = client.collections.get("Animals")

# ---------------- HELPERS ----------------
def file_to_base64(path: Path) -> str:
    with path.open("rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def url_to_base64(url: str) -> str:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return base64.b64encode(r.content).decode("utf-8")

def json_print(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))

def open_with_os(p: Path) -> None:
    """Open a file with default OS app (works from PyCharm)."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(p)], check=False)
        else:
            subprocess.run(["xdg-open", str(p)], check=False)
    except Exception as e:
        print(f"[Could not open {p}] {e}")

# ---------------- INGEST IMAGES (BATCH) ----------------
# NOTE: your original code listed ./source/animal_image/ but read from ./source/image/.
# We standardize to ./source/image/.
image_files = [p for p in IMG_DIR.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]

if not image_files:
    print(f"[Info] Put some images into: {IMG_DIR} (png/jpg/webp)")
else:
    with animals.batch.rate_limit(requests_per_minute=100) as batch:
        for p in image_files:
            print(f"Adding image: {p.name}")
            try:
                batch.add_object({
                    "name": p.name,
                    "path": str(p),
                    "image": file_to_base64(p),   # vectorized via multi2vec-palm
                    "mediaType": "image",
                })
            except Exception as e:
                print(f"[Image ingest error] {p}: {e}")

    if animals.batch.failed_objects:
        print(f"Failed to import {len(animals.batch.failed_objects)} image objects")
        for failed in animals.batch.failed_objects[:5]:
            print(" -", failed.message)
    else:
        print("Image ingest: No errors")

# ---------------- INGEST VIDEOS (ONE-BY-ONE) ----------------
video_files = [p for p in VID_DIR.glob("*") if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}]
if not video_files:
    print(f"[Info] Put some videos into: {VID_DIR} (mp4/mov/webm)")
else:
    for p in video_files:
        print(f"Adding video: {p.name}")
        try:
            animals.data.insert({
                "name": p.name,
                "path": str(p),
                "video": file_to_base64(p),
                "mediaType": "video",
            })
        except Exception as e:
            print(f"[Video ingest error] {p}: {e}")

# ---------------- AGGREGATION CHECK ----------------
agg = animals.aggregate.over_all(group_by="mediaType")
for group in agg.groups:
    print("Group:", group.value, "-> count:", group.count)

# ---------------- QUERIES ----------------
print("\n--- near_text: dog playing with stick ---")
resp = animals.query.near_text(
    query="dog playing with stick",
    return_properties=["name", "path", "mediaType"],
    limit=3,
)
for obj in resp.objects:
    json_print(obj.properties)
    # open_with_os(Path(obj.properties["path"]))  # uncomment if you want to open the file

# Query by a local image (place a test image)
cat_img = TEST_DIR / "test-cat.jpg"
if cat_img.exists():
    print("\n--- near_image: test-cat.jpg ---")
    resp = animals.query.near_image(
        near_image=file_to_base64(cat_img),
        return_properties=["name", "path", "mediaType"],
        limit=3,
    )
    for obj in resp.objects:
        json_print(obj.properties)

# Query by a URL image
print("\n--- near_image: URL meerkat ---")
url = "https://raw.githubusercontent.com/weaviate-tutorials/multimodal-workshop/main/2-multimodal/test/test-meerkat.jpg"
try:
    resp = animals.query.near_image(
        near_image=url_to_base64(url),
        return_properties=["name", "path", "mediaType"],
        limit=3,
    )
    for obj in resp.objects:
        json_print(obj.properties)
except Exception as e:
    print(f"[near_image URL error] {e}")

# Query by a local video (optional)
meerkat_video = TEST_DIR / "test-meerkat.mp4"
if meerkat_video.exists():
    print("\n--- near_media: test-meerkat.mp4 ---")
    from weaviate.classes.query import NearMediaType
    try:
        resp = animals.query.near_media(
            media=file_to_base64(meerkat_video),
            media_type=NearMediaType.VIDEO,
            return_properties=["name", "path", "mediaType"],
            limit=3,
        )
        for obj in resp.objects:
            json_print(obj.properties)
    except Exception as e:
        print(f"[near_media VIDEO error] {e}")

client.close()
print("\nDone.")
