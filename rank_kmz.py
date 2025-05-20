import os
import glob
import zipfile
import re
from io import BytesIO
from PIL import Image  # Requires Pillow

def find_kmz_files():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    kmz_files = glob.glob(os.path.join(script_dir, '*.kmz'))
    return kmz_files

def find_cloakp_png_in_kmz(kmz_path):
    # Match files like cloakpN44W094.png (cloakp, then anything, then .png)
    pattern = re.compile(r'^cloakp.*\.png$', re.IGNORECASE)
    found_files = []
    with zipfile.ZipFile(kmz_path, 'r') as z:
        for name in z.namelist():
            if pattern.match(os.path.basename(name)):
                found_files.append(name)
    return found_files

def count_opaque_pixels(png_bytes):
    with Image.open(BytesIO(png_bytes)) as img:
        img = img.convert("RGBA")
        alpha = img.getchannel("A")
        # Count pixels where alpha == 255 (fully opaque)
        opaque_count = sum(1 for pixel in alpha.getdata() if pixel == 255)
        return opaque_count

area_per_pixel = (1.5625/1000.0)/2.0
def main():
    kmz_files = find_kmz_files()
    results = []
    for kmz in kmz_files:
        total_opaque = 0
        with zipfile.ZipFile(kmz, 'r') as z:
            matches = find_cloakp_png_in_kmz(kmz)
            for match in matches:
                with z.open(match) as png_file:
                    png_bytes = png_file.read()
                    opaque_count = count_opaque_pixels(png_bytes)
                    total_opaque += opaque_count
        area = total_opaque * area_per_pixel
        results.append((os.path.basename(kmz), total_opaque, area))

    # Sort by most pixels to least
    results.sort(key=lambda x: x[1], reverse=True)

    # Print CSV header
    print("Area is in square miles and assumes 2 acres per pixel")
    print("file name,pixels,area")
    for filename, pixels, area in results:
        print(f"{filename},{pixels},{area}")

if __name__ == "__main__":
    main()