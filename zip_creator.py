"""
zip_creator.py

Ushbu skript butun bot loyihasini bitta "media_bot.zip" fayliga arxivlaydi.
Foydalanish:
    python zip_creator.py

Skript quyidagilarni arxivga QO'SHMAYDI (kerak emas yoki maxfiy bo'lgani uchun):
    - .env (maxfiy tokenlar bo'lgani uchun)
    - venv/, __pycache__/, .git/ kabi vaqtinchalik papkalar
    - downloads/ ichidagi vaqtinchalik media fayllar
    - bot.log va bot_database.db kabi runtime fayllar

Skriptni loyiha papkasi ichida (main.py bilan bir joyda) ishga tushiring.
"""

import os
import zipfile

# Arxivga qo'shilmaydigan papka nomlari
EXCLUDED_DIRS = {"__pycache__", ".git", "venv", ".venv", "downloads", "node_modules"}

# Arxivga qo'shilmaydigan fayl nomlari
EXCLUDED_FILES = {".env", "bot.log", "bot_database.db"}

# Arxivga qo'shilmaydigan fayl kengaytmalari
EXCLUDED_EXTENSIONS = {".pyc", ".pyo", ".db", ".log"}


def should_include(path: str, filename: str) -> bool:
    """Berilgan fayl arxivga qo'shilishi kerakligini aniqlaydi."""
    if filename in EXCLUDED_FILES:
        return False
    _, ext = os.path.splitext(filename)
    if ext in EXCLUDED_EXTENSIONS:
        return False
    return True


def create_zip(project_dir: str = ".", output_filename: str = "media_bot.zip") -> None:
    """
    Loyiha papkasidagi barcha kerakli fayllarni bitta zip arxiviga yig'adi.

    Args:
        project_dir: Loyiha joylashgan papka yo'li (default: joriy papka).
        output_filename: Yaratiladigan zip faylining nomi.
    """
    project_dir = os.path.abspath(project_dir)
    output_path = os.path.join(project_dir, output_filename)

    file_count = 0

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            # Istalmagan papkalarni "dirs" ro'yxatidan olib tashlaymiz -
            # shunda os.walk ularning ichiga umuman kirmaydi
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

            for filename in files:
                # Zip faylining o'zini ham arxivga qo'shib yubormaslik uchun
                if filename == output_filename:
                    continue

                if not should_include(root, filename):
                    continue

                file_path = os.path.join(root, filename)
                # Arxiv ichida nisbiy (relative) yo'l bilan saqlaymiz
                arcname = os.path.relpath(file_path, project_dir)
                zipf.write(file_path, arcname)
                file_count += 1
                print(f"  ✓ Qo'shildi: {arcname}")

    print(f"\n✅ Tayyor! {file_count} ta fayl '{output_filename}' arxiviga joylashtirildi.")
    print(f"📦 Fayl manzili: {output_path}")


if __name__ == "__main__":
    create_zip()
