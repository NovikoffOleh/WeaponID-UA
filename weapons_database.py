# weapons_database.py
import json

with open('weapons_db.json', 'r', encoding='utf-8') as f:
    weapons_data = json.load(f)
