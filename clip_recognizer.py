import os
import json
from pathlib import Path
from PIL import Image
import torch
import torchvision.transforms as transforms
from torchvision import models

device = "cuda" if torch.cuda.is_available() else "cpu"

# Завантаження легкої моделі MobileNetV2
model = models.mobilenet_v2(pretrained=True)
model.classifier = torch.nn.Identity()  # Прибираємо останній класифікатор
model = model.to(device).eval()

# Трансформації для зображення
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

def load_image(path):
    image = Image.open(path).convert('RGB')
    return transform(image).unsqueeze(0).to(device)

def load_weapons_db(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def collect_image_folders(root_path):
    folders = []
    for path in Path(root_path).rglob('*'):
        if path.is_dir():
            images = list(path.glob('*.jpg')) + list(path.glob('*.jpeg')) + list(path.glob('*.png'))
            if images:
                folders.append(path)
    return folders

def recognize_weapon(test_image_path, reference_folder, db_path):
    weapons_db = load_weapons_db(db_path)

    # Витягуємо ознаки тестового зображення
    test_image = load_image(test_image_path)
    with torch.no_grad():
        test_features = model(test_image)

    best_match = None
    best_similarity = -1
    match_info = None

    for model_path in collect_image_folders(reference_folder):
        model_name = model_path.name
        similarities = []

        for image_path in model_path.glob("*"):
            if image_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                continue

            try:
                ref_image = load_image(str(image_path))
                with torch.no_grad():
                    ref_features = model(ref_image)
                similarity = torch.nn.functional.cosine_similarity(test_features, ref_features).item()
                similarities.append(similarity)
            except Exception as e:
                print(f"⚠️ Помилка обробки {image_path}: {e}")

        if similarities:
            avg_similarity = sum(similarities) / len(similarities)
            if avg_similarity > best_similarity:
                best_similarity = avg_similarity
                best_match = model_name
                match_info = next((item for item in weapons_db if item["label"] == model_name), None)

    if best_similarity < 0.7:
        return (
            f"⚠️ Ймовірність розпізнавання низька (схожість: {best_similarity:.2f}).\n"
            f"Об’єкт не схожий на відомі зразки зброї або боєприпасів.\n"
            f"Будьте обережні!"
        )

    output = ""

    if match_info:
        output += f"✅ Модель: {match_info['name_ua']}\n"
        output += f"📌 Тип: {match_info['type']} ({match_info['category']})\n"
        output += f"🏳️ Країна: {match_info['country']}\n"
        output += f"🔫 Калібр: {match_info['caliber']}\n"
        output += f"📏 Схожість: {best_similarity:.4f}\n"

        if match_info["category"] in ["гранати", "міни"] and best_similarity > 0.8:
            output += "⚠️ Увага! Може бути вибухонебезпечним об’єктом."
    elif best_match:
        output += f"✅ Найбільш схожа модель: {best_match}\n📏 Схожість: {best_similarity:.4f}"
    else:
        output = "❌ Жодного збігу не знайдено."

    return output
