import os
import math
import time
import requests
from PIL import Image
import shutil

print("🗺️  Welcome to the OGF Map Extracter 🗺️")
time.sleep(2)
print("⚠️  The extracted map will be located in your downloads folder ⚠️")
time.sleep(2)
print("❗ Cancel the program at any point by pressing Ctrl+C ❗")
time.sleep(2)

print("\n📍  Select Coordinate Configuration 📍:")
print("1. East Uletha")
print("2. East Uletha Minor")
print("3. Tarephia")
print("9. Custom Coordinates")
print("0. Exit")

choice = int(input("Selection: "))
exit = False


if choice == 1:
    bbox = {
        "lat_top": 72.548,
        "lon_left": 63.140,
        "lat_bottom": 23.016,
        "lon_right": 175.702
    }

elif choice == 2:
    bbox = {
        "lat_top": 47.904,
        "lon_left": 96.895,
        "lat_bottom": 25.247,
        "lon_right": 150.051
    }

elif choice == 3:
    bbox = {
        "lat_top": 35.4212,
        "lon_left": -17.3502,
        "lat_bottom": -26.8107,
        "lon_right": 58.8065
    }

elif choice == 9:
    lattop = round(float(input("Uppermost Latitude: ")), 3)
    lonleft = round(float(input("Leftmost Longitude: ")), 3)
    latbot = round(float(input("Bottomost Latitude: ")), 3)
    lonright = round(float(input("Rightmost Longitude: ")), 3)

    bbox = {
        "lat_top": lattop,
        "lon_left": lonleft,
        "lat_bottom": latbot,
        "lon_right": lonright
    }

else:
    print("Exiting Program...")
    exit = True

if not exit:
    zoom = int(input("Zoom Level: "))
    print()


    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    output_dir = os.path.join(downloads_dir, "ogf_z8_bbox")
    stitched_filename = os.path.join(downloads_dir, "ogf_bbox_map.png")

    delay = 0.1
    max_retries = 5

    os.makedirs(output_dir, exist_ok=True)

    def latlon_to_tile(lat, lon, z):
        lat_rad = math.radians(lat)
        n = 2 ** z
        x_tile = int((lon + 180.0) / 360.0 * n)
        y_tile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return x_tile, y_tile

    x_min, y_max = latlon_to_tile(bbox["lat_bottom"], bbox["lon_left"], zoom)
    x_max, y_min = latlon_to_tile(bbox["lat_top"], bbox["lon_right"], zoom)

    #print(f"Tile X range: {x_min} to {x_max}; Tile Y range: {y_min} to {y_max}")

    tiles = {}

    total_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
    tiles_downloaded = 0

    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            path = os.path.join(output_dir, f"{x}_{y}.png")
            if os.path.exists(path):
                tiles_downloaded += 1
            else:
                for attempt in range(max_retries):
                    try:
                        url = f"https://tile.opengeofiction.net/ogf-carto/{zoom}/{x}/{y}.png"
                        r = requests.get(url, timeout=15)
                        if r.status_code == 200:
                            with open(path, "wb") as f:
                                f.write(r.content)
                            tiles_downloaded += 1
                            break
                        else:
                            print(f"Failed {x},{y} - status {r.status_code}")
                    except Exception as e:
                        print(f"Error downloading {x},{y} attempt {attempt+1} - {e}")
                    time.sleep(delay)
                else:
                    print(f"⚠️ Skipping {x},{y} after {max_retries} failed attempts")
                    continue

            percent = (tiles_downloaded / total_tiles) * 100
            print(f"Progress: {tiles_downloaded}/{total_tiles} tiles ({percent:.2f}%)", end='\r')

            if os.path.exists(path):
                try:
                    tiles[(x, y)] = Image.open(path)
                except Exception as e:
                    print(f"Error opening {x},{y} - {e}")

    print("\nAll available tiles downloaded. Stitching now...")

    tile_width, tile_height = 256, 256
    map_width = (x_max - x_min + 1) * tile_width
    map_height = (y_max - y_min + 1) * tile_height
    stitched_map = Image.new("RGB", (map_width, map_height), (255, 255, 255))

    for (x, y), img in tiles.items():
        px = (x - x_min) * tile_width
        py = (y - y_min) * tile_height
        stitched_map.paste(img, (px, py))

    stitched_map.save(stitched_filename)

    try:
        shutil.rmtree(output_dir)
        print(f"Temporary folder '{output_dir}' deleted.")
    except Exception as e:
        print(f"Could not delete temp folder: {e}")

    print()
    print(f"Stitched map saved as {stitched_filename}!")
    print("Thank for for using the OGF Map Extracter. Made with ❤️  and ☕ by ParrotMan.")