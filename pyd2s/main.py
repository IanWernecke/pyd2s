#!/bin/usr/python3

import glob
import os

from decorators import Main
from utilities import save_dir, get_characters, get_character_files


@Main(
	(['-c', '--char'], {
		'default': None,
		'dest': 'character',
		'help': 'The character to obtain information on.'
	})
)
def main(args):

	characters = get_characters()
	if args.character is not None:
		if args.character not in characters:
			raise Exception('Invalid character: {}'.format(args.character))
		print('# Listing character files for {} ...'.format(args.character))
		for f in get_character_files(args.character):
			print(f)
		return 0

	print(args)

	return 0

