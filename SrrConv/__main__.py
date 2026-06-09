import argparse
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from SrrConv import __version__
from SrrConv.srrconverter import parse_args

if __name__ == "__main__":
    parse_args()