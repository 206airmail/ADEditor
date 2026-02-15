import os
from pathlib import Path

def list_python_files(start_directory=None, exclude_dirs=None, exclude_files=None):
    """
    List all .py files in a directory tree, excluding specified subdirectories and files.
    
    Args:
        start_directory: Path to the directory to search. 
                        If None, uses the parent directory of the script.
        exclude_dirs: List of directory names to exclude from search.
                     Common examples: ['venv', '.git', '__pycache__', 'node_modules']
        exclude_files: List of file names to exclude from results.
                      Common examples: ['__init__.py', 'setup.py', 'conftest.py']
    """
    # Default exclusions if none provided
    if exclude_dirs is None:
        exclude_dirs = ['venv', '__pycache__', '.git', 'Tools', 'Tests', 'Original', 'FS25_AutoDrive', 'Examples', 'Antigravity']
    
    if exclude_files is None:
        exclude_files = ['__init__.py']
    
    # If no directory specified, use the parent directory of the script
    if start_directory is None:
        start_directory = Path(__file__).parent.parent
    else:
        start_directory = Path(start_directory)
    
    # Check that the directory exists
    if not start_directory.exists():
        print(f"Error: Directory '{start_directory}' does not exist.")
        return []
    
    print(f"Searching for .py files in: {start_directory.absolute()}")
    print(f"Excluding directories: {', '.join(exclude_dirs) if exclude_dirs else 'None'}")
    print(f"Excluding files: {', '.join(exclude_files) if exclude_files else 'None'}\n")
    
    # List to store found files
    python_files = []
    
    # Recursively traverse all files
    for file_path in start_directory.rglob("*.py"):
        # Check if any excluded directory is in the file path
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            continue
        
        # Check if the file name is in the excluded files list
        if file_path.name in exclude_files:
            continue
        
        python_files.append(file_path)
        print(f"  {file_path.relative_to(start_directory)}")
    
    print(f"\nTotal: {len(python_files)} .py file(s) found")
    
    return python_files


if __name__ == "__main__":
    # Default usage: parent directory of the script with default exclusions
    files = list_python_files()
    tmpFile = os.path.join(Path(__file__).parent, 'inputfiles.list')
    with open(tmpFile, 'w') as f:
        for file in files:
            f.write(str(file) + '\n')
    
    # Prepare the xgettext command line
    output_pot = os.path.join(Path(__file__).parent.parent, 'langs', 'adeditor.pot')
    exclude_pot = os.path.join(Path(__file__).parent.parent, 'langs', 'wx-3.2.pot')
    xgettext_cmd = f"xgettext --language=Python --keyword=_ --output={output_pot} --files-from={tmpFile} --exclude-file={exclude_pot}"

    # Launch the xgettext command
    print(f"\nRunning command:\n{xgettext_cmd}\n")
    os.system(xgettext_cmd)

    # Remove the temporary file
    os.remove(tmpFile)
