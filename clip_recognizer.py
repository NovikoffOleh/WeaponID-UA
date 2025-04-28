from pathlib import Path
import clip
import torch
from PIL import Image
import json

device = "cuda" if torch.cuda.is_available() else "cpu"


# Завантаження моделі — буде виконано лише один раз
_model = None
_preprocess = None

def load_clip_model():
    global _model, _preprocess
    if _model is None or _preprocess is None:
        _model, _preprocess = clip.load("ViT-B/32", device=device)

def load_local_image(path):
    return Image.open(path).convert("RGB")

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
    load_clip_model()

    weapons_db = load_weapons_db(db_path)
    test_image = _preprocess(load_local_image(test_image_path)).unsqueeze(0).to(device)

    best_match = None
    highest_similarity = -1
    match_info = None

    for model_path in collect_image_folders(reference_folder):
        model_name = model_path.name
        similarities = []

        for image_path in model_path.glob("*"):
            if not image_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                continue
            try:
                ref_image = _preprocess(load_local_image(str(image_path))).unsqueeze(0).to(device)
                with torch.no_grad():
                    test_features = _model.encode_image(test_image)
                    ref_features = _model.encode_image(ref_image)
                similarity = torch.nn.functional.cosine_similarity(test_features, ref_features).item()
                similarities.append(similarity)
            except Exception as e:
                print(f"⚠️ Помилка з файлом {image_path}: {e}")

        if similarities:
            avg_similarity = sum(similarities) / len(similarities)
            if avg_similarity > highest_similarity:
                highest_similarity = avg_similarity
                best_match = model_name
                match_info = next((item for item in weapons_db if item["label"] == model_name), None)

    if highest_similarity < 0.7:
        return (
            f"⚠️ Ймовірність розпізнавання надто низька (схожість: {highest_similarity:.2f}).\n"
            f"Об’єкт не схожий на відомі зразки зброї або боєприпасів.\n"
            f"Якщо маєте сумніви — не наближайтесь і зверніться до ДСНС або поліції."
        )

    output = ""

    if match_info:
        output += f"✅ Модель: {match_info['name_ua']}\n"
        output += f"📌 Тип: {match_info['type']} ({match_info['category']})\n"
        output += f"🏳️ Країна: {match_info['country']}\n"
        output += f"🔫 Калібр: {match_info['caliber']}\n"
        output += f"📏 Схожість: {highest_similarity:.4f}\n"

        if match_info["category"] in ["гранати", "міни"] and highest_similarity > 0.8:
            output += "⚠️ Увага! Об'єкт може бути вибухонебезпечним. Не торкайтесь!"
    elif best_match:
        output += f"✅ Найбільш схожа модель: {best_match}\n📏 Схожість: {highest_similarity:.4f}"
    else:
        output = "❌ Жодного збігу не знайдено."

    return output
