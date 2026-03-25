"""
setup_db.py
------------
Run this once before starting the app to auto-download chinook.db.

Usage:
    python setup_db.py
"""

import urllib.request
import zipfile
import shutil
from pathlib import Path

DB_PATH = Path("chinook.db")

# Direct download URL for the SQLite version of Chinook
CHINOOK_URL = (
    "https://github.com/lerocha/chinook-database/releases/download/"
    "v1.4.5/ChinookDatabase1.4.5_CompleteVersion.zip"
)


def download_chinook():
    if DB_PATH.exists():
        print(f"chinook.db already exists at {DB_PATH.resolve()} — nothing to do.")
        return

    print("Downloading Chinook database...")
    zip_path = Path("chinook_temp.zip")

    try:
        urllib.request.urlretrieve(CHINOOK_URL, zip_path)
        print("Download complete. Extracting...")

        with zipfile.ZipFile(zip_path, "r") as z:
            # Find the SQLite file inside the zip
            sqlite_files = [f for f in z.namelist() if f.endswith(".sqlite") or f.endswith(".db")]
            if not sqlite_files:
                raise FileNotFoundError(
                    "Could not find a .sqlite or .db file in the downloaded zip. "
                    "Please download chinook.db manually from: "
                    "https://github.com/lerocha/chinook-database/releases"
                )
            # Extract the first match and rename to chinook.db
            source = sqlite_files[0]
            z.extract(source, path=".")
            shutil.move(source, DB_PATH)
            # Clean up any empty extracted folders
            extracted_dir = Path(source).parts[0]
            if Path(extracted_dir).is_dir():
                shutil.rmtree(extracted_dir, ignore_errors=True)

        print(f"chinook.db saved to {DB_PATH.resolve()}")
        print("You're all set — run: streamlit run app.py")

    except Exception as e:
        print(f"Auto-download failed: {e}")
        print(
            "\nManual fallback — download it yourself in one line:\n"
            "  curl -L https://github.com/lerocha/chinook-database/releases/"
            "download/v1.4.5/Chinook_Sqlite.sqlite -o chinook.db"
        )
    finally:
        if zip_path.exists():
            zip_path.unlink()


if __name__ == "__main__":
    download_chinook()