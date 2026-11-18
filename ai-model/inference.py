"""
Thalir AI Disease Detection Engine — MobileNetV2 Deep Learning Pipeline
Performs leaf image preprocessing, PyTorch MobileNetV2 neural network inference,
and returns structured diagnostic reports with actionable remedies.
"""

import io
import os
import json
import numpy as np
from PIL import Image

try:
    import torch
    import torch.nn as nn
    from torchvision import models, transforms
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False

from disease_db import get_disease_info, DISEASE_KNOWLEDGE_BASE

# ABCGMP 12-Class Fruit Leaf Model (Apple, Banana, Citrus, Guava, Mango, Papaya)
ABCGMP_CLASSES_PATH = os.path.join(os.path.dirname(__file__), "abcgmp_classes.json")
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "mobilenetv2_abcgmp.pth")

DEFAULT_ABCGMP_CLASSES = [
    "Apple___Black_rot",
    "Apple___healthy",
    "Banana___Cordana",
    "Banana___healthy",
    "Citrus___Canker",
    "Citrus___healthy",
    "Guava___Red_Rust",
    "Guava___healthy",
    "Mango___Bacterial_Canker",
    "Mango___healthy",
    "Papaya___Ring_Spot",
    "Papaya___healthy"
]


def _load_class_names():
    """Load class names from abcgmp_classes.json, falling back to default list."""
    if os.path.exists(ABCGMP_CLASSES_PATH):
        with open(ABCGMP_CLASSES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_ABCGMP_CLASSES


class MobileNetV2LeafClassifier:
    def __init__(self):
        self.class_names = _load_class_names()
        self.device = torch.device("cpu") if PYTORCH_AVAILABLE else None
        self.model = None

        if PYTORCH_AVAILABLE:
            # Matches train_abcgmp.py validation preprocessing
            self.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            self._load_model()
        else:
            print("[!] Warning: PyTorch is not available. Deep learning inference will be disabled.")

    def _load_model(self):
        """Build MobileNetV2 architecture and load ABCGMP trained weights."""
        try:
            print(f"[*] Initializing MobileNetV2 architecture ({len(self.class_names)} classes)...")
            model = models.mobilenet_v2(weights=None)
            in_features = model.classifier[1].in_features
            model.classifier[1] = nn.Sequential(
                nn.Dropout(0.2),
                nn.Linear(in_features, len(self.class_names))
            )

            if os.path.exists(WEIGHTS_PATH):
                state_dict = torch.load(WEIGHTS_PATH, map_location=self.device)
                model.load_state_dict(state_dict)
                print(f"[+] Loaded ABCGMP MobileNetV2 weights from {WEIGHTS_PATH}")
            else:
                print(f"[!] Model weights file '{WEIGHTS_PATH}' not found.")
                self.model = None
                return

            model.eval()
            self.model = model
        except Exception as e:
            print(f"[!] Error loading MobileNetV2 model: {e}")
            self.model = None

    def predict(self, image_bytes: bytes, target_crop: str = None) -> dict:
        """Run deep neural network inference on leaf image."""
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid image file: {e}",
                "status": "Unknown",
                "disease": "Unknown",
                "confidence": 0.0,
                "recommendation": "Please upload a valid JPEG or PNG image."
            }

        # 1. Primary path: Deep Neural Network (MobileNetV2)
        if self.model is not None and PYTORCH_AVAILABLE:
            try:
                input_tensor = self.transform(img).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    logits = self.model(input_tensor)
                    probabilities = torch.softmax(logits, dim=1)[0].cpu().numpy()

                # Filter by target_crop if provided by user
                crop_indices = list(range(len(self.class_names)))
                if target_crop:
                    filtered = [
                        i for i, name in enumerate(self.class_names)
                        if target_crop.lower() in name.split("___")[0].lower()
                    ]
                    if filtered:
                        crop_indices = filtered

                # Get top prediction within target crop
                best_idx = crop_indices[np.argmax([probabilities[i] for i in crop_indices])]
                selected_key = self.class_names[best_idx]
                confidence = round(float(probabilities[best_idx] * 100.0), 2)

                # Top 3 predictions breakdown with authentic softmax probabilities
                sorted_indices = sorted(crop_indices, key=lambda i: probabilities[i], reverse=True)[:3]
                top_classes = []
                for idx in sorted_indices:
                    info = get_disease_info(self.class_names[idx])
                    top_classes.append({
                        "class_key": self.class_names[idx],
                        "label": f"{info['crop']} - {info['disease_name']}",
                        "confidence": round(float(probabilities[idx] * 100.0), 2)
                    })

                disease_info = get_disease_info(selected_key)

                return {
                    "success": True,
                    "model": "MobileNetV2 (ABCGMP)",
                    "class_key": selected_key,
                    "crop": disease_info["crop"],
                    "disease": disease_info["disease_name"],
                    "scientific_name": disease_info.get("scientific_name", "Pathogen"),
                    "status": disease_info["status"],
                    "severity": disease_info.get("severity", "None"),
                    "confidence": confidence,
                    "symptoms": disease_info.get("symptoms", []),
                    "causes": disease_info.get("causes", "Pathological condition"),
                    "organic_remedies": disease_info.get("organic_remedies", ["Apply organic treatment"]),
                    "chemical_remedies": disease_info.get("chemical_remedies", ["Consult agronomist"]),
                    "preventive_measures": disease_info.get("preventive_measures", ["Maintain proper airflow"]),
                    "recommendation": f"[{disease_info['status']}] {disease_info.get('organic_remedies', ['No action'])[0]}",
                    "top_predictions": top_classes
                }

            except Exception as e:
                print(f"[!] Neural network inference error: {e}")
                return {
                    "success": False,
                    "error": f"Inference execution failed: {str(e)}",
                    "status": "Error",
                    "disease": "Inference Error",
                    "confidence": 0.0,
                    "recommendation": "Neural network inference failed. Please check the model checkpoint and input image."
                }

        return {
            "success": False,
            "error": "MobileNetV2 (ABCGMP) model is not loaded or PyTorch is unavailable.",
            "status": "Error",
            "disease": "Model Unavailable",
            "confidence": 0.0,
            "recommendation": "MobileNetV2 ABCGMP weights are unavailable or failed to initialize."
        }


# Singleton model instance
classifier = MobileNetV2LeafClassifier()


def predict_leaf_disease(image_bytes: bytes, target_crop: str = None) -> dict:
    """Public helper function for prediction endpoint."""
    return classifier.predict(image_bytes, target_crop=target_crop)
