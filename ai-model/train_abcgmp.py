
import os
import json
import copy
import argparse
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "datasets" / "ABCGMP_training"

MODEL_PATH = BASE_DIR / "mobilenetv2_abcgmp.pth"
CLASSES_PATH = BASE_DIR / "abcgmp_classes.json"

BATCH_SIZE = 32
NUM_WORKERS = 0  # Safe for Windows


def get_data_loaders():

    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(
            brightness=0.15,
            contrast=0.15,
            saturation=0.10
        ),
        transforms.ToTensor(),
        transforms.Normalize(
            [0.485, 0.456, 0.406],
            [0.229, 0.224, 0.225]
        )
    ])

    val_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(
            [0.485, 0.456, 0.406],
            [0.229, 0.224, 0.225]
        )
    ])

    train_dataset = datasets.ImageFolder(
        DATA_DIR / "train",
        transform=train_transform
    )

    val_dataset = datasets.ImageFolder(
        DATA_DIR / "val",
        transform=val_transform
    )

    if train_dataset.classes != val_dataset.classes:
        raise ValueError("Training and validation classes do not match!")

    class_names = train_dataset.classes

    print("\nDetected classes:")
    for i, name in enumerate(class_names):
        print(i, name)

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
        pin_memory=torch.cuda.is_available()
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
        pin_memory=torch.cuda.is_available()
    )

    # Calculate weights to reduce class imbalance
    counts = torch.bincount(
        torch.tensor(train_dataset.targets),
        minlength=len(class_names)
    ).float()

    class_weights = counts.sum() / (
        len(class_names) * counts
    )

    return (
        train_loader,
        val_loader,
        class_names,
        class_weights
    )


def build_model(num_classes):

    weights = models.MobileNet_V2_Weights.DEFAULT
    model = models.mobilenet_v2(weights=weights)

    # Freeze all feature extraction layers initially
    for param in model.features.parameters():
        param.requires_grad = False

    # Replace classifier with the SAME architecture
    # expected by Thalir's existing inference.py
    in_features = model.classifier[1].in_features

    model.classifier[1] = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(in_features, num_classes)
    )

    return model


def run_epoch(model, loader, criterion, optimizer, device, training):

    model.train(training)

    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:

        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        if training:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(training):

            outputs = model(images)
            loss = criterion(outputs, labels)

            if training:
                loss.backward()
                optimizer.step()

        predictions = outputs.argmax(dim=1)

        running_loss += loss.item() * images.size(0)
        correct += (predictions == labels).sum().item()
        total += labels.size(0)

    return running_loss / total, correct / total


def train(epochs):

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("\nTraining device:", device)

    if device.type == "cuda":
        print("GPU:", torch.cuda.get_device_name(0))

    (
        train_loader,
        val_loader,
        class_names,
        class_weights
    ) = get_data_loaders()

    with open(CLASSES_PATH, "w", encoding="utf-8") as f:
        json.dump(class_names, f, indent=4)

    model = build_model(len(class_names)).to(device)

    criterion = nn.CrossEntropyLoss(
        weight=class_weights.to(device)
    )

    # First phase: train classification head
    optimizer = optim.AdamW(
        model.classifier.parameters(),
        lr=0.001,
        weight_decay=0.0001
    )

    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=0.5,
        patience=2
    )

    best_accuracy = 0.0
    best_state = None

    for epoch in range(epochs):

        # Fine-tune the final feature layers after phase one
        if epoch == 4:
            print("\nUnfreezing final MobileNetV2 feature layers...")

            for param in model.features[-3:].parameters():
                param.requires_grad = True

            optimizer = optim.AdamW([
                {
                    "params": model.features[-3:].parameters(),
                    "lr": 0.00005
                },
                {
                    "params": model.classifier.parameters(),
                    "lr": 0.0003
                }
            ], weight_decay=0.0001)

            scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                optimizer,
                mode="max",
                factor=0.5,
                patience=2
            )

        train_loss, train_acc = run_epoch(
            model, train_loader, criterion,
            optimizer, device, True
        )

        val_loss, val_acc = run_epoch(
            model, val_loader, criterion,
            optimizer, device, False
        )

        scheduler.step(val_acc)

        print(f"\nEpoch {epoch + 1}/{epochs}")
        print(f"Train Loss: {train_loss:.4f}")
        print(f"Train Accuracy: {train_acc * 100:.2f}%")
        print(f"Val Loss: {val_loss:.4f}")
        print(f"Val Accuracy: {val_acc * 100:.2f}%")

        if val_acc > best_accuracy:

            best_accuracy = val_acc
            best_state = copy.deepcopy(model.state_dict())

            torch.save(best_state, MODEL_PATH)

            print("Best model saved:", MODEL_PATH)

    print("\nTraining completed!")
    print(f"Best validation accuracy: {best_accuracy * 100:.2f}%")
    print("Model:", MODEL_PATH)
    print("Classes:", CLASSES_PATH)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--epochs",
        type=int,
        default=15
    )

    args = parser.parse_args()

    if not (DATA_DIR / "train").exists():
        raise FileNotFoundError(f"Dataset missing: {DATA_DIR}")

    train(args.epochs)
