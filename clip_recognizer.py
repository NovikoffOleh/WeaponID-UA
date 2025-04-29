import os
import json
import torch
from torchvision import models, transforms
from PIL import Image
from pathlib import Path

device = "cuda" if torch.cuda.is_available() else "cpu"
model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1).features.to(device)
model.eval()

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

cache_file = "features_cache.pt"
features_cache = {}

def load_local_image(path):
    image = Image.open(path).convert("RGB")
    return transform(image).unsqueeze(0).to(device)

def extract_features(image_tensor):
    with torch.no_grad():
        features = model(image_tensor)
    return features.mean([2, 3])  # Pool spatial dimensions

def build_features_cache(reference_folder):
    features = {}
    for folder in Path(reference_folder).iterdir():
        if folder.is_dir():
            for img_path in folder.glob("*.*"):
                if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
                    continue
                try:
                    img_tensor = load_local_image(str(img_path))
                    features[str(img_path)] = extract_features(img_tensor).cpu()
                except Exception as e:
                    print(f"⚠️ Помилка з {img_path}: {e}")
    torch.save(features, cache_file)
    return features

def load_or_build_cache(reference_folder):
    if os.path.exists(cache_file):
        return torch.load(cache_file)
    else:
        return build_features_cache(reference_folder)

# Завантажуємо або створюємо кеш одразу
features_cache = load_or_build_cache("weapon_images")

def load_weapons_db(db_path):
    with open(db_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def recognize_weapon(test_image_path, reference_folder, db_path):
    weapons_db = load_weapons_db(db_path)
    test_image = load_local_image(test_image_path)
    test_features = extract_features(test_image)

    best_similarity = -1
    best_match = None

    for ref_path, ref_features in features_cache.items():
        similarity = torch.nn.functional.cosine_similarity(test_features, ref_features.unsqueeze(0)).item()
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = ref_path

    if best_similarity < 0.7:
        return (
            f"⚠️ Ймовірність розпізнавання надто низька (схожість: {best_similarity:.2f}).\n"
            f"Об’єкт не схожий на відомі зразки зброї або боєприпасів.\n"
            f"Якщо маєте сумніви — не наближайтесь і зверніться до ДСНС або поліції."
        )

    model_name = Path(best_match).parent.name
    match_info = next((item for item in weapons_db if item["label"] == model_name), None)

    output = ""

    if match_info:
        output += f"✅ Модель: {match_info['name_ua']}\n"
        output += f"📌 Тип: {match_info['type']} ({match_info['category']})\n"
        output += f"🏳️ Країна: {match_info['country']}\n"
        output += f"🔫 Калібр: {match_info['caliber']}\n"
        output += f"📏 Схожість: {best_similarity:.4f}\n"

        if match_info["category"] in ["гранати", "міни"] and best_similarity > 0.8:
            output += "⚠️ Увага! Об'єкт може бути вибухонебезпечним. Не торкайтесь!"
    else:
        output += f"✅ Найбільш схожа модель: {model_name}\n"
        output += f"📏 Схожість: {best_similarity:.4f}"

    return output
