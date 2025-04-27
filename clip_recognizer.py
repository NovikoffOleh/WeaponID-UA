import os
import torch
import clip
from PIL import Image

# Підключення бази даних моделей зброї
from weapons_database import weapons_data  # <-- важливо щоб файл weapons_database.py існував

_model = None
_preprocess = None

def load_clip_model():
    """Ліниве завантаження CLIP-моделі"""
    global _model, _preprocess
    if _model is None or _preprocess is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model, _preprocess = clip.load("ViT-B/32", device=device)
    return _model, _preprocess

def recognize_weapon(image_path):
    """Функція розпізнавання зброї"""
    model, preprocess = load_clip_model()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Завантаження та обробка зображення
    image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)

    # Підготовка текстових підписів
    weapon_names = [weapon["name"] for weapon in weapons_data]
    text_inputs = clip.tokenize(weapon_names).to(device)

    # Отримання ембедінгів
    with torch.no_grad():
        image_features = model.encode_image(image)
        text_features = model.encode_text(text_inputs)

    # Нормалізація
    image_features /= image_features.norm(dim=-1, keepdim=True)
    text_features /= text_features.norm(dim=-1, keepdim=True)

    # Пошук найбільш схожої моделі
    similarities = (100.0 * image_features @ text_features.T).squeeze(0)
    best_idx = similarities.argmax().item()
    highest_similarity = similarities[best_idx].item() / 100.0  # Приводимо до 0-1

    best_match = weapon_names[best_idx]
    match_info = next((w for w in weapons_data if w["name"] == best_match), None)

    # 🔒 Перевірка на низьку впевненість
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
            output += "\n⚠️ Увага! Об'єкт може бути вибухонебезпечним. Не торкайтесь!"
    else:
        output = f"✅ Найбільш схожа модель: {best_match}\n📏 Схожість: {highest_similarity:.4f}"

    return output
