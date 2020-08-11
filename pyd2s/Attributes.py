# standard imports
import binascii
import os
from io import BytesIO

# module imports
from pyd2s.BitIO import BitIO
from pyd2s.utilities import bytes2hexstrs


class Attributes(dict):

	MAGIC = b'gf'
	MAGIC_LENGTH = 2

	SPECIFICATION = [
		(0, 'strength', 10, None),
		(1, 'energy', 10, None),
		(2, 'dexterity', 10, None),
		(3, 'vitality', 10, None),
		(4, 'stats', 10, None),
		(5, 'skills', 8, None),
		(6, 'life_current', 21, 256),
		(7, 'life_max', 21, 256),
		(8, 'mana_current', 21, 256),
		(9, 'mana_max', 21, 256),
		(10, 'stamina_current', 21, 256),
		(11, 'stamina_max', 21, 256),
		(12, 'level', 7, None),
		(13, 'experience', 32, None),
		(14, 'gold', 25, None),
		(15, 'gold_stash', 25, None)
	]

	def __init__(self, handle):

		start = handle.tell()
		header = handle.read(self.MAGIC_LENGTH)
		assert self.MAGIC == header, 'Invalid Header: {}'.format(header.encode('utf8'))

		# initialize values
		for _, flag_string, _, _ in self.SPECIFICATION:
			self[flag_string] = 0

		self.bitio = BitIO(handle, rread=True, rvalues=True)
		while True:

			flag = self.bitio.read(9, 'bits')
			if flag == 0x1ff:
				break

			for flag_int, flag_string, length, divisor in self.SPECIFICATION:
				if flag != flag_int:
					continue
				value = self.bitio.read(length, 'bits')
				if divisor is not None:
					value /= divisor
				self[flag_string] = value

		end = handle.tell()
		handle.seek(start)
		self.original = handle.read(end - start)
		assert self.original == self.to_bytes()

	def to_bytes(self):

		handle = BytesIO()
		for flag_int, flag_string, bit_length, divisor in self.SPECIFICATION:

			# skip empty values
			if self[flag_string] == 0:
				continue

			handle.write('{:b}'.format(flag_int).rjust(9, '0')[::-1].encode())

			value = self[flag_string]
			if divisor is not None:
				value *= divisor

			handle.write('{:b}'.format(int(value)).rjust(bit_length, '0')[::-1].encode())

		# exit flag
		handle.write(b'1' * 9)

		# pad the ending
		_, remainder = divmod(handle.tell(), 8)
		if remainder != 0:
			handle.write(b'0' * (8 - remainder))
		handle.seek(0)

		bio = BytesIO()
		bio.write(self.MAGIC)

		# write each reversed 'byte' to bio and return the result
		data = handle.read(8)
		while len(data) != 0:
			bio.write(int(data[::-1], 2).to_bytes(1, 'little'))
			data = handle.read(8)
		bio.seek(0)
		return bio.read()
