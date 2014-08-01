# Author: Eric Kow
# License: CeCILL-B (French BSD3-like)

"""
remove scratch dirs, evals with no scores
"""

from __future__ import print_function
from os import path as fp
import os
import shutil

from attelo.harness.util import call, force_symlink, subdirs

from ..local import\
    TRAINING_CORPORA, LOCAL_TMP
from ..util import\
    current_tmp, latest_tmp

NAME = 'clean'


def config_argparser(parser):
    """
    Subcommand flags.

    You should create and pass in the subparser to which the flags
    are to be added.
    """
    parser.set_defaults(func=main)


def main(_):
    """
    Subcommand main.

    You shouldn't need to call this yourself if you're using
    `config_argparser`
    """
    for data_dir in sorted(subdirs(LOCAL_TMP)):
        if fp.basename(data_dir) == "latest":
            continue
        for subdir in subdirs(data_dir):
            bname = fp.basename(subdir)
            if bname in ["eval-current", "scratch-current"]:
                os.unlink(subdir)
            elif bname.startswith("scratch-"):
                shutil.rmtree(subdir)
            elif bname.startswith("eval-"):
                if not any(f.startswith("scores-") for
                           f in os.listdir(subdir)):
                    shutil.rmtree(subdir)
