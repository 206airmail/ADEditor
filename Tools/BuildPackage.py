import sys
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from cx_Freeze import setup, Executable
from Core import AppVersion


def BuildPackage():
    # Initialize variables
    appVers = AppVersion()
    sName = appVers.getAppName() + "-" + appVers.getVersion(False)
    archi = '64' if (sys.maxsize > 2**32) else '32'
    v = sys.version_info
    pyVersion = f"{v[0]}.{v[1]}.{v[2]}"
    pyVersFloat = float(f"{v[0]}.{v[1]}")
    print(f"Building package for {sName}-Win{archi}-Py{pyVersion}")

    myExcludes = [
        'asyncio', 'backports', 'cabarchive', 'filelock',
        'concurrent', 'ctypes', 'distutils', 'freeze_core',
        'html', 'http', 'jaraco', 'json', 'lief', 'logging',
        'packaging', 'pydoc_data',
        'setuptools', 'unittest', 'urllib'
        ]
    myIncludes = []
    # Automatically add language files (.mo) and help archives (.zip) from the 'langs' directory
    langs_dir = Path('langs')
    if langs_dir.exists():
        # Find all .mo files recursively
        for mo_file in langs_dir.rglob('*.mo'):
            rel_path = mo_file.as_posix()
            myIncludes.append((rel_path, rel_path))
        
        # Find all Help-ADEditor-*.zip files in the langs root
        for zip_file in langs_dir.glob('Help-ADEditor-*.zip'):
            rel_path = zip_file.as_posix()
            myIncludes.append((rel_path, rel_path))

    build_exe_options = {
        "build_exe": "build/ADEditor",
        'excludes': myExcludes,
        'include_files': myIncludes,
        "optimize": 2
    }

    base = None
    if sys.platform == "win32":
        if pyVersFloat <= 3.12:
            base = "Win32GUI"
        else:
            base = "GUI"

    setup(  name = appVers.getAppName(),
            version = appVers.getVersion(False),
            description = appVers.getAppDescription(),
            options = {
                "build_exe": build_exe_options
            },
            executables = [Executable(
                script = "ADEditor.py",
                base = base,
                icon = 'Graphx/appIcon.ico',
                copyright = appVers.getCopyright(),
                target_name = f'{appVers.getAppName()}.exe'
                )])
    
    # Create the "architecture" file in the output folder
    with open(os.path.join(build_exe_options['build_exe'], "architecture"), "w") as f:
        f.write(f"ARCHITECTURE = {archi}\n")
        f.write(f"DESCRIPTION = {appVers.getAppDescription()}\n")
        f.write(f"COPYRIGHT = {appVers.getCopyright()}\n")

    # Try to find 7zip command line executable
    # First, search thru the PATH
    sevenZip = shutil.which('7z.exe')
    if sevenZip is None:
        # Try the standard installation folder
        sevenZip = Path(os.environ.get("ProgramFiles")) / '7-Zip' / '7z.exe'
        if not sevenZip.exists():
            sevenZip = None
    
    archName = sName +"_Python-" + pyVersion + '_Win' + archi + ('.7z' if sevenZip is not None else '.zip')

    source_dir = Path(__file__).parent.parent / 'build' / 'ADEditor'

    print(f"Creating archive {archName} from {source_dir}")
    if sevenZip:
        subprocess.run(
                [sevenZip, "a" ,"-t7z", '-mx9', '../' + archName, "."],
                cwd=source_dir,
                check=True
            )
    else:
        with zipfile.ZipFile('build/' + archName, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_dir.rglob('*'):
                    if file_path.is_file():
                        # arcname permet de garder la structure relative sans le dossier parent
                        zipf.write(file_path, arcname=file_path.relative_to(source_dir))
    
    # Now, prepare the package for the "portable" version by creating a minimal settings file
    with open(source_dir / 'settings.xml', 'w') as f:
        f.write("<?xml version='1.0' encoding='UTF-8'?><Settings-file Version='1.0'></Settings-file>")
    
    archName = sName +"_Python-" + pyVersion + '_Win' + archi + '_Portable' + ('.7z' if sevenZip is not None else '.zip')
    print(f"Creating archive {archName} from {source_dir}")
    if sevenZip:
        subprocess.run(
                [sevenZip, "a" ,"-t7z", '-mx9', '../' + archName, "."],
                cwd=source_dir,
                check=True
            )
    else:
        with zipfile.ZipFile('build/' + archName, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_dir.rglob('*'):
                    if file_path.is_file():
                        # arcname permet de garder la structure relative sans le dossier parent
                        zipf.write(file_path, arcname=file_path.relative_to(source_dir))
