
import requests
import json

url = "https://datasets-server.huggingface.co/rows"

params = {
    "dataset": "Project-AgML/DIMPSAR_medicinal_leaf_classification",
    "config": "default",
    "split": "train",
    "offset": 0,
    "length": 2
}

response = requests.get(url, params=params, timeout=60)

print("HTTP Status:", response.status_code)
response.raise_for_status()

data = response.json()

print("\nTOTAL ROWS:", data.get("num_rows_total"))

print("\nFEATURE INFORMATION:")
for feature in data.get("features", []):
    print(json.dumps(feature, indent=2))

print("\nFIRST TWO ROWS:")

for item in data.get("rows", []):
    row = item["row"]

    print("\nROW KEYS:", list(row.keys()))

    print("\nLABEL VALUE:")
    print(repr(row.get("label")))

    print("\nIMAGE VALUE:")
    image = row.get("image")
    print(repr(image)[:1500])
