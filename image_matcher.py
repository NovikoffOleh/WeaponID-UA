from PIL import Image
import imagehash
import os

WEAPONS_FOLDER = "weapon_images"
INPUT_IMAGE_PATH = "input_photos/test.jpg"

def get_image_hash(path):
    with Image.open(path) as img:
        return imagehash.average_hash(img)

def find_closest_match(input_img_path):
    input_hash = get_image_hash(input_img_path)
    closest_match = None
    min_diff = float('inf')

    for filename in os.listdir(WEAPONS_FOLDER):
        weapon_path = os.path.join(WEAPONS_FOLDER, filename)
        weapon_hash = get_image_hash(weapon_path)
        diff = input_hash - weapon_hash

        if diff < min_diff:
            min_diff = diff
            closest_match = filename

    return closest_match, min_diff

if __name__ == "__main__":
    match, difference = find_closest_match(INPUT_IMAGE_PATH)
    if match:
        print(f"✅ Найбільш схоже зображення: {match}")
        print(f"📏 Різниця хешів: {difference}")
    else:
        print("❌ Не вдалося знайти збіг.")

