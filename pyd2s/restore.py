#!/bin/usr/python3

# standard imports
import glob
import os

# module imports
from pyd2s.decorators import Main
from pyd2s.utilities import get_backups, restore_backup


@Main((['character'], {'help': 'The character to load.'}))
def main(args):
	restore_backup(get_backups(args.character)[-1])
	return 0
