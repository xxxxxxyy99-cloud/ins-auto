import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

IMAGE_DIR = BASE_DIR / "generated_images"
IMAGE_DIR.mkdir(exist_ok=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "your-openrouter-api-key-here")
IG_USERNAME = os.getenv("IG_USERNAME", "your-instagram-username")
IG_PASSWORD = os.getenv("IG_PASSWORD", "your-instagram-password")

IMAGE_MODEL = "google/gemini-2.5-flash-image"
CAPTION_MODEL = "openai/gpt-4o-mini"

POST_INTERVAL_DAYS = 2
POST_WINDOW_START = 16
POST_WINDOW_END = 23
HASHTAGS = [
    "#kitchenware", "#cooking", "#homecooking", "#kitchentools",
    "#cookware", "#foodprep", "#kitchengadgets", "#homechef",
    "#kitchenlove", "#cookingathome", "#kitchenlife", "#厨具"
]
