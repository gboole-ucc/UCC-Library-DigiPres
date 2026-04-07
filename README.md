# This repository contains python and shell scripts required for the purpose of digital preservation of unique and distinct collections in UCC Library.


## Pre-requisites

1) Ensure [mediainfo](https://mediaarea.net/en/MediaInfo) and [exiftool](https://exiftool.org/) cli software are installed in your system.
2) Ensure [python 3.x](https://www.python.org/downloads/) is installed in your system.
3) Once python 3.x is installed, perform installation of pandas and pymediainfo packages.
Command to install these packages - 
```bash
pip3 install pandas pymediainfo
```
Note: If "pip3 install <package>" does not work, try "python3 -m pip install <package>".

4) While working on MacOS, ensure homebrew package manager is installed. Check using the following command in the bash command prompt - 
```bash
brew help
```
If the command is not found, perform the installation using the following command ([details](https://brew.sh)) -
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
5) To utilise jhove utility, ensure [java](https://www.oracle.com/ie/java/technologies/downloads/) is installed in your system. Open bash command prompt to check the java version using the following command. 
```bash
java --version
```
Then, perform the required steps available at [jhove](https://jhove.openpreservation.org/getting-started/).

6) To utilise the brunnhilde/ClamAV utility, perform installation of the [siegfried](https://github.com/richardlehane/siegfried?tab=readme-ov-file) module first and then perform the required procedure explained at this [blog](https://www.dpconline.org/blog/blog-niamh-murphy-brunnhilde-installation) by Niamh Murphy. Note that the brunnhilde utility is tried and tested in MacOS only while the siegfried ultility is available for all platforms.

## Python Scripts:

### Points to Note : 
    
1) Open a bash command prompt before you attempt to execute any of the scripts. 
2) Logs for each script executed is stored in Desktop in a folder called "ucclibrary_logs" with the name of the log file indicating the script executed along with a timestamp of execution.
3) Go to the directory where the scripts are stored using the command "cd". Example - 
```bash
cd /home/user/ucc_library
```
4) To display the parameters accepted by a python script, use the following command -
```bash
python3 <script_name>.py -h 
```    
The "-h" stands for help.

### Scripts

### 1) folder_summary.py - 
    
#### Summary
    
The purpose of this script is to summarise the different formats available in a specific directory. The script automatically parses the contents recursively. It summarizes the different file formats present in the directory and it's sub-directories along with return the space occupied by each file format in Megabytes (MB). These details are diplayed both in the command window and the logs.

#### Argument accepted by this script
    
1) -i : Input (Absolute) path of the directory to summarize. 
        (Required Parameter)
        
#### Example command to execute the script in the command window

```bash
python3 folder_summary.py -i "/home/user/directory1"
```

### 2) metadata_extractor.py - 
    
#### Summary
    
The purpose of this script is to extract the technical metadata of selected file format/formats of interest within a given directory and storing the metadata details for each file in a csv file and a txt file (for image formats) or a xml file (for av formats). The individual csv files are merged together to form a master csv file containing the metadata of all the files for each format of interest.  Exiftool is used to extract metadata for image formats and Mediainfo is used to extract technical metadata for av formats. The list of image or av formats supported by the script can be viewed in the "format" column of av_format_mapper.csv and image_format_mapper.csv files. To support additional formats please update these format-mapper csv files. Aditionally, jhove and brunnhilde utilities are optionally available for use within this script. The final files are placed in a new folder beside the input_folder (sidecar) by default but can be modified to store it in a specific destination by providing the output directory argument. Finally, an optional "other supplements" argument is also provided to copy a file or directory from a different source onto the destination.

#### Output
    
For every format of interest, a separate folder is created with the name "<folder_of_interest>_metadata_<format_of_interest>" which is placed right beside the input folder the script will be working on.

Two subdirectories are created inside the output folder named exiftool_csv and exiftool_txt for image formats or mediainfo_csv and mediainfo_pbcore for av format. Correspondingly, individial csv files and txt/xml files are placed for every input file. The master csv file is placed inside the output folder.

#### Notes
    
1) Always run folder_summary.py first to understand the formats present in the input directory of interest and refer to the "format" column (image/av)_format_mapper.csv files and use the exact values in the arguments for this script.
2) Ensure that you manually verify that the jhove and brunnhilde utility is properly installed in your system for use in the script.

#### Arguments accepted by this script
    
1) -i : Input (Absolute) path of the directory to inspect. 
        (Required Parameter)
2) -o : Enter the output directory to place all the required processing outputs. If no value is entered all output files/folders are placed as a sidecar to the input directory.
        (Optional parameter)
3) -img :  Enter the image format/formats to inspect.
4) -av : Enter the av format/formats to inspect.
5) -text : Enter the "other" format/formats to inspect.
6) -jhove : Enter y/n to enable the jhove audit utility to validate and summarize the formats present in the source folder.
            (Optional in command line argument, mandatory user input during execution)
7) -brunnhilde : Enter y/n to enable the brunnhilde/Clam-AV utility to perform and report file format identification along with virus-checking.
            (Optional in command line argument, mandatory user input during execution)
8) -other_sup : Enter any other folder/file from a different source to be copied into the destination.
            (Optional parameter)
    
Either one of -img, -av and -text is mandatory for the script to execute. All three or any two of them could be used together as well. 

#### Example commands to execute the script in the command window :

```bash
python3 metadata_extractor.py -i "/home/user/directory1" -img ".jpeg"
python3 metadata_extractor.py -i "/home/user/directory1" -av ".mp3" -jhove y -brunnhilde y
python3 metadata_extractor.py -i "/home/user/directory1" -img ".jpeg .png" -jhove y
python3 metadata_extractor.py -i "/home/user/directory1" -av ".mp3 .mp4" -brunnhilde y
python3 metadata_extractor.py -i "/home/user/directory1" -img ".jpeg .tiff .png" -text ".pdf" -jhove y -brunnhilde y
```

### 3) ip_creator.py -
    
#### Summary 
    
The purpose of this script is to create a package wherein a specific format of interest (av/image) is copied and stored inside the "objects" folder created inside the output directory - "<destination_directory>/<uid>". An optional argument is used to decide on performing a simple copy of the file or copy the file along with preserving it's original directory structure from the source to the destination. Metadata extraction is done with the help of metadata_extractor.py and stored in the "metadata" folder created in the destination directory. Optionally, supplementary files could be stored in the "supplement" folder. Additonally, jhove and brunnhilde utilities are optionally available for use within this script. Finally, an optional "other supplements" argument is also provided to copy a file or directory from a different source onto the destination's supplement folder.
        
#### Output
1) "output-directory/objects" - Copy of files of a specfic format (av/image) of interest.
2) "output-directory/objects_manifest.md5" - Stores the md5 checksums of all the files in objects.
3) "output-directory/metadata" - contains sub-directories of csv and txt/xml files of metadata generated by metadata_extractor.py functions.
4) "output-directory/supplement" - Optionally present if there are supplements to be saved.
        
#### Notes
    
1) Always run folder_summary.py first to understand the formats present in the input directory of interest and refer to the "format" column (image/av)_format_mapper.csv files and use the exact values in the arguments for this script.
2) Ensure that you manually verify that the jhove and brunnhilde utility is properly installed in your system for use in the script.
        
#### Arguments accepted by this script

1) -i : Input (Absolute) path of the directory to inspect. 
        (Required Parameter)
2) -o : Output (Absolute) path of the directory to create the uid package. 
        (Required Parameter)
3) -uid : uid name to be provided in command-line or dynamically entered by user during code execution. A folder of this name is created in the output path specified by -o.
        (Optional in command line argument, mandatory user input during execution)
4) -format : The file format of interest to be packaged.
        (Required Parameter) 
5) -supplement : Specfic supplementary file formats to be stored.
        (Optional in command line argument, mandatory user input during execution)
6) -kfs : Preserve the input folder structure when copying files to objects directory. Pass on either 'y' for yes or 'n' for no.
        (Optional Parameter)
7) -jhove : Enter y/n to enable the jhove audit utility to validate and summarize the formats present in the source folder.
        (Optional in command line argument, mandatory user input during execution)
8) -brunnhilde : Enter y/n to enable the brunnhilde/Clam-AV utility to perform and report file format identification along with virus-checking.
        (Optional in command line argument, mandatory user input during execution)
9) -other_sup : Enter any other folder/file from a different source to be copied into the destination.
        (Optional Parameter)


#### Example commands to execute the script in the command window

```bash
python3 ip_creator.py -i "/home/user/directory1" -o "/home/user/directory4" -uid "dooa1212" -format ".jpeg" -supplement ".pdf" -kfs y -jhove n -brunnhilde y
python3 ip_creator.py -i "/home/user/directory1" -o "/home/user/directory4" -uid "dooa1212" -format ".tiff" -brunnhilde y -jhove y -supplement ".docx"
python3 ip_creator.py -i "/home/user/directory1" -o "/home/user/directory4" -uid "dooa1212" -format ".jpeg" -supplement ".xlsx .pdf"
python3 ip_creator.py -i "/home/user/directory1" -o "/home/user/directory4" -uid "dooa1212" -format ".jpeg" -supplement ".xlsx .pdf" -other_sup "/home/user/directory1/filA.txt"
python3 ip_creator.py -i "/home/user/directory1" -o "/home/user/directory4" -uid "dooa1212" -format ".jpeg"  -other_sup "/home/user/directory9/filA.txt"
python3 ip_creator.py -i "/home/user/directory1" -o "/home/user/directory4" -uid "dooa1212" -format ".jpeg"  -other_sup "/home/user/directory9/directory2"
```

### 4) search_duplicates.py -
    
#### Summary 
    
The purpose of this script is to search and return a list of duplicates across directories and return the list of the duplicate file paths for each file if it contains a duplicate. 

#### Output 

"/home/user/directory1/file1" : ["/home/user/directory2/file1A", "home/user/directory3/file1"]
"/home/user/directory2/file7" : ["/home/user/directory2/f2/file7", "home/user/directory3/f4/f5/file678"]

#### Arguments accepted by this script

1) -i : Input (Absolute) path(s) of the directory/directories to inspect. 
        (Required Parameter)

#### Example commands to execute the script in the command window

```bash
python3 search_duplicates.py -i "/home/user/directory1" 
python3 search_duplicates.py -i "/home/user/directory1" "/home/user/directory2" "/home/user/directory3"
```

### 5) remove.py -
    
#### Summary 
    
The purpose of this script is to remove specific files formats of interest from a given input directory. The script automatically searches recursively in the given directory and removes the required files. Also, there is an option to remove empty directories if required. 
        
#### Note
    
Always run folder_summary.py first to understand the formats present in the input directory of interest and refer to the "format" column (image/av)_format_mapper.csv files and use the exact values in the arguments for this script.
        
#### Arguments accepted by this script

1) -i : Input (Absolute) path of the directory to inspect. 
        (Required Parameter)
2) -formats : Enter the file formats to be removed from the given directory.
        (Optional Parameter)
3) -ref : Enter if you would like to remove empty directories. Enter y/n (yes/no)
        (Optional Parameter)
Either one of -formats or -ref is mandatory.

#### Example commands to execute the script in the command window

```bash
python3 remove.py -i "/home/user/directory1" -formats ".xlsx" 
python3 remove.py -i "/home/user/directory1" -ref y
python3 remove.py -i "/home/user/directory1" -formats ".jpg" -ref n
```

### 6) pdf2csv.py -
    
#### Summary 
    
The purpose of this script is to extract the description for a specific set of pdfs provided by the ucc library and place them in a csv file for further processing. This script is not intended for general use.

#### Arguments accepted by this script

1) -i : Input (Absolute) path(s) of the directory/directories to inspect. 
        (Required Parameter)
2) -start : Page number of the pdf from which the extraction starts.
        (Required Parameter)
3) -end : Page number of the pdf at the which the extraction ends.
        (Required Parameter)
4) -o : Full path of output directory to place the spreadsheet.
        (Required Parameter)

#### Example commands to execute the script in the command window

```bash
python3 pdf2csv.py -i "/home/user/directory1/abc.pdf" -start 12 -end 35 -o "home/user/directory3"
```

### 7) logger.py -
    
#### Summary
    
This script contains functions necessary to log all the above script runs.


## Bash Scripts: 
### These scripts are designed to be used by external donors or depositors who wish to deliver digital objects to UCC-Library Digital Archive.

#### Points to note
    
1) Open a bash command prompt before you attempt to execute any of the scripts.
2) Logs and Manifests for each script executed are stored in Desktop in a folder called "ucclibrary_logs" and "ucc_moveit_manifests" with the name of the log file indicating the script executed along with a timestamp of execution and name of the manifest file indicating the folder the script worked on.
3) Go to the directory where the scripts are stored using the command "cd". Example - 
```bash
cd "/home/user/ucc_library"
```

### Scripts : 

### 1) manifest.sh -
    
#### Summary
    
The purpose of this bash script is to generate the md5 checksum manifest for each and every file for a given directory and store all the checksum results in a single file. An optional parameter "sidecar" could be passed while calling the script of execution with which the log file and manifest file is stored right beside the directory on which the script will work on. If sidecar isn't passed the logs and checksum file are stored in logs and manifest folder respectively.
        
#### Output
    
"<input-folder>_manifest.md5" file
        
#### Arguments accepted by this script : 
    
1) -s : sidecar argument to store logs and checksum beside the directory the script operates on.
        (Optional)
        
#### Commands to execute the script in the command window :
    
```bash    
bash manifest.sh "/home/user/directory1"
bash manifest.sh "/home/user/directory1" -s
```

### 2) copyfixity.sh -
    
#### Summary
    
The purpose of this script is to copy files from a source directory to a destination while ensuring data integrity through checksum validation. It calculates fixity checksums for each file in both the source and destination directories, compares them, and logs any discrepancies. If a mismatch is detected, it reports the failed files and advises re-copying them. The script generates detailed logs and checksum manifests for future reference, ensuring that all files are copied correctly and remain intact during the transfer.

        
#### Commands to execute the script in the command window :
    
```bash    
bash copyfixity.sh "/home/user/<source-directory>" "/home/user/<destination-directory>"
```

#### Output:
Folder completely copied to destination with fixity manifest file which has checksum details of all the files copied to destination.

## Acknowledgements
manifest.sh and copyfixity.sh are based on two python fixity scripts developed by IFIscripts. 
1. [manifest.py](https://github.com/Irish-Film-Institute/IFIscripts/blob/master/scripts/manifest.py)
2. [copyit.py](https://github.com/Irish-Film-Institute/IFIscripts/blob/master/scripts/copyit.py).

The file manifest created as a sidecar to the digital objects is structured in a way that fixity can 
be validated using the IFIscripts python script [validate.py](https://github.com/Irish-Film-Institute/IFIscripts/blob/master/scripts/validate.py).

## Documented by :
```bash
Abhijeet Rao,
Digital Archive Intern - Summer 2024,
M.Sc. Data Science and Analytics,
UCC 2023-2024
```
