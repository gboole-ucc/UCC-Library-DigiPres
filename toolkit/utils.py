import os
import json
import pandas as pd

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

def resolve_input_files(
    input_dir: str | None,
    input_files: list[str] | None,
    extensions: list[str] | None = None,
) -> list[str]:
    """
    Resolve a definitive list of files to process.

    Supports:
    - Directory input (-i)
    - Explicit file list (--files)

    Parameters
    ----------
    input_dir : str | None
        Directory path to scan
    input_files : list[str] | None
        Explicit file paths
    extensions : list[str] | None
        Allowed file extensions

    Returns
    -------
    list[str]
        List of valid file paths
    """

    resolved_files: list[str] = []

    # --------------------------------------------------
    # Case 1: explicit files passed (--files)
    # --------------------------------------------------
    if input_files:
        for file_path in input_files:

            # Ensure file exists
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Filter by extension if provided
            if extensions:
                if not file_path.lower().endswith(tuple(extensions)):
                    continue

            resolved_files.append(os.path.abspath(file_path))

        if not resolved_files:
            raise ValueError("No valid input files matched the specified format")

        return resolved_files

    # --------------------------------------------------
    # Case 2: directory input (-i)
    # --------------------------------------------------
    if input_dir:
        if not os.path.isdir(input_dir):
            raise NotADirectoryError(f"Invalid directory: {input_dir}")

        resolved_files = collect_files(
            root_dir=input_dir,
            extensions=extensions,
            ignore_hidden=True
        )

        if not resolved_files:
            raise ValueError("No matching files found in directory")

        return resolved_files

    # --------------------------------------------------
    # No valid input
    # --------------------------------------------------
    raise ValueError("Either input_dir or input_files must be provided")




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
    
# ----------------Format mapping functions----------------

# Base directory for toolkit resources (CSV mappers live here)
TOOLKIT_DIR = os.path.dirname(os.path.abspath(__file__))

def format_details (format_name: str, csv_filename: str) -> list[str] | str:
    '''
    Looks up a logical format name in a format-mapper CSV and returns
    a list of associate fle extensions.
    
    Parameters
    ----------
    format_name : str
        Logical format name (e.g. 'tiff', 'wav', 'pdf')
    csv_filename : str
        Name of the CSV mapper file (e.g. 'image_format_mapper.csv')
    Returns
    -------
    list[str] | str
        List of file extensions (lowercase, including dot), 
        or an empty string if the format is not found.
    '''
    csv_path = os.path.join(TOOLKIT_DIR, csv_filename)

    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Format mapper file not found: {csv_path}") 
    df = pd.read_csv(csv_path, header=0, index_col='format')
    if format_name in df.index:
        return ''
    
    # Drop empty cells and normalise extensions
    extensions = (
        df.loc[format_name]
        .dropna()
        .astype(str)
        .str.lower()
        .tolist()
    )
    
    return extensions

# ----------------Format mapper helpers----------------
# These functions are used to load format mappers and infer logical formats
# these functions not in use yet. needs testing and refinement.

def load_format_mappers(csv_paths: list[str]) -> dict[str, str]:
    '''
    Loads one or more format-mapper CSVs and returns a mapping of
    file extension -> logical format name.

    Parameters
    ----------
    csv_paths : list[str]
        Paths to format mapper CSV files.

    Returns
    -------
    dict[str, str]
        Mapping of extension ('.tif', '.iiq', etc.) to format name.
    '''

    extension_map: dict[str, str] = {}

    for csv_path in csv_paths:
        df = pd.read_csv(csv_path, header=0, index_col='format')

        for format_name, row in df.iterrows():
            extensions = (
                row
                .dropna()
                .astype(str)
                .str.lower()
                .tolist()
            )

            for ext in extensions:
                extension_map[ext] = format_name

    return extension_map


def infer_logical_format(
    csv_path: str,
    extension_map: dict[str, str]
) -> str:
    '''
    Infers the logical format of a metadata CSV using the SourceFile
    field inside the CSV.

    Parameters
    ----------
    csv_path : str
        Path to a metadata CSV file.
    extension_map : dict[str, str]
        Mapping of extension to logical format.

    Returns
    -------
    str
        Logical format name, or 'unknown'.
    '''

    try:
        df = pd.read_csv(csv_path, usecols=['SourceFile'])
    except ValueError:
        return 'unknown'

    if df.empty:
        return 'unknown'

    source_file = str(df.iloc[0]['SourceFile']).lower()
    ext = os.path.splitext(source_file)[1]

    return extension_map.get(ext, 'unknown')

# ----------------OS/system artefact detection----------------
def is_system_artefact(filename: str) -> bool:
    """
    Identify system artefacts (macOS + Windows), case-insensitively.
    """

    name = filename.lower()

    return (
        name.startswith("._") or          # Mac resource forks
        name == ".ds_store" or            # Mac Finder metadata
        name in ("desktop db", "desktop df") or  # classic Mac
        name == "thumbs.db" or            # Windows thumbnails
        name == "autorun.inf"             # Windows autorun 
    )

#----------------OS/system directory filtering----------------

def filter_system_directories(dirs: list[str]) -> list[str]:
    """
    Remove OS/system directories from traversal.

    Parameters
    ----------
    dirs : list[str]
        Directory names from os.walk()

    Returns
    -------
    list[str]
        Filtered list of directories
    """

    excluded_dirs = {
        ".Spotlight-V100",
        ".Trashes",
        ".fseventsd"
    }

    return [d for d in dirs if d not in excluded_dirs]




# ----------------Metadata CSV merge functions----------------
# Merges metadata CSV files by logical format, using format mapper CSVs.
# these functions not in use yet. needs testing and refinement.

def merge_metadata_csvs_by_format(
    csv_files: list[str],
    image_mapper_csv: str,
    other_mapper_csv: str,
    output_dir: str,
) -> dict[str, pd.DataFrame]:
    '''
    Merges metadata CSV files by logical format, using format
    mapper CSVs. IIQ formats are merged using a union-of-columns
    strategy; all other formats are merged safely row-wise.

    Parameters
    ----------
    csv_files : list[str]
        Paths to metadata CSV files.
    image_mapper_csv : str
        Path to image_format_mapper.csv.
    other_mapper_csv : str
        Path to other_format_mapper.csv.
    output_dir : str
        Directory where merged CSVs will be written.

    Returns
    -------
    dict[str, pd.DataFrame]
        Mapping of logical format -> merged DataFrame.
    '''

    os.makedirs(output_dir, exist_ok=True)

    extension_map = load_format_mappers(
        [image_mapper_csv, other_mapper_csv]
    )

    grouped: dict[str, list[str]] = {}

    for csv_file in csv_files:
        logical_format = infer_logical_format(
            csv_file,
            extension_map
        )
        grouped.setdefault(logical_format, []).append(csv_file)

    merged_outputs: dict[str, pd.DataFrame] = {}

    for format_name, files in grouped.items():
        dataframes: list[pd.DataFrame] = []

        for csv_file in files:
            df = pd.read_csv(csv_file)
            df['source_csv'] = os.path.basename(csv_file)
            dataframes.append(df)

        # IIQ requires union-of-columns merging
        if format_name.lower() == 'iiq':
            merged_df = pd.concat(
                dataframes,
                ignore_index=True,
                sort=False
            )
        else:
            merged_df = pd.concat(
                dataframes,
                ignore_index=True
            )

        output_path = os.path.join(
            output_dir,
            f'{format_name}_metadata_merged.csv'
        )

        merged_df.to_csv(output_path, index=False)
        merged_outputs[format_name] = merged_df

    return merged_outputs