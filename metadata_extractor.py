import os
import shutil
import argparse
import subprocess
import sys
import time
import pandas as pd
from logger import make_desktop_logs_dir, generate_log, remove_bad_files
import csv
from pymediainfo import MediaInfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Below function provides the list of file formats
# mapped to the file of interest
def format_details(format, file):
    file_path = os.path.join(BASE_DIR, file)
    df = pd.read_csv(file_path, header=0, index_col='format')
    try:
        mapped_formats = list(map(str.strip, df.loc[format, "map_list"].split(",")))
    except: 
        mapped_formats = ""

    return mapped_formats

# Below function parses input arguments from the command line provided by the user.
def arg_parse():

    '''
    Enter the arguments required 
    '''

    parser = argparse.ArgumentParser(
        description="Generates the csv and txt metadata files for each file format in a directory that is \
            requested in formats parameter during each script call. \
            Written by Abhijeet Rao, UCC 2023-2024"
    )

    parser.add_argument('-i', 
                        required=True,
                        type=str, 
                        help="Full path of input directory")
    
    parser.add_argument('-img', 
                        type=str,
                        default="", 
                        help="Enter the image formats you would like to inspect")
    
    parser.add_argument('-av',
                        type=str,
                        default="", 
                        help="Enter the audio/video (av) formats you would like to inspect")
    
    parser.add_argument('-text',
                        type=str,
                        default="", 
                        help="Enter the other formats you would like to inspect")
    
    parser.add_argument('-o',
                        type=str,
                        default="", 
                        help="Enter a specific destination directory to package all the required metadata and reports into it \
                            instead of placing it as a default sidecar to the input directory")
    
    parser.add_argument('-other_sup',
                        type=str,
                        default="", 
                        help="Enter the additional directory/file to be copied from a different source to the destination")
    
    parser.add_argument('-jhove',
                        choices=['y', 'n'],
                        type=str,
                        default='', 
                        help="Enter your choice on using 'jhove' utility IF available")

    parser.add_argument('-brunnhilde',
                        choices=['y', 'n'],
                        type=str,
                        default='', 
                        help="Enter your choice on using 'brunnhilde-ClamAV' utility IF available")

    parsed_args = parser.parse_args()

    return parsed_args

# Below function converts media information of a file to CSV format.
def mediainfo_to_csv(file_path, csv_path):
    media_info = MediaInfo.parse(file_path)
    data = []

    # Collecting the headers
    headers = set()
    for track in media_info.tracks:
        for key in track.to_data().keys():
            headers.add(key)
    
    headers = sorted(headers)
    
    # Add 'file_path' as the first header
    headers = ['file_path'] + headers

    # Collecting the data
    for track in media_info.tracks:
        row = {header: track.to_data().get(header, '') for header in headers[1:]}  # Skip 'file_path' for now
        row['file_path'] = file_path
        data.append(row)

    # Writing to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

# Below function processes image files using exiftool and generates technical metadata files.
def image_exiftool(args, log_name_source):

    input_path = args.i
    img_formats_list = list(args.img.split(" "))

    print(f"Beginning exiftool processing of target {img_formats_list} image formats")
    generate_log(log_name_source, f" Beginning exiftool processing of target {img_formats_list} image formats")

    for format in img_formats_list:
        if hasattr(args, 'dest'):
            destination_directory = os.path.join(args.dest, "metadata")
        else:
            output_path = args.o
            if output_path:
                os.makedirs(output_path, exist_ok=True)
                metadata_fold = os.path.basename(input_path) + "_metadata_" + format[1:]
                destination_directory = os.path.join(output_path, metadata_fold)
            else:
                destination_directory = os.path.join(input_path + "_metadata_" + format[1:])
            
        os.makedirs(destination_directory, exist_ok=True)
        format_detailed_list = format_details(format, r"image_format_mapper.csv")

        csv_path = os.path.join(destination_directory, "exif_csv")
        txt_path = os.path.join(destination_directory, "exif_txt")

        os.makedirs(csv_path, exist_ok=True)
        os.makedirs(txt_path, exist_ok=True)

        print(f'Beginning processing for {format} format')
        generate_log(log_name_source,f' Beginning processing for {format} format')

        remove_bad_files(input_path, log_name_source)

        for root, _, files in os.walk(input_path):
            if files == () or files == []:
                continue
            
            for file in files:
                if str(os.path.splitext(file)[1]).lower() in format_detailed_list:
                    
                    source_file = os.path.join(root, file)
                    dest_file = os.path.basename(root) + "_" + file 
                    exif_csv = os.path.join(csv_path, dest_file)
                    command = f"""\
                    exiftool -csv "{source_file}" > "{exif_csv}.csv"
                    """      
                    subprocess.run(command, shell=True, text=True)

                    exif_txt = os.path.join(txt_path, dest_file)
                    command = f"""\
                    exiftool "{source_file}" > "{exif_txt}.txt"
                    """
                    subprocess.run(command, shell=True, text=True) 
        
        print(f'- csv and txt folders are created successfully for {format} format')
        generate_log(log_name_source, f'- csv and txt folders are created successfully for {format} format')

        try:
            merged_csv = pd.DataFrame()

            for file in os.listdir(csv_path):
                df = pd.read_csv(os.path.join(csv_path, file), header=0)
                merged_csv = pd.concat([merged_csv, df], ignore_index=True)
            
            if hasattr(args, 'dest'):
                csv_file_name = os.path.basename(args.dest) + "_merged.csv"
            else:
                csv_file_name = os.path.basename(input_path) + "_exif_master.csv"

            merged_csv.to_csv(os.path.join(destination_directory, csv_file_name), index=False, encoding='utf-8')
            print(f'Merged csv files into master_csv for {format}')
            generate_log(log_name_source, f' Merged csv files into master_csv for {format}')

        except Exception as e:
            
            print(f'Could not perform the csv files merge operation - \n {e}')
            generate_log(log_name_source, f' Could not perform the csv files merge operation - \n {e}')
            print(f'File causing an error in creating master csv - {file}')
            generate_log(log_name_source, f' File causing an error in creating master csv - {file}')
        
        print(f'Exiting Processing for {format} format')
        generate_log(log_name_source,f' Exiting Processing for {format} format')
    
    print("Exiting exiftool processing of target image formats")
    generate_log(log_name_source, " Exiting exiftool processing of target image formats")
    return

# Below function processes audio/video files using mediainfo and generates technical metadata files.
def av_mediainfo(args, log_name_source):

    input_path = args.i
    av_formats_list = list(args.av.split(" "))

    print(f"Beginning mediainfo processing of target {av_formats_list} av formats")
    generate_log(log_name_source, f" Beginning mediainfo processing of target {av_formats_list} av formats")

    for format in av_formats_list:
        if hasattr(args, 'dest'):
            destination_directory = os.path.join(args.dest, "metadata")
        else:
            output_path = args.o
            if output_path:
                os.makedirs(output_path, exist_ok=True)
                metadata_fold = os.path.basename(input_path) + "_metadata_" + format[1:]
                destination_directory = os.path.join(output_path, metadata_fold)
            else:
                destination_directory = os.path.join(input_path + "_metadata_" + format[1:])
        
        os.makedirs(destination_directory, exist_ok=True)
        format_detailed_list = format_details(format, r"av_format_mapper.csv")

        csv_path = os.path.join(destination_directory, "mediainfo_csv")
        xml_path = os.path.join(destination_directory, "mediainfo_pbcore")

        os.makedirs(csv_path, exist_ok=True)
        os.makedirs(xml_path, exist_ok=True)

        print(f'Beginning processing for {format} format')
        generate_log(log_name_source,f' Beginning processing for {format} format')

        for root, _, files in os.walk(input_path):
            if files == () or files == []:
                continue

            for file in files:
                if str(os.path.splitext(file)[1]).lower() in format_detailed_list:
                    
                    source_file = os.path.join(root, file)
                    dest_file = os.path.basename(root) + "_" + file 
                    exif_csv = os.path.join(csv_path, dest_file) + "_mediainfo.csv"
                    mediainfo_to_csv(source_file, exif_csv)
                    # command = f"""\
                    # mediainfo -f "{source_file}" > "{exif_csv}_mediainfo.csv"
                    # """      
                    # subprocess.run(command, shell=True, text=True)

                    exif_txt = os.path.join(xml_path, dest_file)
                    command = f"""\
                    mediainfo -f "{source_file}" --Output=PBCore2 > "{exif_txt}_mediainfo.xml"
                    """
                    subprocess.run(command, shell=True, text=True) 
        
        print(f'- csv and xml folders are created successfully for {format} format')
        generate_log(log_name_source, f'- csv and xml folders are created successfully for {format} format')

        try:
            merged_csv = pd.DataFrame()

            for file in os.listdir(csv_path):
                df = pd.read_csv(os.path.join(csv_path, file), header=0)
                merged_csv = pd.concat([merged_csv, df], ignore_index=True)
            
            if hasattr(args, 'dest'):
                csv_file_name = os.path.basename(args.dest) + "_merged.csv"
            else:
                csv_file_name = os.path.basename(input_path) + "_mediainfo_master.csv"
            
            merged_csv.to_csv(os.path.join(destination_directory, csv_file_name), index=False, encoding='utf-8')
            print(f'Merged csv files into master_csv for {format} format')
            generate_log(log_name_source, f' Merged csv files into master_csv for {format} format')

        except Exception as e:
            
            print(f'Could not perform the csv files merge operation - \n {e}')
            generate_log(log_name_source, f' Could not perform the csv files merge operation - \n {e}')
            print(f'File causing an error in creating master csv - {file}')
            generate_log(log_name_source, f' File causing an error in creating master csv - {file}')
    
        print(f'Exiting Processing for {format} format')
        generate_log(log_name_source,f' Exiting Processing for {format} format')
    
    print("Exiting Mediainfo processing of target audio/video formats")
    generate_log(log_name_source, " Exiting Mediainfo processing of target audio/video formats")
    return

def others_exiftool(args, log_name_source):

    input_path = args.i
    txt_formats_list = list(args.text.split(" "))

    print(f"Beginning exiftool processing of target {txt_formats_list} text formats")
    generate_log(log_name_source, f" Beginning exiftool processing of target {txt_formats_list} text formats")

    for format in txt_formats_list:
        if hasattr(args, 'dest'):
            destination_directory = os.path.join(args.dest, "metadata")
        else:
            output_path = args.o
            if output_path:
                os.makedirs(output_path, exist_ok=True)
                metadata_fold = os.path.basename(input_path) + "_metadata_" + format[1:]
                destination_directory = os.path.join(output_path, metadata_fold)
            else:
                destination_directory = os.path.join(input_path + "_metadata_" + format[1:])
            
        os.makedirs(destination_directory, exist_ok=True)
        format_detailed_list = format_details(format, r"other_format_mapper.csv")

        csv_path = os.path.join(destination_directory, "exif_csv")
        txt_path = os.path.join(destination_directory, "exif_txt")

        os.makedirs(csv_path, exist_ok=True)
        os.makedirs(txt_path, exist_ok=True)

        print(f'Beginning processing for {format} format')
        generate_log(log_name_source,f' Beginning processing for {format} format')

        remove_bad_files(input_path, log_name_source)

        for root, _, files in os.walk(input_path):
            if files == () or files == []:
                continue
            
            for file in files:
                if str(os.path.splitext(file)[1]).lower() in format_detailed_list:
                    
                    source_file = os.path.join(root, file)
                    dest_file = os.path.basename(root) + "_" + file 
                    exif_csv = os.path.join(csv_path, dest_file)
                    command = f"""\
                    exiftool -csv "{source_file}" > "{exif_csv}.csv"
                    """      
                    subprocess.run(command, shell=True, text=True)

                    exif_txt = os.path.join(txt_path, dest_file)
                    command = f"""\
                    exiftool "{source_file}" > "{exif_txt}.txt"
                    """
                    subprocess.run(command, shell=True, text=True) 
        
        print(f'- csv and txt folders are created successfully for {format} format')
        generate_log(log_name_source, f'- csv and txt folders are created successfully for {format} format')

        try:
            merged_csv = pd.DataFrame()

            for file in os.listdir(csv_path):
                df = pd.read_csv(os.path.join(csv_path, file), header=0)
                merged_csv = pd.concat([merged_csv, df], ignore_index=True)
            
            if hasattr(args, 'dest'):
                csv_file_name = os.path.basename(args.dest) + "_merged.csv"
            else:
                csv_file_name = os.path.basename(input_path) + "_exif_master.csv"

            merged_csv.to_csv(os.path.join(destination_directory, csv_file_name), index=False, encoding='utf-8')
            print(f'Merged csv files into master_csv for {format}')
            generate_log(log_name_source, f' Merged csv files into master_csv for {format}')

        except Exception as e:
            
            print(f'Could not perform the csv files merge operation - \n {e}')
            generate_log(log_name_source, f' Could not perform the csv files merge operation - \n {e}')
            print(f'File causing an error in creating master csv - {file}')
            generate_log(log_name_source, f' File causing an error in creating master csv - {file}')
        
        print(f'Exiting Processing for {format} format')
        generate_log(log_name_source,f' Exiting Processing for {format} format')
    
    print("Exiting exiftool processing of target text formats")
    generate_log(log_name_source, " Exiting exiftool processing of target text formats")
    return

# Below function triggers jhove auditing process for all the files stored
# in the "objects" folder and stores the results in the "metadata" folder.
def jhove_audit(args, log_name_source):
    
    input_path = args.i
    output_path = args.o

    print(' - JHOVE available/enabled - Beginning auditing')
    generate_log(log_name_source, ' - JHOVE available/enabled - Beginning auditing')

    if args.o:
        jhove_xml_file = os.path.join(output_path, os.path.basename(input_path) + "_jhove_audit.xml")
    else:
        jhove_xml_file = input_path + "_jhove_audit.xml"
    
    command = f"""\
    {os.path.expanduser("~/")}jhove/jhove -h Audit -o "{jhove_xml_file}" "{input_path}"
    """
    subprocess.run(command, shell=True, text=True)

    print(' - JHOVE available/enabled - auditing process completed')
    generate_log(log_name_source, ' - JHOVE available/enabled - auditing process completed')
    return

# Below function performs the brunnhilde/ClamAv virus scanning of the "objects" folder
# content and stores the results in the "metadata" folder.
def brunnhilde_scan(args, log_name_source):

    input_path = args.i
    output_path = args.o
    base_folder = os.path.basename(input_path)

    print(' - Brunnhilde-ClamAV scan available/enabled - Beginning scanning')
    generate_log(log_name_source, ' - Brunnhilde-ClamAV scan available/enabled - Beginning scanning')

    if args.o:
        brunnhilde_output_folder = os.path.join(output_path, base_folder + "_brunnhilde")
    else:
        brunnhilde_output_folder = input_path + "_brunnhilde"
    
    command = f"""\
    brunnhilde.py "{input_path}" "{brunnhilde_output_folder}"
    """
    print(command)
    subprocess.run(command, shell=True, text=True)


    os.rename(os.path.join(brunnhilde_output_folder, "report.html"), \
              os.path.join(brunnhilde_output_folder, base_folder+"_report.html"))
    
    os.rename(os.path.join(brunnhilde_output_folder, "siegfried.csv"), \
              os.path.join(brunnhilde_output_folder, base_folder+"_siegfried.csv"))
    
    os.rename(os.path.join(os.path.join(brunnhilde_output_folder, "logs"), "viruscheck-log.txt"), \
              os.path.join(os.path.join(brunnhilde_output_folder, "logs"), base_folder+"_viruscheck-log.txt"))
    
    print(' - brunnhilde-ClamAV available/enabled - scanning process completed')
    generate_log(log_name_source, ' - brunnhilde-ClamAV available/enabled - scanning process completed')

# Main function that controls the flow of the script.
def main():
    args = arg_parse()
    input_path = args.i
    log_name_source_ = "metadata_extractor_"  + str(os.path.basename(input_path)) + time.strftime("_%Y_%m_%dT%H_%M_%S") + ".log"
    desktop_logs_dir = make_desktop_logs_dir()
    log_name_source = os.path.join(desktop_logs_dir, log_name_source_)
    

    if not os.path.isdir(input_path):
            print(' - Input must be a directory/folder - exiting!')
            generate_log(log_name_source, ' - Input must be a directory/folder - exiting!')
            sys.exit()
    
    if args.img == "" and args.av == "" and args.text == "":
            print(' - At least one format must be provided as input')
            generate_log(log_name_source, ' - At least once format must be provided as input')
            sys.exit()    
    
    if args.jhove == "":
        q = input("Would you like to generate a jhove audit report? (Ensure jhove installed in this system. \
                  Provide y/n as your input)")
        if q.lower() == 'y':
            args.jhove = 'y'
            generate_log(log_name_source, f"Enabling jhove audit report")
        else:
            args.jhove = 'n'
            generate_log(log_name_source, "Ignoring jhove auditing")

    if args.brunnhilde == "":
        q = input("Would you like to generate a siegfried-brunnhilde virus report? (Ensure \
                  brunnhilde/clamAV installed in this system. Recommended OS for using this feature is MacOS.\
                  Provide y/n as your input) ")
        if q.lower() == 'y':
            args.brunnhilde = 'y'
            generate_log(log_name_source, f"Enabling jhove audit report")
        else:
            args.brunnhilde = 'n'
            generate_log(log_name_source, "Ignoring jhove auditing")
    
    if args.img:
        image_exiftool(args, log_name_source)
    
    if args.av:
        av_mediainfo(args, log_name_source)
    
    if args.text:
        others_exiftool(args, log_name_source)

    if args.o:
        output_path = args.o
    else:
        output_path = os.path.dirname(input_path)
    
    other = args.other_sup
    if other:
        print("Other folder/directory is entered for copying into the destination")
        generate_log(log_name_source, "Other folder/directory is entered for copying into the destination")
        if os.path.exists(other):
            if os.path.isfile(other):
                print("The other path is a valid file at source. Copying to destination ...")
                generate_log(log_name_source, "The other path is a valid file at source. Copying to destination ...")
                shutil.copy2(other, output_path)
                print("Other file copied to destination successfully")
                generate_log(log_name_source, "Other file copied to destination successfully")
            elif os.path.isdir(other):
                print("The other path is a valid directory. Copying its contents recursively to destination ...")
                generate_log(log_name_source, "The other path is a valid directory. Copying its contents recursively to destination ...")
                shutil.copytree(other, os.path.join(output_path, os.path.basename(other)), dirs_exist_ok=True)
                print("Other directory copied to destination successfully")
                generate_log(log_name_source, "Other directory copied to destination successfully")
        else:
            print("Enter a valid directory or file to copied in the destination")
            generate_log(log_name_source, "Enter a valid directory or file to copied in the destination - Exiting")
    
    if args.jhove == 'y' and args.img:
        img_formats_list = list(args.img.split(" "))
        for f in img_formats_list:
            if f in ['.jpeg','.tiff','.jpeg2000']:
                jhove_audit(args, log_name_source)
                break
    
    if args.brunnhilde == 'y':
        brunnhilde_scan(args, log_name_source)
    
    
# Below code marks the start of execution of the program.
if __name__ == "__main__":
    main()