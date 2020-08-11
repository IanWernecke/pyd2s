# standard imports
import binascii
import logging
import numpy
import os
import struct

from io import BytesIO


# module imports
from pyd2s.Attributes import Attributes
from pyd2s.BitIO import BitIO
from pyd2s.Items import Items
from pyd2s.constants import CLASS_STRINGS
from pyd2s.utilities import get_character_files, bytes2hexstrs, get_character_save_file, peek


#
# 	checksum functions
#


def create_checksum(binary_data, offset=12):
    """
	Given binary data (bytes), create a crc and inject it into the bytes,
	returning the bytes with a fixed checksum.
	"""

    def checksum(data, start_value=0):
        acc = numpy.int32(start_value)
        for value in data:
            acc = numpy.int32((acc << 1) + value + (acc < 0))
        return numpy.int32(acc)

    # old: data = numpy.fromstring(binary_data, dtype=numpy.uint8)
    data = numpy.frombuffer(binary_data, dtype=numpy.uint8)
    checksum_byte_length = numpy.dtype("int32").itemsize
    pre_data, post_data = data[:offset], data[offset + checksum_byte_length :]

    # generate checksums
    pre_checksum = checksum(pre_data, start_value=0)
    on_checksum = checksum(numpy.zeros(checksum_byte_length, dtype=numpy.uint8), start_value=pre_checksum)
    post_checksum = checksum(post_data, start_value=on_checksum)

    return post_checksum


def create_checksum_bytes(binary_data, offset=12):
    return struct.pack("<i", create_checksum(binary_data, offset))


def patch_checksum(binary_data):
    checksum_bytes = create_checksum_bytes(binary_data)
    return binary_data[:12] + checksum_bytes + binary_data[16:]


class Game(object):

    MAGIC = b"\x55\xaa\x55\xaa"
    MERCENARY_MAGIC = b"jf"
    GOLEM_MAGIC = b"kf"

    def __init__(self, character=None):

        self.character = character
        self.file_path = None if character is None else get_character_save_file(character)
        self.original_binary = None

        self.merc_id = 0
        self.merc_items = Items()

        # the remaining, unknown part of the save file
        self.has_golem_suffix = False
        self.has_golem = 0
        self.end = None

    def __enter__(self):
        assert self.file_path is not None, f"Cannot load unknown file path for character: {self.character}"
        self.from_file(self.file_path)
        return self

    def __exit__(self, exc_type=None, exc_value=None, exc_traceback=None):
        if exc_type is None:
            self.to_file(self.file_path)

    def from_file(self, path=None):
        if path is None:
            path = self.file_path
        assert path is not None, "A file path was not given and this object has no file_path."
        with open(path, "rb") as f:
            self.from_bytes(f.read())

    def from_bytes(self, binary):

        self.original_binary = binary
        bio = BytesIO(binary)

        magic = bio.read(4)
        assert self.MAGIC == magic, 'Invalid Magic: "{}"'.format(magic.hex())

        # 4 byte file version, 4 byte file size, 4 byte checksum, 4 byte active weapon
        self.file_version, self.file_size, self.file_checksum, self.active_weapon = struct.unpack("<IIII", bio.read(16))

        # 16 byte name filled with null characters, 1 byte status, 1 byte progression
        name = bio.read(16)
        self.char_name = name[: name.find(b"\x00")]
        self.char_status = bio.read(1)
        self.char_progression = bio.read(1)
        # logging.debug('Character name: %s', self.char_name)
        # char_status bits:
        # 	7: ?
        # 	6: ladder
        # 	5: expansion
        # 	4: ?
        # 	3: died (present when a character has died at least once)
        # 	2: hardcore
        # 	1: ?
        # 	0: ?
        # logging.debug('Character status: %s', self.char_status)
        # char_progress value: (classic: standard, hardcore) -- (expansion: standard, hardcore)
        # 	0-3: -
        # 	4-7: sir/dame, count/countess -- slayer, destroyer
        # 	8-11: lord/lady, duke/duchess -- champion, conqueror
        # 	12: baron/baroness, king/queen -- guardian
        # logging.debug('Character progression: %s', self.char_progression)

        # 2 unk bytes, 1 byte class, 2 unk bytes (b'\x10\x1e'), 1 byte clvl
        # logging.debug('Unknown: %s', bio.read(2))
        bio.read(2)
        self.char_class = struct.unpack("<b", bio.read(1))[0]
        # logging.debug('Unknown: %s', bio.read(2))
        bio.read(2)

        # this attribute is only used for display when on the character loading screen
        # alter experience to change levels
        self.char_level = struct.unpack("<b", bio.read(1))[0]

        # 4 unk bytes (\x00), last_played, 4 unk bytes (\xff)
        # _, self.last_played, _ = struct.unpack('<III', bio.read(12))
        # logging.debug('Unknown: %s', bio.read(4))
        bio.read(4)
        self.last_played = struct.unpack("<I", bio.read(4))[0]
        # logging.debug('Unknown: %s', bio.read(4))
        bio.read(4)

        # 64 bytes assigned skills
        self.assigned_skills = bio.read(64)

        # 16 bytes button skills
        self.lmb_skill, self.rmb_skill, self.lmb_skill_swp, self.rmb_skill_swp = struct.unpack("<IIII", bio.read(16))

        # 32 bytes appearance, 3 bytes difficulty, 4 bytes map id, 2 unknown
        self.char_menu_appearance = bio.read(32)
        self.difficulty = bio.read(3)
        self.map_id = struct.unpack("<I", bio.read(4))[0]
        # logging.debug('Unknown: %s', bio.read(2))
        bio.read(2)

        # mercenary: 2 bytes dead, 4 id, 2 bytes name, 2 bytes type, 4 bytes experience
        self.merc_dead, self.merc_id, self.merc_name_id, self.merc_type, self.merc_exp = struct.unpack(
            "<HIHHI", bio.read(14)
        )

        # 144 bytes (\x00), 298 bytes (self.quests), 81 bytes (self.waypoints), 51 bytes (npc intros)
        # logging.debug('Unknown: %s', bio.read(144))
        bio.read(144)
        self.quests = bio.read(298)
        self.waypoints = bio.read(81)
        self.npc_intros = bio.read(51)

        # HEADER COMPLETE

        self.attributes = Attributes(handle=bio)
        self.char_skills = bio.read(32)
        self.items = Items(bio)
        self.corpse = Items(bio)

        # if this character is an expansion character, they might also have a mercenary
        magic = bio.read(2)
        while magic:

            if magic == self.MERCENARY_MAGIC:
                if self.merc_id:
                    self.merc_items = Items(bio)
            elif magic == self.GOLEM_MAGIC:
                self.has_golem_suffix = True
                self.has_golem = bio.read(1)

            magic = bio.read(2)

        self.end = bio.read()
        if self.end:
            print("END:")
            print(self.end)

    def to_file(self, path=None):

        # get the path to write to
        if path is None:
            path = self.file_path
        assert path is not None, "A path was not given and this object has no file_path."

        # convert this object to bytes and write it out to a file
        data = self.to_bytes()
        with open(path, "wb") as f:
            f.write(data)
        return len(data)

    def to_bytes(self):

        bio = BytesIO()
        bio.write(self.MAGIC)

        # version, size, checksum
        bio.write(struct.pack("<IIII", self.file_version, self.file_size, 0, self.active_weapon))

        # 16 byte character name
        bio.write(self.char_name)
        bio.write(b"\x00" * (16 - len(self.char_name)))

        # character status and progression
        bio.write(self.char_status)
        bio.write(self.char_progression)

        # 2 unk bytes, 1 byte class, 2 unk bytes (b'\x10\x1e'), 1 byte clvl
        bio.write(struct.pack("<hbhb", 0, self.char_class, 7696, self.char_level))

        # 4 unk bytes (\x00), last_played, 4 unk bytes (\xff)
        bio.write(struct.pack("<III", 0, self.last_played, 0xFFFFFFFF))

        # 64 bytes assigned skills
        bio.write(self.assigned_skills)

        # 16 bytes button skills
        bio.write(struct.pack("<IIII", self.lmb_skill, self.rmb_skill, self.lmb_skill_swp, self.rmb_skill_swp))

        # 32 bytes appearance, 3 bytes difficulty, 4 bytes map id, 2 unknown
        bio.write(self.char_menu_appearance)
        bio.write(self.difficulty)
        bio.write(struct.pack("<IH", self.map_id, 0))

        # mercenary: 2 bytes dead, 4 id, 2 bytes name, 2 bytes type, 4 bytes experience
        bio.write(struct.pack("<HIHHI", self.merc_dead, self.merc_id, self.merc_name_id, self.merc_type, self.merc_exp))

        # 144 bytes (\x00), 298 bytes (self.quests), 81 bytes (self.waypoints), 51 bytes (npc intros)
        bio.write(b"\x00" * 144)
        bio.write(self.quests)
        bio.write(self.waypoints)
        bio.write(self.npc_intros)

        bio.write(self.attributes.to_bytes())
        bio.write(self.char_skills)
        bio.write(self.items.to_bytes())
        bio.write(self.corpse.to_bytes())

        bio.write(self.MERCENARY_MAGIC)
        if self.merc_id:
            bio.write(self.merc_items.to_bytes())

        if self.has_golem_suffix:
            bio.write(self.GOLEM_MAGIC)
            bio.write(self.has_golem)

        # any remaining, mysterious bytes
        bio.write(self.end)

        # patch the file size parameter
        length = bio.tell()
        bio.seek(8)
        bio.write(struct.pack("<I", length))
        bio.seek(0)

        # patch the checksum and return
        return patch_checksum(bio.read())

    def reset_akara(self):
        """Reset the character's ability to reset their skills and stats (normal difficulty)."""
        # under testing, byte index 92 in the quests turned from value '2' to value '1' after resetting
        # the byte in question could be a set of flags, so we should only change the two bits of the 93rd byte
        # (normal == byte index 92, nightmare == byte index 188, hell == byte index 284)
        for byte_index in (92, 188, 284):

            byte = self.quests[byte_index]

            # if there is no value there, do nothing
            # (perhaps this could cause an issue with setting a quest flag for a future difficulty?)
            if not byte:
                continue

            # set the 7th bit
            if not byte & 0x2:
                byte ^= 0x2

            # unset the 8th bit
            if byte & 0x1:
                byte ^= 0x1

            self.quests = self.quests[:byte_index] + byte.to_bytes(1, "little") + self.quests[byte_index + 1 :]

    def reset_hephaesto(self):
        """Reset the Hephaesto/Soulstone quest."""
        # warning: untested
        # this is currently only for hell
        for byte_index in (256,):

            first_byte = self.quests[byte_index]
            second_byte = self.quests[byte_index + 1]

            # if there is not value, do nothing (trying to prevent any issue with future difficulties/acts/quests)
            if not first_byte:
                continue

            # set the 5th bit of the first byte (unknown effect)
            if not first_byte & 0x8:
                first_byte ^= 0x8

            # unset the 3rd and 4th bit of the second byte (unknown effect)
            if second_byte & 0x20:
                second_byte ^= 0x20
            if second_byte & 0x10:
                second_byte ^= 0x10

            self.quests = (
                self.quests[:byte_index]
                + first_byte.to_bytes(1, "little")
                + second_byte.to_bytes(1, "little")
                + self.quests[byte_index + 2 :]
            )
