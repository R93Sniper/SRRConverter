import argparse
from . import __version__

from SrrConv.CLI.impls import *

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='subcommand help', required=True)
    
    # Version Command
    version = subparsers.add_parser('version', help='Displays current version information')
    version.set_defaults(func=lambda _args: print("Version: ", __version__))

    # Hash Command
    hash = subparsers.add_parser('hash', help='Calculate the hash for a string')
    hash.add_argument("-s", "--string", help="The string to be hashed.")
    hash.set_defaults(func=hash_impl)

    # Extract command
    extract = subparsers.add_parser('extract', help='Rips a file from a bigfile using a string name')
    extract_subparser = extract.add_subparsers(help='Extract Target', required=True)
    
    # Extract Manifest  
    extract_manifest = extract_subparser.add_parser("manifest", help="Extract all files found in a hash.manifest file")
    extract_manifest.add_argument("-i", "--input", help="Specifies the manifest file to use", required=True)
    extract_manifest.add_argument("-b", "--bigfile", help="Specifies the big file to extract from", required=True)
    extract_manifest.add_argument("-k", "--known-only", action="store_true", help="Extract only filenames found in the manifest")
    extract_manifest.add_argument("-n", "--no-paths", action="store_true", help="Ignore internal subpaths")
    extract_manifest.add_argument("-o", "--outpath", help="The destination folder to write the file(s). Default = current directory", default="./")
    extract_manifest.set_defaults(func=extract_manifest_impl)

    # Extract File
    extract_file = extract_subparser.add_parser("file", help="Extract a single file using a hash or string path")
    extract_file.add_argument(
        "-t", 
        "--type", 
        choices=("hash", "string"), 
        help="Determines if the search parameter is a hash or a string. Default string",
        default="string"
    )
    extract_file.add_argument("-i", "--input",  help="The hash/filename that you wish to extract", required=True)
    extract_file.add_argument("-b", "--bigfile", help="Big file that contains the file", required=True)
    extract_file.add_argument("-n", "--no-paths", action="store_true", help="Ignore internal subpaths")
    extract_file.add_argument("-o", "--outpath", help="The folder to write the file. Default = current directory", default="./")
    extract_file.set_defaults(func=extract_file_impl)

    args = parser.parse_args()
    if "func" in args.__dict__:
        args.func(args)