"""
Store a solved steady state as the warm-start seed.

    python examples/save_warm_start.py examples/OG-ETH-Example/OUTPUT_BASELINE

See ogeth/warm_start.py for why the seed matters.
"""

import os
import sys

from ogcore.utils import safe_read_pickle

from ogeth import warm_start


def main(output_dir):
    ss = safe_read_pickle(os.path.join(output_dir, "SS", "SS_vars.pkl"))
    path = warm_start.save_seed(ss)
    print(f"wrote {path}")


if __name__ == "__main__":
    main(sys.argv[1])
