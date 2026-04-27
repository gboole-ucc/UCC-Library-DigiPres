import os
import json

# ----------------Filesystem functions----------------

def collect_files(
        root_dir: str,
        extensions: list[str] | None = None,
        ignore_hidden: bool = True,
    ) -> list[str]:
    '''
    Walks a directory and collects all files with the specified extensions.
    If no extensions are provided, collects all files.
    '''
    files: list[str] = []

    for root, dirs, filenames in os.walk(root_dir):
        if ignore_hidden:
            dirs[:] = [d for d in dirs if not d.startswith('.')]
        for filename in filenames:
            if ignore_hidden and filename.startswith('.'):
                continue
            if extensions:
                if not filename.lower(). endswith(tuple(extensions)):
                    continue
            files.append(os.path.join(root, filename))
    return files

def normalise_path(path: str, base_dir: str) -> str:
    '''
    Returns a normalised path relative to the base directory.
    '''
    rel_path = os.path.relpath(path, base_dir)
    return os.path.normpath(rel_path)

# ----------------I/O functions----------------

def read_json(file_path: str) -> dict | None:
    '''
    Reads a JSON file and returns its contents as a dictionary.
    '''
    try:
        with open(file_path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None

def read_text_file(file_path: str) -> str | None:
    '''
    Reads a text file and returns its contents as a string.
    '''
    try:
        with open(file_path, 'r', encoding='utf-8') as fh:
            return fh.read()
    except OSError:
        return None
    

    # ----------------Metadata functions----------------

    def classify_file(path: str) -> str:
        '''
        Classifies a file based on its extension.        
        Returns one of:
        'content', 'metadata', 'documentation', 'ignore'
        '''



        ext = os.path.splitext(path.lower())[1]
        if ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.wav', '.mov', '.mp4']:
            return 'content'
        if ext in [".xml", ".json", ".csv", ".html"]:
            return 'metadata'
        if ext in [".txt", ".md", ".pdf"]:
            return 'documentation'
        return 'ignore'
    
    def normalise_metadata_keys(metadata: dict) -> dict:
        '''
        Normalises metadata keys to lowercase and replaces spaces with underscores.
        '''
        normalised: dict = {}
        for key, value in metadata.items():
            clean_key = key.strip().lower().replace(' ', '_')
            normalised[clean_key] = value
        return normalised
    