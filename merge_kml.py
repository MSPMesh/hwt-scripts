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

def collect_cloakp_images_from_kmz_files():
    """
    Returns a dictionary: {cloakp file name: [image data from each kmz]}
    """
    kmz_files = find_kmz_files()
    cloakp_dict = {}

    # For each kmz, extract image data for each cloakp image
    for kmz_path in kmz_files:
        # Skip KMZs with the flag file
        with zipfile.ZipFile(kmz_path, 'r') as z:
            if "DO_NOT_USE_AS_INPUT.flag" in z.namelist():
                print(f"Skipping {kmz_path} (contains DO_NOT_USE_AS_INPUT.flag)")
                continue
            # Find all cloakp image names in this kmz
            cloakp_names = find_cloakp_png_in_kmz(kmz_path)
            # Add new image names to the dict if not already present
            for name in cloakp_names:
                base_name = os.path.basename(name)
                if base_name not in cloakp_dict:
                    cloakp_dict[base_name] = []
                with z.open(name) as img_file:
                    image_data = img_file.read()
                    cloakp_dict[base_name].append(image_data)
    return cloakp_dict

def generate_overlap_visualizations(cloakp_dict):
    """
    For each image group in the dict, generates a new image where the color of each pixel
    depends on the number of overlapping opaque pixels at that location:
        0: transparent
        1: red
        2: yellow
        3 or more: green
    Returns a dict: {image name: PIL.Image object}
    """
    result_images = {}
    for img_name, img_datas in cloakp_dict.items():
        if not img_datas:
            continue

        # Open all images and convert to RGBA
        imgs = [Image.open(BytesIO(data)).convert('RGBA') for data in img_datas]
        width, height = imgs[0].size
        num_imgs = len(imgs)

        # Get alpha channels for all images
        alphas = [img.getchannel('A') for img in imgs]
        alpha_datas = [list(alpha.getdata()) for alpha in alphas]

        # Prepare output image (RGBA)
        out_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        out_pixels = out_img.load()

        for y in range(height):
            for x in range(width):
                idx = y * width + x
                # Count how many images have opaque pixel at this location
                opaque_count = sum(alpha_data[idx] == 255 for alpha_data in alpha_datas)
                if opaque_count == 0:
                    out_pixels[x, y] = (0, 0, 0, 0)  # transparent
                elif opaque_count == 1:
                    out_pixels[x, y] = (255, 0, 0, 255)  # red
                elif opaque_count == 2:
                    out_pixels[x, y] = (255, 255, 0, 255)  # yellow
                else:  # 3 or more
                    out_pixels[x, y] = (0, 255, 0, 255)  # green

        result_images[img_name] = out_img

    return result_images

def generate_ground_overlay_xml(filename):
    """
    Given a filename like 'cloakpN44W093.png', generate the corresponding GroundOverlay XML string.
    """
    import re

    # Extract coordinates from filename
    match = re.match(r'cloakp([NS])(\d+)([EW])(\d+)\.png', filename, re.IGNORECASE)
    if not match:
        raise ValueError(f"Filename {filename} does not match expected pattern.")

    lat_dir, lat, lon_dir, lon = match.groups()
    lat = int(lat)
    lon = int(lon)

    # Calculate bounding box
    south = lat if lat_dir.upper() == 'N' else -lat
    north = south + 1 if lat_dir.upper() == 'N' else south - 1
    west = -lon if lon_dir.upper() == 'W' else lon
    east = west + 1 if lon_dir.upper() == 'W' else west - 1

    # Build XML string
    xml = f"""<GroundOverlay>
  <name>{lat_dir}{lat}{lon_dir}{str(lon).zfill(3)}</name>
  <visibility>1</visibility>
  <drawOrder>0</drawOrder>
  <color>90ffffff</color>
  <Icon><href>{filename}</href></Icon>
  <LatLonBox>
    <south>{south}</south>
    <west>{west}</west>
    <north>{north}</north>
    <east>{east}</east>
    <rotation>0</rotation>
  </LatLonBox>
</GroundOverlay>"""
    return xml

xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.1">


<Document id="CombinedMap">
  <name>CombinedMap</name>
  <visibility>1</visibility>
  <open>0</open>
  <LookAt><latitude>44.986656</latitude><longitude>-93.258133</longitude><range>10000</range><tilt>0</tilt><heading>0</heading></LookAt>  

!!!GROUND_OVERLAYS!!!

</Document>
</kml>
"""

def save_kmz(overlap_images, kml_output, kmz_filename="output.kmz"):
    """
    Saves the provided images and KML output into a KMZ (zip) file.
    overlap_images: dict of {filename: PIL.Image}
    kml_output: string containing the KML XML
    kmz_filename: output KMZ file name (default: output.kmz)
    """
    import zipfile

    with zipfile.ZipFile(kmz_filename, 'w', zipfile.ZIP_DEFLATED) as kmz:
        # Write the KML file
        kmz.writestr("combined.kml", kml_output)

        # Write each image
        for img_name, img in overlap_images.items():
            img_bytes = BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            kmz.writestr(img_name, img_bytes.read())
        # Write the special flag file
        kmz.writestr("DO_NOT_USE_AS_INPUT.flag", b"This KMZ was generated as output and should not be used as input.")
    print(f"Saved KMZ as {kmz_filename}")

def main():
    cloakp_images = collect_cloakp_images_from_kmz_files()
    if not cloakp_images:
        print("No KMZ files or cloakp images found.")
        return
    for img_name, img_list in cloakp_images.items():
        print(f"{img_name}: {len([img for img in img_list if img is not None])} images found in KMZ files")
    
    # Generate overlap visualization images
    overlap_images = generate_overlap_visualizations(cloakp_images)

    # Print GroundOverlay XML for each image
    overlay_xmls = []
    for img_name, img in overlap_images.items():
        xml_data = generate_ground_overlay_xml(img_name)
        overlay_xmls.append(xml_data)
    
    # Combine all XML data into the template
    ground_overlays = "\n".join(overlay_xmls)
    kml_output = xml_template.replace("!!!GROUND_OVERLAYS!!!", ground_overlays)

    save_kmz(overlap_images, kml_output, "CombinedSanitized.kmz")




if __name__ == "__main__":
    main()