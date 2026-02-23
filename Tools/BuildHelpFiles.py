import os
import zipfile
import glob

def create_help_zip(lang, output_filename):
    # Define paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"base_dir = {base_dir}")
    doc_dir = os.path.join(base_dir, 'doc', lang)
    print(f"doc_dir = {doc_dir}")
    output_path = os.path.join(base_dir, 'langs', output_filename)
    print(f"output_path = {output_path}")

    print(f"Creating {output_filename} from {doc_dir}...")

    # Create ZIP file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through the directory
        for root, dirs, files in os.walk(doc_dir):
            for file in files:
                # Filter for relevant files (html, hhp, hhc, hhk, images, css)
                # For now, we'll include everything except maybe temporary files if any
                if file.endswith(('.html', '.htm', '.hhp', '.hhc', '.hhk', '.css', '.png', '.jpg', '.gif')):
                    file_path = os.path.join(root, file)
                    # Calculate arcname (relative path inside zip)
                    # We want a flat structure or relative to doc_dir?
                    # wxWidgets help controller usually expects files to be relative to the project file
                    # If we zip the contents of 'doc/en', 'index.html' should be at root of zip.
                    arcname = os.path.relpath(file_path, doc_dir)
                    zipf.write(file_path, arcname)
                    print(f"  Added {arcname}")

    print(f"Successfully created {output_path}")

if __name__ == "__main__":
    create_help_zip('en', 'Help-ADEditor-en.zip')
    create_help_zip('fr', 'Help-ADEditor-fr.zip')
