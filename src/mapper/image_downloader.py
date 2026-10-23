import requests
from pathlib import Path
from typing import List
from config.settings import STAGED_IMAGES_DIR, USER_AGENT

def download_item_images(item_id: str, image_urls: List[str], max_images: int = 10) -> List[Path]:
    """Downloads images to a local folder ready for browser file input upload."""
    item_dir = STAGED_IMAGES_DIR / str(item_id)
    item_dir.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT}
    saved_paths: List[Path] = []

    for idx, url in enumerate(image_urls[:max_images]):
        ext = ".jpg"
        if ".png" in url.lower():
            ext = ".png"
        elif ".webp" in url.lower():
            ext = ".webp"

        file_path = item_dir / f"image_{idx:02d}{ext}"

        # If file already downloaded and not empty, skip
        if file_path.exists() and file_path.stat().st_size > 1024:
            saved_paths.append(file_path)
            continue

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 1024:
                with open(file_path, "wb") as f:
                    f.write(resp.content)
                saved_paths.append(file_path)
        except Exception as e:
            print(f"Warning: Failed downloading image {url}: {e}")

    return saved_paths
