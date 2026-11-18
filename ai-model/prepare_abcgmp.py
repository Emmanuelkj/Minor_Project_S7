
import random
import shutil
from pathlib import Path

# Original extracted dataset
SOURCE = Path(
    r"D:\ABCGMP Fruit and Leaf Disease Six Crop Dataset"
) / "6  indian Fruit crops Fruit and Leaf Disease Dataset"

# Destination inside Thalir
DESTINATION = Path(__file__).parent / "datasets" / "ABCGMP_training"

# Original folder name : New training class name
CLASS_MAPPING = {
    "Apple___Black_rot": "Apple___Black_rot",
    "Apple___healthy": "Apple___healthy",
    "Healthy Banana Leaf": "Banana___healthy",
    "Banana cordana": "Banana___Cordana",
    "Citrus Healthy Leaf": "Citrus___healthy",
    "Citrus Cancker Leaf": "Citrus___Canker",
    "Guava Healthly Leaf": "Guava___healthy",
    "Guava Red Rust": "Guava___Red_Rust",
    "Mang Healthy Leaf": "Mango___healthy",
    "Mango Bacterial Canker": "Mango___Bacterial_Canker",
    "Papaya Healthy leaf": "Papaya___healthy",
    "Papaya RingSpot": "Papaya___Ring_Spot",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

random.seed(42)


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Dataset not found: {SOURCE}")

    if DESTINATION.exists():
        raise FileExistsError(
            f"{DESTINATION} already exists. "
            "Rename or remove this generated folder before running again."
        )

    total_images = 0

    for original_name, class_name in CLASS_MAPPING.items():

        source_folder = SOURCE / original_name

        if not source_folder.is_dir():
            raise FileNotFoundError(
                f"Missing class folder: {source_folder}"
            )

        images = [
            p for p in source_folder.rglob("*")
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        ]

        if len(images) < 2:
            raise ValueError(
                f"Not enough images in {original_name}: {len(images)}"
            )

        random.shuffle(images)

        split_index = int(len(images) * 0.8)
        train_images = images[:split_index]
        val_images = images[split_index:]

        for split_name, split_images in [
            ("train", train_images),
            ("val", val_images)
        ]:
            for image_path in split_images:
                relative_path = image_path.relative_to(source_folder)

                destination = (
                    DESTINATION / split_name /
                    class_name / relative_path
                )

                destination.parent.mkdir(
                    parents=True, exist_ok=True
                )

                shutil.copy2(image_path, destination)

        total_images += len(images)

        print(
            f"{class_name}: "
            f"Train={len(train_images)}, "
            f"Validation={len(val_images)}, "
            f"Total={len(images)}"
        )

    print("\nDataset preparation completed!")
    print(f"Total images: {total_images}")
    print(f"Dataset location: {DESTINATION}")


if __name__ == "__main__":
    main()
