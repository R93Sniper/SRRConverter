# SRRConverter

Python toolchain to convert game assets from Legacy of Kain: Soul Reaver 1 & 2 Remastered and Legacy of Kain: Defiance Remastered into FBX.

This repository contains no game files, only tooling to convert them.

---

## Features

- Extract files from 64bit BigFile archives used in Defaince Remastered
- Convert SRM model files (Gen1: SR1/2 Remastered, Gen2: Defiance Remastered) to FBX
- Convert DDS textures to common image formats via Pillow
- Calculate SR3 hashes (CRC-32 variant used by the game engine)

---

## Requirements

### Python 3.10

### pip packages

```
pillow>=11.3.0       # texture conversion (required)
pyyaml>=6.0.2        # config file management (required)
colorama>=0.4.6      # colorized terminal output (optional)
```

### External SDK

- **Autodesk FBX Python SDK** -- required for FBX export. Available from the Autodesk developer portal (not on PyPI). Without it, all commands except `convert srm` and `convert bigfile` will function normally.

---

## Installation

1. Clone or download this repository.
2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
3. (Optional) Download and install the Autodesk FBX Python SDK for FBX export.
4. Run `python SrrConv/__main__.py version` to verify the installation.
5. Run `python SrrConv/__main__.py defaults list` to view default paths. Configure game install directories with `defaults set`.

The config file `config.yaml` is auto-generated on first run. If upgrading from an older version, the legacy `config.defaults` (pickle) file is automatically migrated.

---

## Usage

### Entry points

| Command                                       | Purpose                                               |
| -----------------------------------------------| -------------------------------------------------------|
| `python SrrConv/__main__.py <command> [args]` | CLI (preferred, works from any directory)             |
| `python -m SrrConv <command> [args]`          | Module invocation (requires project root on sys.path) |
| `SrrConv.bat`                                 | Windows shortcut for `python -m SrrConv %*`           |

### Global flags

Available on all subcommands:

| Flag | Description |
|---|---|
| `-l, --log-level <LEVEL>` | Log level: `none`, `error`, `warning`, `info`, `debug` (default: `info`) |
| `-w, --write-log [<FILE>]` | Write log output to a file (default: `./output.log`) |

### Subcommands

#### `version`

Display the program version.

#### `defaults`

View and modify persistent configuration stored in `config.yaml`.

| Command | Description |
|---|---|
| `defaults list` | List all current default values |
| `defaults set <key> <value>` | Set a default property |

Available properties:

| Key | Default | Description |
|---|---|---|
| `hash_manifest` | `./file_hashes.manifest` | Path to the hash/filename manifest |
| `log_file` | `./output.log` | Default log file path |
| `out_path` | `./` | Default output directory |
| `image_format` | `dds` | Default texture export format |
| `sr_directory` | Steam path for Soul Reaver 1-2 Remastered | Game install directory |
| `def_directory` | Steam path for Defiance Remastered | Game install directory |
| `log_level` | `info` | Default logging level |

Set game directories if not using default Steam paths:
```
python SrrConv/__main__.py defaults set sr_directory /path/to/Soul\ Reaver\ I-II
python SrrConv/__main__.py defaults set def_directory /path/to/Defiance\ Remastered
```

#### `hash`

Calculate the SR3 hash of a string (CRC-32 variant with polynomial `0x4C11DB7`).

```
python SrrConv/__main__.hash "some/file/path.drm"
```

#### `extract`

Extract files from BigFile archives.

| Command                                 | Description                                  |
| -----------------------------------------| ----------------------------------------------|
| `extract file [-t hash/string] <input>` | Extract a single file by hash or string path |
| `extract manifest`                      | Extract files listed in a manifest file      |

Flags:

| Flag                     | Description                                                                                                          |
| --------------------------| ----------------------------------------------------------------------------------------------------------------------|
| `-i, --input <PATH>`     | Path to the manifest or input identifier                                                                             |
| `-b, --bigfile <PATH>`   | Path to the BigFile (default from config)                                                                            |
| `-n, --no-paths`         | Flatten output directory (no subdirectories)                                                                         |
| `-a, --allow-overwrite`  | Allow overwriting existing files                                                                                     |
| `-o, --outpath <DIR>`    | Output directory (default: `./`)                                                                                     |
| `-t, --type hash/string` | Input type for `extract file`                                                                                        |
| `-k, --known-only`       | For `extract manifest`: only extract files listed in the manifest (default behavior uses hash for unknown filenames) |

Extract a single file by hash:
```
python SrrConv/__main__.py extract file -t hash 0x12345678
```

Extract a single file by path:
```
python SrrConv/__main__.py extract file -t string "tex_hd/feral_m_1_d.dds"
```

Extract all files from a BigFile, using the manifest for naming:
```
python SrrConv/__main__.py extract manifest
```

Extract only files present in the manifest:
```
python SrrConv/__main__.py extract manifest --known-only
```

#### `convert`

Convert SRM model files to FBX.

| Command | Description |
|---|---|
| `convert srm <input>` | Convert a single SRM file |
| `convert bigfile <input> <name>` | Extract and convert an SRM from a BigFile |

Flags:

| Flag                       | Description                                 |
| ----------------------------| ---------------------------------------------|
| `-o, --outpath <FILE>`     | Output FBX path                             |
| `-a, --allow-overwrite`    | Allow overwrite                             |
| `-p, --prevent-cleanup`    | Keep intermediary files                     |
| `-t, --texture-dir <DIR>`  | Absolute texture directory                  |
| `-g, --game-dir sr1/sr2`   | Use game-relative texture path              |
| `-i, --image-format <FMT>` | Texture export format (default from config) |

Convert an SRM file:
```
python SrrConv/__main__.py convert srm model.srm
```

SRM version is auto-detected: byte `[3]` = `1` for Gen1 (SR1/2 Remastered), `8` for Gen2 (Defiance Remastered).

---

## Manifest files

The manifest files (`file_hashes.manifest`, `hash_classic.manifest`) list precalculated SR3 hashes and their corresponding filenames, one per line in tab-separated format:

```
0x0004887e      tex_hd/feral_m_1_d.dds
0x000497b4      pcenglish/strong1_4.raw
```

- `hash.manifest` -- Soul Reaver 1 & 2 Remastered file listing
- `hash_classic.manifest` -- Classic game file listing

(This list is incomplete, if you wish to contribute to the research please feel free)


---

## License

GPLv3 See `LICENSE` for details.
