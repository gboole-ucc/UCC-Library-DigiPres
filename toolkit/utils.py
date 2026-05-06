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

# allows chice between directories or individual files for input

def resolve_input_files(
    input_dir: str | None = None,
    input_files: list[str] | None = None,
    extensions: list[str] | None = None,
) -> list"""
    Returns a concrete list of files to process, based on either:
    - a directory (walked recursively), or
    - an explicit list of files.

    Exactly one of input_dir or input_files must be provided.
    """

    if input_dir and input_files:
        raise ValueError("Provide either input_dir or input_files, not both")

    if not input_dir and not input_files:
        raise ValueError("Either input_dir or input_files must be provided")

    # Case 1: explicit files
    if input_files:
        files: list[str] = []
        for f in input_files:
            if not os.path.isfile(f):
                raise FileNotFoundError(f"Input file does not exist: {f}")
            if extensions:
                if not f.lower().endswith(tuple(extensions)):
                    continue
            files.append(os.path.abspath(f))
        return files

    # Case 2: directory walk
    return collect_files(
        root_dir=input_dir,
        extensions=extensions,
        ignore_hidden=True,
    )

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
    
