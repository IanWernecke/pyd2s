#!/bin/usr/python3

# standard imports
import glob
import os

# module imports
from pyd2s.decorators import Main
from pyd2s.utilities import create_backup, get_characters, get_character_files


@Main(
	(['character'], dict(default='ALL', help='The character to backup.'))
)
def main(args):
	characters = get_characters()
	if args.character == 'ALL':
		for character in characters:
			create_backup(character)
	else:
		assert args.character in characters, 'Character not found: "{}"'.format(args.character)
		create_backup(args.character)
	return 0
