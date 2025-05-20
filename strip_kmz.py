import os
import glob
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET

def find_kmz_files():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    kmz_files = glob.glob(os.path.join(script_dir, '*.kmz'))
    return kmz_files

def edit_kml_content(kml_content):
    # Parse the KML as XML
    ET.register_namespace('', "http://earth.google.com/kml/2.1")
    root = ET.fromstring(kml_content)
    ns = {'kml': "http://earth.google.com/kml/2.1"}

    # Find the Document element
    document = root.find('kml:Document', ns)
    if document is not None:
        # Find all Placemark elements
        placemarks = document.findall('kml:Placemark', ns)
        for placemark in placemarks:
            snippet = placemark.find('kml:Snippet', ns)
            if snippet is not None and snippet.text == "position of viewer":
                document.remove(placemark)
                break  # Remove only the first matching Placemark

    # Return the modified XML as a string
    return ET.tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')

def process_kmz_file(kmz_path):
    with zipfile.ZipFile(kmz_path, 'r') as zin:
        with tempfile.TemporaryDirectory() as tempdir:
            zin.extractall(tempdir)
            # Find the KML file at the root of the zip
            kml_file = None
            for name in zin.namelist():
                if name.lower().endswith('.kml') and '/' not in name:
                    kml_file = name
                    break
            if kml_file:
                kml_path = os.path.join(tempdir, kml_file)
                with open(kml_path, 'r', encoding='utf-8') as f:
                    kml_content = f.read()
                new_kml_content = edit_kml_content(kml_content)
                with open(kml_path, 'w', encoding='utf-8') as f:
                    f.write(new_kml_content)
            # Create a new KMZ with the modified KML
            temp_kmz = kmz_path + '.tmp'
            with zipfile.ZipFile(temp_kmz, 'w', zipfile.ZIP_DEFLATED) as zout:
                for foldername, subfolders, filenames in os.walk(tempdir):
                    for filename in filenames:
                        file_path = os.path.join(foldername, filename)
                        arcname = os.path.relpath(file_path, tempdir)
                        zout.write(file_path, arcname)
            shutil.move(temp_kmz, kmz_path)

def main():
    for kmz_file in find_kmz_files():
        process_kmz_file(kmz_file)
        print(f"Stripped {kmz_file}")

if __name__ == "__main__":
    main()