import os
import requests
import zipfile
import xml.etree.ElementTree as ET


new_kml_template = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.1">

<Document>
    <name>!!!NAME!!!</name>
    <visibility>1</visibility>
    <open>0</open>
    <Placemark>
        <name>!!!NAME!!!</name>
        <Snippet>position of viewer</Snippet>
        <Point>
            <altitudeMode>relativeToGround</altitudeMode>
            <coordinates>!!!COORDINATES!!!</coordinates>
        </Point>
    </Placemark>
    <Folder>
        <name>Visibility cloak</name>
        <open>1</open>
        !!!GROUND_OVERLAYS!!!
    </Folder>
</Document>
</kml>
"""

def generate_ground_overlay_xml(coord_str):
    """
    Given a string like 'N44W093', generate the corresponding GroundOverlay XML string.
    The output href will be 'cloakpN44W093.png'.
    """
    import re

    # Extract coordinates from string
    match = re.match(r'([NS])(\d+)([EW])(\d+)', coord_str, re.IGNORECASE)
    if not match:
        raise ValueError(f"Coordinate string {coord_str} does not match expected pattern.")

    lat_dir, lat, lon_dir, lon = match.groups()
    lat = int(lat)
    lon = int(lon)

    # Calculate bounding box
    south = lat if lat_dir.upper() == 'N' else -lat
    north = south + 1 if lat_dir.upper() == 'N' else south - 1
    west = -lon if lon_dir.upper() == 'W' else lon
    east = west + 1 if lon_dir.upper() == 'W' else west - 1

    filename = f"cloakp{lat_dir.upper()}{lat:02d}{lon_dir.upper()}{int(lon):03d}.png"

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

def build_new_kml_from_names(name: str, coordinates: str, go_names: list) -> str:
    """
    Takes a name, coordinates, and a list of ground overlay names (like 'N44W093'),
    generates the GroundOverlay XML for each using generate_ground_overlay_xml,
    and inserts them into the new_kml_template. Returns the resulting KML string.
    """
    ground_overlays = [generate_ground_overlay_xml(go_name) for go_name in go_names]
    overlays_str = "\n".join(ground_overlays)
    kml_str = new_kml_template.replace("!!!NAME!!!", name)
    kml_str = kml_str.replace("!!!COORDINATES!!!", coordinates)
    kml_str = kml_str.replace("!!!GROUND_OVERLAYS!!!", overlays_str)
    return kml_str

import zipfile

def write_kml_to_zip(kml_str: str, name: str, top_level_folder: str, go_names: list, go_hrefs: list):
    """
    Creates a zip file named after 'name' in the supplied top_level_folder,
    containing the KML string as '{name}.kml' at the root of the zip,
    and all PNG images (downloaded from go_hrefs) at the root of the zip,
    named as in generate_ground_overlay_xml.
    """
    # Sanitize file and folder names
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()
    zip_dir = os.path.join(top_level_folder)
    os.makedirs(zip_dir, exist_ok=True)
    zip_filename = os.path.join(zip_dir, f"{safe_name}.kmz")
    kml_filename = f"{safe_name}.kml"

    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Write the KML file
        zipf.writestr(kml_filename, kml_str)
        # Write each PNG image
        for go_name, href in zip(go_names, go_hrefs):
            # Generate the filename as in generate_ground_overlay_xml
            import re
            match = re.match(r'([NS])(\d+)([EW])(\d+)', go_name, re.IGNORECASE)
            if not match:
                raise ValueError(f"Ground overlay name {go_name} does not match expected pattern.")
            lat_dir, lat, lon_dir, lon = match.groups()
            filename = f"cloakp{lat_dir.upper()}{int(lat):02d}{lon_dir.upper()}{int(lon):03d}.png"
            try:
                img_bytes = download_png_to_memory(href)
                zipf.writestr(filename, img_bytes)
            except Exception as e:
                print(f"Failed to download or write image for {go_name}: {e}")

def download_png_to_memory(href: str) -> bytes:
    """
    Downloads a PNG image from the given href URL and returns its content as bytes.
    Raises an exception if the download fails or the response is not a PNG.
    """
    response = requests.get(href)
    if response.status_code != 200:
        raise ValueError(f"Failed to download image from {href} (status code {response.status_code})")
    if not response.headers.get("Content-Type", "").startswith("image/png"):
        raise ValueError(f"URL {href} did not return a PNG image (Content-Type: {response.headers.get('Content-Type')})")
    return response.content


# Find the first .kml file in the same directory as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
kml_file = None

for filename in os.listdir(script_dir):
    if filename.lower().endswith('.kml'):
        kml_file = os.path.join(script_dir, filename)
        break

if kml_file:
    # Parse the KML file as XML
    tree = ET.parse(kml_file)
    root = tree.getroot()

    # KML uses namespaces, so we need to handle them
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    # Find the Document element
    document = root.find('kml:Document', ns)
    if document is not None:
        # Find all top-level Folder tags under Document
        folders = document.findall('kml:Folder', ns)
        for folder in folders:
            name_elem = folder.find('kml:name', ns)
            if name_elem is None or not name_elem.text or not name_elem.text.strip():
                raise ValueError("Missing required <name> in top-level <Folder>")
            folder_name = name_elem.text.strip()
            # Create a directory for each folder name
            dir_path = os.path.join(script_dir, folder_name)
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                print(f"Failed to create directory '{dir_path}': {e}")
            # Process subfolders under this top-level folder
            subfolders = folder.findall('kml:Folder', ns)
            if subfolders:
                for subfolder in subfolders:
                    sub_name_elem = subfolder.find('kml:name', ns)
                    if sub_name_elem is None or not sub_name_elem.text or not sub_name_elem.text.strip():
                        raise ValueError(f"Missing required <name> in subfolder of '{folder_name}'")
                    subfolder_name = sub_name_elem.text.strip()
                    # Check if KMZ already exists, skip if so
                    safe_name = "".join(c for c in subfolder_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
                    kmz_path = os.path.join(folder_name, f"{safe_name}.kmz")
                    if os.path.exists(kmz_path):
                        print(f"Skipping '{kmz_path}' (already exists)")
                        continue  # Skip this subfolder if KMZ exists
                    # Find Placemark under subfolder and extract coordinates
                    placemark = subfolder.find('kml:Placemark', ns)
                    if placemark is None:
                        raise ValueError(f"Missing required <Placemark> in subfolder '{subfolder_name}'")
                    point = placemark.find('kml:Point', ns)
                    if point is None:
                        raise ValueError(f"Missing required <Point> in Placemark of subfolder '{subfolder_name}'")
                    coords_elem = point.find('kml:coordinates', ns)
                    if coords_elem is None or not coords_elem.text or not coords_elem.text.strip():
                        raise ValueError(f"Missing required <coordinates> in Point of subfolder '{subfolder_name}'")
                    coordinates = coords_elem.text.strip()
                    # Find "Visibility cloak" folder under this subfolder
                    vis_cloak_folder = None
                    for f in subfolder.findall('kml:Folder', ns):
                        f_name_elem = f.find('kml:name', ns)
                        if f_name_elem is not None and f_name_elem.text and f_name_elem.text.strip() == "Visibility cloak":
                            vis_cloak_folder = f
                            break
                    go_names = []
                    go_hrefs = []
                    if vis_cloak_folder is not None:
                        ground_overlays = vis_cloak_folder.findall('kml:GroundOverlay', ns)
                        for go in ground_overlays:
                            go_name_elem = go.find('kml:name', ns)
                            if go_name_elem is None or not go_name_elem.text or not go_name_elem.text.strip():
                                raise ValueError("Missing required <name> in <GroundOverlay>")
                            go_names.append(go_name_elem.text.strip())
                            # Get the href field
                            icon_elem = go.find('kml:Icon/kml:href', ns)
                            if icon_elem is None or not icon_elem.text or not icon_elem.text.strip():
                                raise ValueError("Missing required <href> in <GroundOverlay>")
                            go_hrefs.append(icon_elem.text.strip())
                    # Now go_names is a list of N44W093 strings, and go_hrefs is a list of hrefs in the same order
                    # You can use both lists as needed
                    new_kml = build_new_kml_from_names(subfolder_name, coordinates, go_names)
                    print(f"Creating '{kmz_path}'")
                    write_kml_to_zip(new_kml, subfolder_name, folder_name, go_names, go_hrefs)
                    
    else:
        raise ValueError("No KML file found in the script directory.")