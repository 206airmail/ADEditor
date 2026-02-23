import os
import zipfile
import glob

def create_help_zip(lang, doc_dir, base_dir):
    """Create a ZIP file for the specified language from its doc directory."""
    output_filename = f"Help-ADEditor-{lang}.zip"
    output_path = os.path.join(base_dir, 'langs', output_filename)

    print(f"Creating {output_filename} from {doc_dir}...")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Create ZIP file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through the directory
        for root, dirs, files in os.walk(doc_dir):
            for file in files:
                # Filter for relevant files (html, hhp, hhc, hhk, images, css, etc.)
                if file.endswith(('.html', '.htm', '.hhp', '.hhc', '.hhk', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg')):
                    file_path = os.path.join(root, file)
                    # Calculate arcname (relative path inside zip)
                    arcname = os.path.relpath(file_path, doc_dir)
                    zipf.write(file_path, arcname)
                    print(f"  Added {arcname}")

    print(f"Successfully created {output_filename}")

def main():
    # Define paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_root = os.path.join(base_dir, 'doc')
    
    if not os.path.exists(docs_root):
        print(f"Error: Documentation root '{docs_root}' not found.")
        return

    # List all subdirectories in doc/
    found_langs = 0
    for item in os.listdir(docs_root):
        item_path = os.path.join(docs_root, item)
        if os.path.isdir(item_path):
            # We assume the directory name is the language code (e.g., 'en', 'fr')
            # skip hidden folders (starting with .)
            if not item.startswith('.'):
                create_help_zip(item, item_path, base_dir)
                found_langs += 1
    
    if found_langs == 0:
        print("No language folders found in 'doc/'.")
    else:
        print(f"Processed {found_langs} language(s).")

if __name__ == "__main__":
    main()
