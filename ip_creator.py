#!/usr/bin/env python3
import os
import sys
import argparse
import time
import re
import shutil
import hashlib
import subprocess
from logger import generate_log, make_desktop_logs_dir, remove_bad_files
from metadata_extractor import format_details, image_exiftool, av_mediainfo, others_exiftool

# Empty class to create custom objects. Useful to modify argument lists.
class Arguments():
    pass

# Below function parses input arguments from the command line provided by the user.
def arg_parse():

    '''
    Enter the arguments required 
    '''

    parser = argparse.ArgumentParser(
        description="this script is an information package creator. It packages all files belonging to a specific format of interest into a folder \
            and creates manifests for the packaged file. Additonally, metadata is extracted and stored in csv and txt files for reference. Optionally, \
            supplementary files could be stored as well. Written by, Abhijeet Rao, UCC 2023-2024"
    )

    parser.add_argument('-i', 
                        required=True,
                        type=str, 
                        help="Full path of input directory")
    
    parser.add_argument('-format',
                        required=True, 
                        type=str,
                        default="", 
                        help="Enter the format you would like to package")
    
    parser.add_argument('-uid', 
                        type=str,
                        default="", 
                        help="Enter the destination uid name you would like to assign")
    
    parser.add_argument('-o',
                        type=str,
                        required=True,
                        default="", 
                        help="Full path of output directory to place the uid package")

    parser.add_argument('-supplement',
                        type=str,
                        default="", 
                        help="Enter the supplementary formats you would like to preserve")
    
    parser.add_argument('-kfs',
                        choices=['y', 'n'],
                        required=True,
                        type=str,
                        default='n', 
                        help="(KFS - Keep folder structure) : Enter your choice on preserving directory structure for the objects in the destination")
    
    parser.add_argument('-jhove',
                        choices=['y', 'n'],
                        type=str,
                        default='', 
                        help="Enter your choice on using 'jhove' utility IF available")

    parser.add_argument('--no-brunnhilde',
                        dest='brunnhilde',
                        action='store_false', 
                        help='Do not run Brunnhilde (enabled by default)')
    
    # Set Brunnhilde to run as default explicitly
    parser.set_defaults(brunnhilde=True)
    ''
    # --noclam flag: disables ClamAV when running Brunnhilde
    parser.add_argument('--noclam',
                        action='store_true',
                        help='Disable ClamAV when running Brunnhilde (enabled by default)')
    '' 

    parser.add_argument('-other_sup',
                        type=str,
                        default='', 
                        help="Enter the additional directory/file to be copied from a different source to the destination")
    
    parsed_args = parser.parse_args()

    return parsed_args

# Logic used to determine the manifest checksum for a single file.
# Function taken from ififuncs.py from IFIscripts repository: https://github.com/Irish-Film-Institute/IFIscripts/blob/master/scripts/ififuncs.py
def hashlib_md5(filename):
    '''
    uses hashlib to return an MD5 checksum of an input filename
    '''
    read_size = 0
    last_percent_done = 0
    m = hashlib.md5()
    total_size = os.path.getsize(filename)
    with open(str(filename), 'rb') as f:
        while True:
            buf = f.read(2**20)
            if not buf:
                break
            read_size += len(buf)
            m.update(buf)
            percent_done = 100 * read_size / total_size
            if percent_done > last_percent_done:
                sys.stdout.write('[%d%%]\r' % percent_done)
                sys.stdout.flush()
                last_percent_done = percent_done
    md5_output = m.hexdigest()
    return md5_output

# Below function is used to copy files of interest into the "objects"
# folder while storing supplement files if required, in the "supplement"
# folder.
def objects_and_supplements_ip(args, log_name_source):
    
    input_path = args.i
    file_formats = args.format_list
    supplement_formats = args.supplement
    output_path = os.path.join(args.o, args.uid)
    objects_folder = args.objects_folder
    supplement_folder = args.supplement_folder
    manifest = os.path.join(output_path, "objects_manifest.md5")

    for root, _, files in os.walk(input_path):
        if files == () or files == []:
            continue

        for file in files:
            file_format = (os.path.splitext(file)[1]).lower()
            if file_format in file_formats:
                file_src = os.path.join(root, file)
                hash_source = str(hashlib_md5(file_src))

                
                if args.kfs == 'n':
                    shutil.copy2(file_src, objects_folder)

                    new_file_name = os.path.basename(root) + "_" + file
                    file_dest = os.path.join(objects_folder, new_file_name)
                    os.rename(os.path.join(objects_folder, file), file_dest)

                else:
                    relative_path = os.path.relpath(root, os.path.dirname(input_path))
                    dest_dir = os.path.join(objects_folder, relative_path)
                    
                    # Ensure the destination directory exists
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    # Copy the file to the new destination preserving the directory structure
                    new_file_name = file
                    file_dest = os.path.join(dest_dir, new_file_name)
                    shutil.copy2(file_src, file_dest)

                hash_dest = str(hashlib_md5(file_dest))

                if hash_source != hash_dest:
                    print(f"- File {file} not copied properly, integrity compromised. Exiting ip_creator.py")
                    generate_log(log_name_source, f'- File {file} not copied properly, integrity compromised. Exiting ip_creator.py')
                    shutil.rmtree(output_path)
                    sys.exit()
                
                print(f"{file} copied to destination correctly")
                generate_log(log_name_source, f"{file} copied to destination correctly")

                with open(manifest, 'a', encoding='utf-8') as f:
                    rel_path = os.path.relpath(file_dest, output_path)
                    f.write(hash_dest + "  " + str(rel_path))
                    f.write("\n")
            
            elif supplement_formats!=[] and file_format in supplement_formats:
                file_src = os.path.join(root, file)

                shutil.copy2(file_src, supplement_folder)

                new_file_name = os.path.basename(root) + "_" + file
                file_dest = os.path.join(supplement_folder, new_file_name)
                os.rename(os.path.join(supplement_folder, file), file_dest)
            
    print(f"Manifest file ready for {args.format} files at {manifest}")
    generate_log(log_name_source, f"Manifest file ready for {args.format} files at {manifest}")
    print(f"Finished processing object and supplementary files for {args.format} files")
    generate_log(log_name_source, f"Finished processing object and supplementary files for {args.format} files")
    return

# Below function checks if the user entered "uid" names adheres to 
# a specfic condition.
def uid_pattern_check(uid):
    uid_pattern = re.compile(pattern=r"[a-z]{4}\d{4}")
    m = uid_pattern.fullmatch(uid)
    while m is None: #or len(m.group()) != 7:
        print("\nWrong format followed - Enter the uid which follows the below rule")
        print("Name format - 4 lowercase alphabets followed by 4 digits (Example : 'doaa4321')")
        uid = input("Please input an uid which follows the above rule: ")
        m = uid_pattern.fullmatch(uid)

    return uid

# Below function triggers jhove auditing process for all the files stored
# in the "objects" folder and stores the results in the "metadata" folder.
def jhove_audit(args, log_name_source):
    
    print(' - JHOVE available/enabled - Beginning auditing')
    generate_log(log_name_source, ' - JHOVE available/enabled - Beginning auditing')

    jhove_xml_file = os.path.join(args.metadata_folder, args.uid+"_jhove_audit.xml")
    command = f"""\
    {os.path.expanduser("~/")}jhove/jhove -h Audit -o "{jhove_xml_file}" "{args.objects_folder}"
    """
    print(command)
    subprocess.run(command, shell=True, text=True)

    print(' - JHOVE available/enabled - auditing process completed')
    generate_log(log_name_source, ' - JHOVE available/enabled - auditing process completed')
    return

# Below function performs the brunnhilde/ClamAv virus scanning of the "objects" folder
# content and stores the results in the "metadata" folder.
def brunnhilde_scan(args, log_name_source):
          
    # print status of Brunnhilde's process on terminal
    if args.noclam:
        msg = ' - Brunnhilde scan beginning (ClamAV disabled via --noclam)'
    else:
        msg = ' - Brunnhilde scan beginning (ClamAV enabled)'
    print(msg)
    generate_log(log_name_source, msg)

    # Define the Brunnhilde output directory first  
    brunnhilde_output_folder = os.path.join(
        args.metadata_folder,
        args.uid+"_brunnhilde"
        )
    
    # Base Brunnhilde command
    command = [
        "brunnhilde.py",
        args.objects_folder,
        brunnhilde_output_folder,
    ]

    # Remove Brunnhilde output directory if it already exists to allow a re-run
    if os.path.exists(brunnhilde_output_folder):
        shutil.rmtree(brunnhilde_output_folder)

    # If --noclam was requested, pass it through to Brunnhilde
    if args.noclam:
        command.append("--noclam")

    # Execute Brunnhilde
 
    print(command)
    subprocess.run(command, text=True)


    os.rename(os.path.join(brunnhilde_output_folder, "report.html"), \
              os.path.join(brunnhilde_output_folder, args.uid+"_report.html"))
    
    os.rename(os.path.join(brunnhilde_output_folder, "siegfried.csv"), \
              os.path.join(brunnhilde_output_folder, args.uid+"_siegfried.csv"))
    
    # Rename ClamAV log only if it exists (i.e. ClamAV was run)
    virus_log = os.path.join(
        brunnhilde_output_folder, "logs", "viruscheck-log.txt"
    )
    
    if os.path.exists(virus_log):
        os.rename(
            virus_log, 
            os.path.join(
                brunnhilde_output_folder,
                "logs",
                args.uid+"_viruscheck-log.txt"
            )
        )
    else:
        generate_log(
            log_name_source,
            "Brunnhilde ran with --noclam option, so no viruscheck log generated"
            )
    




# Below function is the main logic to setup all the required folders for 
# "information package" creation. It also ensures all required arguments
# are entered properly by the user.
def main():
    args = arg_parse()
    input_path = args.i
    log_name_source_ = "ip_creator_"  + str(os.path.basename(input_path)) + time.strftime("_%Y_%m_%dT%H_%M_%S") + ".log"
    desktop_logs_dir = make_desktop_logs_dir()
    log_name_source = os.path.join(desktop_logs_dir, log_name_source_)
    
    if not os.path.isdir(input_path):
        print(' - Input must be a directory/folder - exiting!')
        generate_log(log_name_source, ' - Input must be a directory/folder - exiting!')
        sys.exit()

    remove_bad_files(input_path, log_name_source)
    
    if args.uid == "":
        uid = input('Please enter the uid name to be created (Do not enter an empty string): ')
        uid = uid_pattern_check(uid)
    else:
        uid = uid_pattern_check(args.uid)
    
    args.uid = uid
    output_path_ = args.o
    os.makedirs(output_path_, exist_ok= True)
    output_path = os.path.join(output_path_, uid)

    if os.path.exists(output_path):
        q = input(f"Warning - {output_path} path already exists, do you want to continue with package creation with this uid? (y/n): ")
        generate_log(log_name_source, f"Warning - {output_path} path already exists, do you want to continue with package creation with this uid? (y/n)")
        generate_log(log_name_source, str(q))
        if q.lower() != 'y':
            print("ip_creator.py - Process Exiting")
            generate_log(log_name_source, "ip_creator.py - Process Exiting")
            sys.exit()
    
    if args.supplement == "":
        q = input("Would you like to preserve supplementary files of specific formats? (y/n): ")
        if q.lower() == 'y':
            supplement = input('Enter supplements list: ')
            generate_log(log_name_source, f"Supplementary formats to be preserved - {supplement}")
            supplement = list(map(str, supplement.strip().split(" ")))
        else:
            supplement = []
            print("No supplmentary formats to be preserved")
            generate_log(log_name_source, "No supplmentary formats to be preserved")
    else:
        supplement = args.supplement
        generate_log(log_name_source, f"Supplementary formats to be preserved - {supplement}")

    if args.jhove == "":
        q = input("Would you like to generate a jhove audit report? (Ensure jhove installed in this system. \
                  Provide y/n as your input)")
        if q.lower() == 'y':
            args.jhove = 'y'
            generate_log(log_name_source, f"Enabling jhove audit report")
        else:
            args.jhove = 'n'
            generate_log(log_name_source, "Ignoring jhove auditing")

    

    args_object = Arguments()

    # format = args.format
    # ret = format_details(format, "image_format_mapper.csv")
    # if ret == "":
    #     ret = format_details(format, "av_format_mapper.csv")
    #     if ret == "":
    #         generate_log(log_name_source, "Enter a proper av or image format to package")
    #         print("Enter a proper image or av format to package")
    #         sys.exit()
    #     else:
    #         args_object.av = format
    #         args.format_list = ret
    #         metadata = av_mediainfo
    # else:
    #     args_object.img = format
    #     args.format_list = ret
    #     metadata = image_exiftool

    format = args.format
    if format_details(format, "image_format_mapper.csv") != "":
        args_object.img = format
        args.format_list = format_details(format, "image_format_mapper.csv")
        metadata = image_exiftool
    elif format_details(format, "av_format_mapper.csv") != "":
        args_object.av = format
        args.format_list = format_details(format, "av_format_mapper.csv")
        metadata = av_mediainfo
    elif format_details(format, "other_format_mapper.csv") != "":
        args_object.text = format
        args.format_list = format_details(format, "other_format_mapper.csv")
        metadata = others_exiftool
    else:
        generate_log(log_name_source, "Enter a proper av/image/text format to package")
        print("Enter a proper image/av/text format to package")
        sys.exit()


    args_object.i = input_path
    args_object.dest = output_path
    
    os.makedirs(output_path, exist_ok=True)

    objects_folder = os.path.join(output_path, "objects")
    args.objects_folder = objects_folder
    os.makedirs(objects_folder, exist_ok=True)

    metadata_folder = os.path.join(output_path, "metadata")
    args.metadata_folder = metadata_folder
    os.makedirs(metadata_folder, exist_ok=True)

    supplement_folder = os.path.join(output_path, "supplement")
    args.supplement_folder = supplement_folder
    
    os.makedirs(supplement_folder, exist_ok=True)
    
    # Creating required objects structure of the information package creation
    objects_and_supplements_ip(args, log_name_source)

    # Calling appropriate metadata extractor function
    metadata(args_object, log_name_source)

    other = args.other_sup
    if other:
        print("Other folder/directory is entered for copying into the destination")
        generate_log(log_name_source, "Other folder/directory is entered for copying into the destination")
        if os.path.exists(other):
            if os.path.isfile(other):
                print("The other path is a valid file at source. Copying to destination ...")
                generate_log(log_name_source, "The other path is a valid file at source. Copying to destination ...")
                shutil.copy2(other, supplement_folder)
                print("Other file copied to destination successfully")
                generate_log(log_name_source, "Other file copied to destination successfully")
            elif os.path.isdir(other):
                print("The other path is a valid directory. Copying its contents recursively to destination ...")
                generate_log(log_name_source, "The other path is a valid directory. Copying its contents recursively to destination ...")
                shutil.copytree(other, os.path.join(supplement_folder, os.path.basename(other)), dirs_exist_ok=True)
                print("Other directory copied to destination successfully")
                generate_log(log_name_source, "Other directory copied to destination successfully")
        else:
            print("Enter a valid directory or file to copied in the destination")
            generate_log(log_name_source, "Enter a valid directory or file to copied in the destination - Exiting")
    
    if args.jhove == 'y' and args.format in ['.tiff', '.jpeg', '.jpeg2000', '.pdf']:
        jhove_audit(args, log_name_source)
    
    if args.brunnhilde:
        brunnhilde_scan(args, log_name_source)

    # final brunnhilde nd clamAV status message
    if not args.brunnhilde:
        msg = (
            "- Process completed. Brunnhilde was disabled. "
            " ClamAV scan was not performed."
        )
    elif args.noclam:
        msg = (
            "- Process completed. Brunnhilde was enabled."
            " ClamAV scan was not performed."
        )
    else:
        msg = (
            "- Process completed. Brunnhilde was enabled."
            " ClamAV scan was performed."
        )
    print(msg)
    generate_log(log_name_source, msg)
    

    if os.path.exists(supplement_folder):
        if len(os.listdir(supplement_folder)) == 0:
            os.removedirs(supplement_folder)
    
    return

# Below code marks the start of execution of the program.
if __name__ == "__main__":
    main()

    
