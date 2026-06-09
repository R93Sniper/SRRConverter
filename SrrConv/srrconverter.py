import argparse
from pathlib import Path

from . import __version__
from SrrConv.CLI.impls import *
from SrrConv.CLI.default_properties import _CONFIG_PATH, generate_new_defaults, get_default_property


def parse_args() -> None:
    """Parse command-line arguments and dispatch to the appropriate handler."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="subcommand help", required=True)

    if not _CONFIG_PATH.exists():
        generate_new_defaults()

    # Global Flags
    parser.add_argument(
        "-l",
        "--log-level",
        help="set the logging level. (lower is more verbose) default: Info",
        choices=("none", "error", "warning", "info", "debug")
    )
    log_default = get_default_property("log_file", None)
    parser.add_argument("-w", "--write-log", metavar="<FILE>", action="store", nargs="?", help="write any log output to a file", const=log_default)

    # Version Command
    version_parser = subparsers.add_parser("version", help="displays program version information")
    version_parser.set_defaults(func=lambda _args: print("Version: ", __version__))

    # Defaults Command
    defaults_parser = subparsers.add_parser("defaults", help="view and modify system defaults")
    defaults_subcommands = defaults_parser.add_subparsers()
    list_parser = defaults_subcommands.add_parser("list", help="list the current defaults")
    list_parser.set_defaults(func=list_defaults_impl)

    set_parser = defaults_subcommands.add_parser("set", help="set a default value")
    set_parser.add_argument("default", metavar="<default>", help="determines the default property wanting to be set.")
    set_parser.add_argument("value", metavar="<value>", help="determines the new value to be assigned.")
    set_parser.set_defaults(func=assign_default_impl)

    # Hash Command
    hash_parser = subparsers.add_parser("hash", help="calculate the SR3 hash of a given string")
    hash_parser.add_argument("string", metavar="<string>", help="the string to be hashed.")
    hash_parser.set_defaults(func=hash_impl)

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="extract a single file using a hash or string path")
    extract_subparser = extract_parser.add_subparsers(help="extract Target", required=True)

    # Extract Manifest
    extract_manifest = extract_subparser.add_parser("manifest", help="extracts files listed within a `file_hashes.manifest`.")
    extract_manifest.add_argument("-i", "--input", help="path to the manifest file containing hash/filename pairs.")
    extract_manifest.add_argument("-b", "--bigfile", help="path to the bigfile from which to extract. If unspecified `config.yaml` is used.")
    extract_manifest.add_argument("-k", "--known-only", action="store_true", help="extract only files listed within the manifest file; ignore others.")
    extract_manifest.add_argument("-n", "--no-paths", action="store_true", help="flattens the output directory, preventing subdirectory creation.")
    extract_manifest.add_argument("-a", "--allow-overwrite", action="store_true", help="allow files to be overwritten when extracting")
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
    extract_file.add_argument("input", help="Hash/String of the data to extract from the bigfile")
    extract_file.add_argument("-b", "--bigfile", help="path to the bigfile from which to extract. If unspecified `config.yaml` is used.")
    extract_file.add_argument("-n", "--no-paths", action="store_true", help="flattens the output directory, preventing subdirectory creation.")
    extract_file.add_argument("-a", "--allow-overwrite", action="store_true", help="allow files to be overwritten when extracting")
    extract_file.add_argument("-o", "--outpath", help="specify the output directory where the extracted file will be saved.")
    extract_file.set_defaults(func=extract_file_impl)

    # Convert
    convert_parser = subparsers.add_parser("convert", help="convert a SRM file to FBX")
    convert_subparser = convert_parser.add_subparsers(help="Target Game", required=True)

    srm_parser = convert_subparser.add_parser("srm", help="Convert a SRM file")
    srm_parser.add_argument("input", help="path to the SRM file to be converted.")
    srm_parser.add_argument("-p", "--prevent-cleanup", action="store_true", help="clean up intermediary files used for conversion.", default=False)
    srm_parser.add_argument("-o", "--outpath", help="specify the output path where the FBX file will be saved.")
    srm_parser.add_argument("-a", "--allow-overwrite", action="store_true", help="allow files to be overwritten when extracting")
    srm_parser.add_argument("-g", "--game-dir", choices=("sr1", "sr2"), help="Reference textures relative to a game directory. (must not be used with -t)")
    srm_parser.add_argument("-t", "--texture-dir", help="Reference textures with an absolute directory. (must not be used with -g)")
    srm_parser.add_argument("-i", "--image-format", help="Preferred texture export format.")
    srm_parser.set_defaults(func=convert_file_impl)

    bigfile_parser = convert_subparser.add_parser("bigfile", help="Extract and convert SRM from bigfile")
    bigfile_parser.add_argument("input", help="path to the big file to be converted.")
    bigfile_parser.add_argument("name", help="name of the object to be extracted")
    bigfile_parser.add_argument("-o", "--outpath", help="specify the output path where the FBX file will be saved.")
    bigfile_parser.add_argument("-p", "--prevent-cleanup", action="store_true", help="clean up intermediary files used for conversion.", default=False)
    bigfile_parser.add_argument("-a", "--allow-overwrite", action="store_true", help="allow files to be overwritten when extracting")
    bigfile_parser.add_argument("-t", "--texture-dir", help="use a specified texture directory, instead of big file")
    bigfile_parser.add_argument("-i", "--image-format", help="Preferred texture export format.")
    # bigfile_parser.set_defaults(func=convert_from_bigfile)

    args = parser.parse_args()
    if "func" in args.__dict__:
        args.func(args)