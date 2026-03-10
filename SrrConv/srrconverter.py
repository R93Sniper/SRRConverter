import argparse
from . import __version__

from SrrConv.CLI.impls import *

from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='subcommand help', required=True)

    if not Path("./config.defaults").exists():
        generate_new_defaults()

    # Global Flags
    parser.add_argument(
        "-l", 
        "--log-level", 
        help="set the logging level. (lower is more verbose) default: Info", 
        choices=("none", "error", "warning", "info", "debug"), 
        default="info"
    )
    log_default = get_default_property("log_file", None)
    parser.add_argument("-w", "--write-log", metavar="<FILE>", action="store", nargs="?", help="write any log output to a file", const=log_default)
    
    # Version Command
    version = subparsers.add_parser('version', help='displays program version information')
    version.set_defaults(func=lambda _args: print("Version: ", __version__))
    
    # Defaults Command
    defaults = subparsers.add_parser('defaults', help='view and modify system defaults')
    defaults_subcommands = defaults.add_subparsers()
    list = defaults_subcommands.add_parser('list', help='list the current defaults')
    list.set_defaults(func=list_defaults_impl)

    set = defaults_subcommands.add_parser('set', help='set a default value')
    set.add_argument("default", metavar="<default>", help="determines the default property wanting to be set.")
    set.add_argument("value", metavar="<value>", help="determines the new value to be assigned.")
    set.set_defaults(func=assign_default_impl)

    # Hash Command
    hash = subparsers.add_parser('hash', help='calculate the SR3 hash of a given string')
    hash.add_argument("string", metavar='<string>', help="the string to be hashed.")
    hash.set_defaults(func=hash_impl)

    # Extract command
    extract = subparsers.add_parser('extract', help='extract a single file using a hash or string path')
    extract_subparser = extract.add_subparsers(help='extract Target', required=True)
    
    # Extract Manifest  
    extract_manifest = extract_subparser.add_parser("manifest", help="extracts all files listed within a `hash.manifest` file.")
    extract_manifest.add_argument("-i", "--input", help="path to the manifest file containing filenames.")
    extract_manifest.add_argument("-b", "--bigfile", help="path to the bigfile from which to extract. If unspecified `config.defaults` is used.")
    extract_manifest.add_argument("-k", "--known-only", action="store_true", help="extract only files listed within the manifest file; ignore others.")
    extract_manifest.add_argument("-n", "--no-paths", action="store_true", help="flattens the output directory, preventing subdirectory creation.")
    extract_manifest.add_argument("-o", "--outpath", help="specify the output directory where the extracted file will be saved. default: ./")
    extract_manifest.set_defaults(func=extract_manifest_impl)

    # Extract File
    extract_file = extract_subparser.add_parser("file", help="extract a single file using a hash or string path")
    extract_file.add_argument(
        "-t", 
        "--type", 
        choices=("hash", "string"), 
        help="specify whether `input` is a hash or a string. default: string",
        default="string"
    )
    extract_file.add_argument("input", help="Hash/String of the data  to extract from the bigfile")
    extract_file.add_argument("-b", "--bigfile", help="path to the bigfile from which to extract. If unspecified `config.defaults` is used.")
    extract_file.add_argument("-n", "--no-paths", action="store_true", help="flattens the output directory, preventing subdirectory creation.")
    extract_file.add_argument("-o", "--outpath", help="specify the output directory where the extracted file will be saved. default: ./", default="./")
    extract_file.set_defaults(func=extract_file_impl)

    args = parser.parse_args()
    if "func" in args.__dict__:
        args.func(args)