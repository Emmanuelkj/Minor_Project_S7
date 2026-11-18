
import requests
import time
import re
import json
import random
import shutil

from pathlib import Path
from collections import Counter
from io import BytesIO
from PIL import Image, ImageOps


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DATASET_ID = "Project-AgML/DIMPSAR_medicinal_leaf_classification"

API = "https://datasets-server.huggingface.co"

MAX_IMAGES_PER_CLASS = 150
IMAGE_SIZE = (224, 224)
BATCH_SIZE = 100
RANDOM_SEED = 42

OUTPUT_DIR = Path("ai-model/datasets/DIMPSAR_18_224")
STAGING_DIR = Path("ai-model/datasets/.dimpsar_staging")

# Original class names and possible spelling variations.
# The output folders use clean, consistent names.

TARGETS = {
    "Papaya": ["papaya"],
    "Neem": ["neem"],
    "Curry": ["curry"],
    "Tulsi": ["tulsi"],
    "Mango": ["mango"],
    "Guava": ["guava"],
    "Jackfruit": ["jackfruit"],
    "Drumstick": ["drumstick"],
    "Hibiscus": ["hibiscus"],
    "Aloe_Vera": ["aloevera", "aloe vera"],
    "Amla": ["amla"],
    "Turmeric": ["turmeric"],
    "Ginger": ["ginger"],
    "Mint": ["mint"],
    "Lemon": ["lemon"],
    "Tamarind": ["tamarind"],
    "Rose": ["rose"],
    "Pomegranate": ["pomoegranate", "pomegranate"]
}


def normalize(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


LABEL_LOOKUP = {}

for output_name, aliases in TARGETS.items():
    for alias in aliases:
        LABEL_LOOKUP[normalize(alias)] = output_name


# --------------------------------------------------
# SESSION
# --------------------------------------------------

session = requests.Session()
session.headers.update({
    "User-Agent": "Thalir-DIMPSAR-Downloader/1.0"
})


def get_json(url, params=None):
    for attempt in range(4):
        try:
            response = session.get(
                url,
                params=params,
                timeout=60
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            print(f"Request failed: {error}")
            time.sleep(3 * (attempt + 1))

    raise RuntimeError("Unable to contact Hugging Face API")


# --------------------------------------------------
# DISCOVER DATASET SPLIT
# --------------------------------------------------

print("\nChecking DIMPSAR dataset...")

split_data = get_json(
    f"{API}/splits",
    {"dataset": DATASET_ID}
)

available_splits = split_data.get("splits", [])

if not available_splits:
    raise RuntimeError(
        "No dataset splits returned by Hugging Face."
    )

selected_split = next(
    (s for s in available_splits if s["split"] == "train"),
    available_splits[0]
)

CONFIG = selected_split["config"]
SPLIT = selected_split["split"]

print("Config:", CONFIG)
print("Split:", SPLIT)


# --------------------------------------------------
# DOWNLOAD IMAGE AND RESIZE
# --------------------------------------------------

def save_image(image_url, destination):

    for attempt in range(3):

        try:
            response = session.get(
                image_url,
                timeout=60
            )
            response.raise_for_status()

            with Image.open(BytesIO(response.content)) as original:

                original = ImageOps.exif_transpose(original)

                # Preserve transparency against a white background.
                if original.mode in ("RGBA", "LA"):
                    rgba = original.convert("RGBA")
                    background = Image.new(
                        "RGBA",
                        rgba.size,
                        (255, 255, 255, 255)
                    )
                    background.alpha_composite(rgba)
                    original = background.convert("RGB")
                else:
                    original = original.convert("RGB")

                # Preserve the whole leaf without cropping.
                resized = ImageOps.pad(
                    original,
                    IMAGE_SIZE,
                    method=Image.Resampling.LANCZOS,
                    color=(255, 255, 255)
                )

                resized.save(
                    destination,
                    format="JPEG",
                    quality=90,
                    optimize=True
                )

            return True

        except Exception as error:
            print(f"Image error: {error}")
            time.sleep(2)

    return False


# --------------------------------------------------
# PREPARE DIRECTORIES
# --------------------------------------------------

if OUTPUT_DIR.exists():
    raise RuntimeError(
        f"{OUTPUT_DIR} already exists. "
        "Rename or remove it before running again."
    )

if STAGING_DIR.exists():
    raise RuntimeError(
        f"{STAGING_DIR} already exists. "
        "Inspect it before removing it and restarting."
    )

STAGING_DIR.mkdir(parents=True, exist_ok=True)

for class_name in TARGETS:
    (STAGING_DIR / class_name).mkdir(
        parents=True,
        exist_ok=True
    )


# --------------------------------------------------
# GET FIRST PAGE AND DETECT LABELS
# --------------------------------------------------

first_page = get_json(
    f"{API}/rows",
    {
        "dataset": DATASET_ID,
        "config": CONFIG,
        "split": SPLIT,
        "offset": 0,
        "length": BATCH_SIZE
    }
)

if first_page.get("partial"):
    raise RuntimeError(
        "Hugging Face returned a partial dataset view."
    )

features = first_page["features"]

label_feature = next(
    f for f in features if f["name"] == "label"
)

image_feature = next(
    f for f in features
    if f["type"].get("_type") == "Image"
)

LABEL_COLUMN = label_feature["name"]
IMAGE_COLUMN = image_feature["name"]

label_type = label_feature["type"]
label_names = label_type.get("names", [])

if not label_names:
    raise RuntimeError(
        "Could not discover ClassLabel names. "
        "Inspect the dataset label feature before continuing."
    )

available_labels = {}

for original_name in label_names:
    normalized = normalize(original_name)

    if normalized in LABEL_LOOKUP:
        available_labels[original_name] = LABEL_LOOKUP[normalized]

found_classes = set(available_labels.values())
missing_classes = set(TARGETS) - found_classes

print("\nAvailable selected classes:")
for name in sorted(found_classes):
    print(" -", name)

if missing_classes:
    raise RuntimeError(
        "Some selected species are missing from the actual "
        "Hugging Face label mapping:\n"
        + "\n".join(sorted(missing_classes))
        + "\nDo not silently train with an incomplete class list."
    )


# --------------------------------------------------
# PROCESS DATASET ROWS
# --------------------------------------------------

counts = Counter()
failed_images = 0

total_rows = first_page["num_rows_total"]

print("\nTotal dataset rows:", total_rows)
print("Starting selective download...\n")


def process_page(page):

    global failed_images

    for item in page["rows"]:

        row = item["row"]

        label_value = row[LABEL_COLUMN]

        if isinstance(label_value, int):
            if not (0 <= label_value < len(label_names)):
                continue

            original_label = label_names[label_value]
        else:
            original_label = str(label_value)

        if original_label not in available_labels:
            continue

        class_name = available_labels[original_label]

        if counts[class_name] >= MAX_IMAGES_PER_CLASS:
            continue

        image_info = row.get(IMAGE_COLUMN)

        if not isinstance(image_info, dict):
            failed_images += 1
            continue

        image_url = image_info.get("src")

        if not image_url:
            failed_images += 1
            continue

        image_number = counts[class_name]

        destination = (
            STAGING_DIR /
            class_name /
            f"{image_number:05d}.jpg"
        )

        if save_image(image_url, destination):
            counts[class_name] += 1
        else:
            failed_images += 1


for offset in range(0, total_rows, BATCH_SIZE):

    if offset == 0:
        page = first_page
    else:
        page = get_json(
            f"{API}/rows",
            {
                "dataset": DATASET_ID,
                "config": CONFIG,
                "split": SPLIT,
                "offset": offset,
                "length": BATCH_SIZE
            }
        )

    if page.get("partial"):
        raise RuntimeError(
            f"Partial dataset response at offset {offset}"
        )

    process_page(page)

    downloaded = sum(counts.values())

    print(
        f"Scanned {min(offset + BATCH_SIZE, total_rows)}"
        f"/{total_rows} rows | "
        f"Downloaded: {downloaded}"
    )


# --------------------------------------------------
# VERIFY DOWNLOAD
# --------------------------------------------------

print("\nDOWNLOAD SUMMARY")

for name in TARGETS:

    print(
        f"{name}: {counts[name]} images"
    )

total_images = sum(counts.values())

if total_images == 0:
    raise RuntimeError("No images were downloaded.")

if any(counts[name] == 0 for name in TARGETS):
    raise RuntimeError(
        "At least one selected class has no downloaded images."
    )

print("\nTotal images:", total_images)
print("Failed images:", failed_images)


# --------------------------------------------------
# CREATE TRAIN / VALIDATION SPLITS
# --------------------------------------------------

random.seed(RANDOM_SEED)

for class_name in sorted(TARGETS):

    files = sorted(
        (STAGING_DIR / class_name).glob("*.jpg")
    )

    random.shuffle(files)

    val_count = max(1, round(len(files) * 0.20))

    val_files = files[:val_count]
    train_files = files[val_count:]

    train_dir = OUTPUT_DIR / "train" / class_name
    val_dir = OUTPUT_DIR / "val" / class_name

    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)

    for file in train_files:
        shutil.move(
            str(file),
            str(train_dir / file.name)
        )

    for file in val_files:
        shutil.move(
            str(file),
            str(val_dir / file.name)
        )


# --------------------------------------------------
# SAVE CLASS MAPPING
# --------------------------------------------------

class_names = sorted(TARGETS.keys())

class_to_idx = {
    name: index
    for index, name in enumerate(class_names)
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with open(
    OUTPUT_DIR / "class_to_idx.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        class_to_idx,
        file,
        indent=4
    )


# --------------------------------------------------
# CLEAN TEMPORARY FILES
# --------------------------------------------------

shutil.rmtree(STAGING_DIR)

print("\n================================")
print("DIMPSAR PREPROCESSING COMPLETE")
print("================================")

print("Output:", OUTPUT_DIR)
print("Classes:", len(class_names))
print("Images:", total_images)
print("Resolution:", IMAGE_SIZE)

print("\nTraining images:",
      sum(1 for _ in (OUTPUT_DIR / "train").rglob("*.jpg")))

print("Validation images:",
      sum(1 for _ in (OUTPUT_DIR / "val").rglob("*.jpg")))

print("\nClass mapping saved successfully.")
