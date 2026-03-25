import urllib.request
import os

url = "https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
dest = "chinook.db"

if os.path.exists(dest):
    print("chinook.db already exists, skipping.")
else:
    print("Downloading chinook.db...")
    urllib.request.urlretrieve(url, dest)
    print("Done! chinook.db is ready.")

