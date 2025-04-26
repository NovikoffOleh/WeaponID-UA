import json

with open('weapons_db.json', 'r', encoding='utf-8') as file:
    weapons = json.load(file)

for weapon in weapons:
    print(f"Model: {weapon['name']}")
    print(f"Country: {weapon['country']}")
    print(f"Years of production: {weapon['years']}")
    print(f"Caliber: {weapon['caliber']}")
    print(f"Type: {weapon['type']}")
    print("-" * 30)

