import json
import os

# Знаходимо абсолютний шлях до файлу JSON
base_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(base_dir, "weapons_db.json")

# Відкриваємо файл та читаємо дані
with open(json_path, "r", encoding="utf-8") as f:
    weapons_data = json.load(f)
