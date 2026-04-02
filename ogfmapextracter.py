import os
import math
import time
import requests
from PIL import Image
import shutil
import random

print("🗺️  Welcome to the OGF Map Extracter 🗺️")
time.sleep(2)
print("⚠️  The extracted map will be located in your downloads folder ⚠️")
time.sleep(2)
print("❗ Cancel the program at any point by pressing Ctrl+C ❗")
time.sleep(2)

print("\nSelect Coordinate Configuration:")
print("1. East Uletha")
print("2. East Uletha Minor")
print("3. Tarephia")
print("8. World")
print("9. Custom Coordinates")
print("0. Exit")

choice = int(input("\n> Selection: "))
exit = False

if choice == 1:
    bbox = {"lat_top": 72.548, "lon_left": 63.140, "lat_bottom": 23.016, "lon_right": 175.702}
elif choice == 2:
    bbox = {"lat_top": 47.904, "lon_left": 96.895, "lat_bottom": 25.247, "lon_right": 150.051}
elif choice == 3:
    bbox = {"lat_top": 35.4212, "lon_left": -17.3502, "lat_bottom": -26.8107, "lon_right": 58.8065}
elif choice == 8:
    bbox = {"lat_top": 80.6825, "lon_left": -18.1100, "lat_bottom": -75.9798, "lon_right": 179.8627}
elif choice == 9:
    lattop = round(float(input("Uppermost Latitude: ")), 3)
    lonleft = round(float(input("Leftmost Longitude: ")), 3)
    latbot = round(float(input("Bottommost Latitude: ")), 3)
    lonright = round(float(input("Rightmost Longitude: ")), 3)
    bbox = {"lat_top": lattop, "lon_left": lonleft, "lat_bottom": latbot, "lon_right": lonright}
else:
    print("Exiting Program...")
    exit = True

if not exit:
    zoom = int(input("> Zoom Level: "))
    print("\nThe following will split up the output into smaller chunks. Enter 1 for both if you want just one image.")
    numrows = int(input("> Number of Rows: "))
    numcols = int(input("> Number of Columns: "))
    print()

    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    output_dir = os.path.join(downloads_dir, "ogf_z8_bbox")
    os.makedirs(output_dir, exist_ok=True)

    request_interval = 0.25
    next_request_time = time.time()
    max_retries = 5

    session = requests.Session()
    session.headers.update({"User-Agent": "OGF-Extractor"})

    def latlon_to_tile(lat, lon, z):
        lat_rad = math.radians(lat)
        n = 2 ** z
        x_tile = int((lon + 180.0) / 360.0 * n)
        y_tile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return x_tile, y_tile

    x_min, y_max = latlon_to_tile(bbox["lat_bottom"], bbox["lon_left"], zoom)
    x_max, y_min = latlon_to_tile(bbox["lat_top"], bbox["lon_right"], zoom)

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
                        now = time.time()
                        if now < next_request_time:
                            time.sleep(next_request_time - now)

                        url = f"https://tile.opengeofiction.net/ogf-carto/{zoom}/{x}/{y}.png"
                        r = session.get(url, timeout=15)

                        next_request_time += request_interval + random.uniform(-0.02, 0.02)

                        if r.status_code == 200:
                            with open(path, "wb") as f:
                                f.write(r.content)
                            tiles_downloaded += 1
                            break
                        else:
                            print(f"Failed {x},{y} - status {r.status_code}")

                    except Exception as e:
                        print(f"Error downloading {x},{y} attempt {attempt+1} - {e}")

                    time.sleep(0.1 * (attempt + 1))
                else:
                    print(f"⚠️  Skipping {x},{y} after {max_retries} failed attempts ⚠️")
                    continue

            percent = (tiles_downloaded / total_tiles) * 100
            print(f"Progress: {tiles_downloaded}/{total_tiles} tiles ({percent:.2f}%)", end='\r')

            if os.path.exists(path):
                try:
                    tiles[(x, y)] = Image.open(path)
                except Exception as e:
                    print(f"Error opening {x},{y} - {e}")

    print("\nAll available tiles downloaded. Stitching into grid images now...")

    tile_width, tile_height = 256, 256
    tiles_x_count = x_max - x_min + 1
    tiles_y_count = y_max - y_min + 1

    # Compute how many tiles per output image
    tiles_per_chunk_x = tiles_x_count // numcols
    tiles_per_chunk_y = tiles_y_count // numrows

    # For remainders, we'll extend the last chunk
    remainder_x = tiles_x_count % numcols
    remainder_y = tiles_y_count % numrows

    output_folder = os.path.join(downloads_dir, "ogf_grid_output")
    os.makedirs(output_folder, exist_ok=True)

    for row in range(numrows):
        for col in range(numcols):
            chunk_width_tiles = tiles_per_chunk_x + (1 if col == numcols - 1 and remainder_x > 0 else 0) * remainder_x
            chunk_height_tiles = tiles_per_chunk_y + (1 if row == numrows - 1 and remainder_y > 0 else 0) * remainder_y

            chunk = Image.new(
                "RGB",
                (chunk_width_tiles * tile_width, chunk_height_tiles * tile_height),
                (255, 255, 255)
            )

            for dx in range(chunk_width_tiles):
                for dy in range(chunk_height_tiles):
                    tile_x = x_min + col * tiles_per_chunk_x + dx
                    tile_y = y_min + row * tiles_per_chunk_y + dy

                    if (tile_x, tile_y) in tiles:
                        px = dx * tile_width
                        py = dy * tile_height
                        chunk.paste(tiles[(tile_x, tile_y)], (px, py))

            filename = os.path.join(output_folder, f"map_r{row}_c{col}.png")
            chunk.save(filename)

    try:
        shutil.rmtree(output_dir)
        print(f"Temporary folder '{output_dir}' deleted.")
    except Exception as e:
        print(f"Could not delete temp folder: {e}")

    print(f"\nGrid images saved in: {output_folder}!")
    print("Thanks for using the OGF Map Extracter. Made with ❤️  and ☕ by ParrotMan.\n")

    timeleft = 10
    while timeleft > 0:
        print(f"Automatically closing this window in {timeleft} seconds    ", end='\r')
        time.sleep(1)
        timeleft -= 1