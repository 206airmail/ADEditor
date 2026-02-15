import subprocess
import datetime
import os
from pathlib import Path

def create_7z_archive(exclusions=None):
    """
    Creates a 7z archive containing the CONTENTS of the parent directory,
    excluding the base folder itself.
    """
    # 1. Path Configuration
    current_dir = Path(__file__).parent.absolute()
    target_dir = current_dir.parent
    
    # Use the parent folder's name for the filename
    parent_folder_name = target_dir.name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    archive_name = f"{parent_folder_name}_{timestamp}.7z"
    
    seven_zip_path = r"C:\Program Files\7-Zip\7z.exe"
    output_file = current_dir / archive_name

    # 2. Target the contents specifically
    source_path = str(target_dir / "*")

    # 3. Command Construction
    command = [seven_zip_path, "a", "-t7z", "-mx=9", str(output_file), source_path]

    # 4. Handling Exclusions
    if exclusions:
        for item in exclusions:
            command.append(f"-xr!{item}")

    # 5. Execution
    print(f"--- 7-Zip Archive creation ---")
    print(f"Source contents: {target_dir}")
    print(f"Archive Name: {archive_name}")
    
    subprocess.run(command, check=True, capture_output=True, text=True)
    
    print(f"Success! Archive created at: {output_file}")


if __name__ == "__main__":
    # Define items to exclude
    items_to_exclude = [
        "venv", 
        "__pycache__", 
        "Examples",
        "Tests",
        ".git", 
        "*.adproject",
        "*.lnk",
        "*.7z" 
    ]
    
    create_7z_archive(exclusions=items_to_exclude)
