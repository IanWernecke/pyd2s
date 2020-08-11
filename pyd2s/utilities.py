#!/bin/usr/python3

import glob
import os


from io import BytesIO
from zipfile import ZipFile


base_dir = os.path.dirname(os.path.abspath(__file__))
backup_dir = os.path.join(base_dir, 'backup')
save_dir = os.path.expanduser("~/.wine/drive_c/users/default/Saved Games/Diablo II/")


"""

Basic Conversion

"""
def bytes2hexstrs(bs):
	return [int2hexstr(i) for i in bs]


def int2hexbytes(i):
	return str2bytes(int2hexstr(i))


def int2hexstr(i):
	return '{:02x}'.format(i)


def str2bytes(s):
	return s.encode('utf8')


#
# 	functions
#

def bin_diff(before, after):
	"""Dump as much information as possible to find a different between two sets of bytes."""
	if len(before) != len(after):
		print('Different lengths: {} (original), {} (new)'.format(len(before), len(after)))
	print('Before: %s' % ' '.join(bytes2hexstrs(before)))
	print(' After: %s' % ' '.join(bytes2hexstrs(after)))
	bin_diff_comparison(before, after)


def bin_diff_comparison(before, after):
	"""Dump the difference of the binary forms (reversing each byte in the process)."""
	# reverse each byte given in place before diffing the binary string
	before_bs = ''.join('{:08b}'.format(byte)[::-1] for byte in before)
	after_bs = ''.join('{:08b}'.format(byte)[::-1] for byte in after)

	length = len(before_bs)
	first_change = 0
	while before_bs[first_change] == after_bs[first_change]:
		first_change += 1
	last_change = length - 1
	while before_bs[last_change] == after_bs[last_change]:
		last_change -= 1

	print(before_bs)
	print((' ' * (first_change)) + after_bs[first_change:last_change + 1])


def binstring(element, length):

	if isinstance(element, int):

		return '{:0{length}b}'.format(element, length=length).encode()

	elif isinstance(element, bytes):

		return ''.join(
			'{:08b}'.format(i)
			for i in element
		).encode()


def equal(*args):
	return all(args[0] == a for a in args[1:])


def hexdump(*texts):

	assert 0 < len(texts), 'Texts are required for hexdumping.'

	tcount = len(texts)
	for i in range(tcount):
		if isinstance(texts[i], str):
			texts[i] = texts[i].encode('utf8')

	# one text given
	if 1 == len(texts):
		return bytes2hexstrs(texts[0])

	# several texts given
	tlens = [len(t) for t in texts]
	maxlen = max(tlens)
	minlen = min(tlens)
	bios = [BytesIO() for _ in range(tcount + 1)]
	for i in range(maxlen):

		# check the lengths are all greater than i
		# check that the characters are all the same
		# if i <= minlen and equal(*[texts[j][i] for j in range(tcount)]):
		if i < minlen and equal(*[texts[j][i] for j in range(tcount)]):

			bios[0].write(texts[0][i].encode('hex'))
			[b.write('..') for b in bios[1:]]

		else:

			bios[0].write('..')
			for j in range(tcount):
				if i < tlens[j]:
					bios[j + 1].write(texts[j][i].encode('hex'))

		sep = '\n' if 31 == i % 32 else ' '
		[b.write(sep) for b in bios]

	[b.seek(0) for b in bios]
	return tuple(b.read()[:-1] for b in bios)


def create_backup(character):
	if not os.path.isdir(backup_dir):
		os.makedirs(backup_dir)
	zip_file = create_backup_zip_name(character)
	with ZipFile(zip_file, 'w') as zf:
		for fn in get_character_files(character):
			zf.write(fn, os.path.basename(fn))
	return zip_file


def create_backup_zip_name(character):
	i = 0
	fn = os.path.join(backup_dir, '{}-{:04}.zip'.format(character, i))
	while os.path.isfile(fn):
		i += 1
		fn = os.path.join(backup_dir, '{}-{:04}.zip'.format(character, i))
	return fn


def delete_character_files(character):
	for fn in get_character_files(character):
		os.remove(fn)


def get_backups(character):
	"""Return a list of backups for a given character."""
	return sorted(glob.glob(
		os.path.join(backup_dir, '{}-*.zip'.format(character))
	))


def get_characters():
	characters = []
	for filename in os.listdir(save_dir):
		name, ext = os.path.splitext(filename)
		if name not in characters:
			characters.append(name)
	return sorted(characters)


def get_character_files(name):
	return sorted(glob.glob(
		os.path.join(save_dir, '{}.*'.format(name))
	))


def get_character_save_file(name):
	for file_name in get_character_files(name):
		if file_name.endswith('.d2s'):
			return file_name
	return None


def peek(handle, amount):
	"""Read some bytes in front of the cursor in a handle."""
	t = handle.tell()
	data = handle.read(amount)
	handle.seek(t)
	return data


def rbits(element, length):

	if isinstance(element, int):

		return int(binstring(element, length)[::-1], 2)

	elif isinstance(element, bytes):

		# create a binary string where each byte is reversed
		b = binstring(element, len(element))[::-1]

		# create bytes from each section of 8 in the binary string
		return b''.join(
			int(b[i:i+8], 2).to_bytes(1, 'little')
			for i in range(0, len(b), 8)
		)

	else:
		raise Exception('Type not yet implemented: %r' % type(element))


def restore_backup(zip_file):

	# ensure the zip file exists before anything is removed
	ap = os.path.abspath(zip_file)
	assert os.path.isfile(ap), 'File not found: "{}"'.format(ap)

	# get the basename for the zip file,
	# get the character name, and remove the character files
	bn = os.path.basename(ap)
	character = bn.split('-')[0]
	delete_character_files(character)

	# open the zip file for reading
	with ZipFile(zip_file, 'r') as zf:
		for n in zf.namelist():

			# define the output file name and write it to the save directory
			bn = os.path.basename(n)
			with open(os.path.join(save_dir, bn), 'wb') as f:
				f.write(zf.read(n))


def to_binstring(integer, length):
	return '{:0{width}b}'.format(integer, width=length)


def to_rbinstring(integer, length):
	return to_binstring(integer, length)[::-1]
