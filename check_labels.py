
import requests
import time
from collections import Counter

URL = "https://datasets-server.huggingface.co/rows"

BASE_PARAMS = {
    "dataset": "Project-AgML/DIMPSAR_medicinal_leaf_classification",
    "config": "default",
    "split": "train"
}

session = requests.Session()

def fetch_rows(offset, length):
    """Retry requests and split failed batches into smaller ones."""

    params = {
        **BASE_PARAMS,
        "offset": offset,
        "length": length
    }

    for attempt in range(3):
        try:
            response = session.get(
                URL,
                params=params,
                timeout=60
            )
            response.raise_for_status()
            return response.json()["rows"]

        except requests.RequestException as error:
            print(
                f"Retry {attempt + 1}/3: "
                f"offset={offset}, length={length}"
            )
            time.sleep(2 * (attempt + 1))

    if length == 1:
        print(f"Skipping unavailable row: {offset}")
        return []

    # Split the failed request into two smaller requests.
    first_length = length // 2
    second_length = length - first_length

    print(f"Splitting failed batch at offset {offset}")

    return (
        fetch_rows(offset, first_length)
        + fetch_rows(offset + first_length, second_length)
    )


# Get label mapping
first_rows = fetch_rows(0, 1)

if not first_rows:
    raise RuntimeError("Unable to retrieve the first dataset row.")

# Get class names from the dataset features
response = session.get(
    URL,
    params={**BASE_PARAMS, "offset": 0, "length": 1},
    timeout=60
)
response.raise_for_status()

features = response.json()["features"]

label_names = next(
    f["type"]["names"]
    for f in features
    if f["name"] == "label"
)

counts = Counter()
skipped = 0

print("\nChecking all 6900 dataset rows...\n")

for offset in range(0, 6900, 20):

    rows = fetch_rows(
        offset,
        min(20, 6900 - offset)
    )

    if not rows:
        skipped += 20
        continue

    for item in rows:
        label = item["row"]["label"]
        counts[label_names[label]] += 1

    print(
        f"Checked up to {min(offset + 20, 6900)}/6900"
    )

print("\n========== PLANT DISTRIBUTION ==========")

for plant, count in sorted(counts.items()):
    print(f"{plant}: {count}")

print("\nTotal rows retrieved:", sum(counts.values()))
print("Unavailable rows/batches:", skipped)
