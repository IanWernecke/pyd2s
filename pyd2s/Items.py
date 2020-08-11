# standard imports
import logging
import struct
from copy import deepcopy
from io import BytesIO

# installed imports
import colored
from colored import stylize

# module imports
from pyd2s.BitIO import BitIO
from pyd2s.MagicalProperties import MagicalProperties, MagicalProperty
from pyd2s.constants import *
from pyd2s.utilities import bin_diff, bytes2hexstrs


# def create_item(code=None, type_string=None, defense=None, durability=None, sockets=None):
#
# 	assert (code is not None) or (type_string is not None), 'Code of type name required.'
# 	if code is None:
# 		code = get_code(type_string)
#
# 	item = Item()
# 	item.set_code(code)
#
# 	if item.type_id & (TYPE_ARMOR | TYPE_SHIELD):
# 		assert defense is not None, 'Defense required for item: {}'.format(item.type_string)
# 		item.defense = defense
#
# 	if item.type_id & (TYPE_ARMOR | TYPE_SHIELD | TYPE_WEAPON):
# 		assert durability is not None, 'Durability required for item: {}'.format(item.type_string)
# 		item.durability_max = item.durability_current = durability
#
# 	if sockets is not None:
# 		item.sockets = sockets
#
# 	return item


class Item(object):

    MAGIC = b"\x4a\x4d"

    def __init__(self, handle=None):

        self.original_binary = None

        # basic information
        self.autoequip = 0
        self.autofill = False
        self.ear = False
        self.ethereal = False
        self.identified = False
        self.personalized = False
        self.quest_item = False
        self.runeword = False
        self.simple = False
        self.socketed = False
        self.starter = False
        self.unknown = 0

        # socket information
        self.sockets = []
        self.sockets_filled = 0

        # location information
        self.parent = ITEM_STORED
        self.equipped = 0
        self.x, self.y = 0, 0
        self.stored = STORED_INVENTORY

        # item information
        self.code = None
        self.type_id = 0
        self.type_string = None

        # complex information
        self.name, self.id = None, None
        self.level, self.quality = 1, 1
        self.multipic, self.pic_id = False, 0
        self.class_specific, self.class_info = False, 0
        self.unusual_bit = 0

        # basic informations
        self.quality_info, self.tome_info = None, None
        self.name_id_first, self.name_id_last = None, None
        self.magical_name_ids = []
        self.magical_name_prefixes = []
        self.magical_name_suffixes = []

        self.personalized_name = None
        self.defense = None
        self.durability_max = None
        self.durability_current = None

        self.quantity = None
        self.magical_props = None
        self.set_props = None
        self.runeword_props = None
        self.runeword_id = None
        self.runeword_name = None
        # set_list_value
        # self.magical_props, self.set_props, self.runeword_props

        # load data into self if a handle was given
        if handle is not None:
            self.from_handle(handle)

    def __str__(self):

        parts = []
        start = ""
        if self.name is not None:
            # parts.append(self.name)
            parts.append(self.color_name)
            start += "  "

        parts.append(f"{start}{self.type_string} ({QUALITY_STRINGS[self.quality]})")
        start += "  "

        if self.starter:
            parts.append(f"{start}*Starter")

        if self.simple:
            parts.append(f"{start}*Simple")

        if self.equipped:
            parts.append(f"{start}Equipped: {EQUIPPED_LOCATIONS[self.equipped]}")
        else:
            parts.append(f"{start}Location: {self.parent}, Column: {self.x}, Row: {self.y}, Stored: {self.stored}")

        if self.defense is not None:
            parts.append(f"{start}Defense: {self.defense}")

        if self.durability_max is not None and 0 < self.durability_max:
            parts.append(f"{start}Durability: {self.durability_current}/{self.durability_max}")

        if self.magical_props:
            parts.append(f"{start}Magical Properties:")
            for prop in self.magical_props:
                parts.append(f"{start}  {prop}")

        if self.set_props:
            parts.append(f"{start}Set Properties:")
            for prop in self.set_props:
                parts.append(f"{start}  {prop}")

        if self.runeword:
            parts.append(f"{start}Runeword Properties:")
            for prop in self.runeword_props:
                parts.append(f"{start}  {prop}")

        if self.socketed:
            parts.append(f"{start}Sockets: {len(self.sockets)-self.sockets.count(None)}/{len(self.sockets)}")
            for socket in self.sockets:
                if socket is None:
                    continue
                parts.append(f"Socketed: {socket}")

        return "\n".join(parts)

    #
    # 	convenience properties
    #

    @property
    def color_name(self):
        # if the item is a rune, the color is independent of the quality
        if self.is_rune:
            return stylize(self.name, colored.fg("orange_red_1"))

        # name = f"{self.personalized_name}'s {self.name}" if self.personalized else self.name

        # return the color of the name, based upon the quality
        return stylize(
            self.name,
            colored.fg(
                {
                    QUALITY_CRAFTED: "orange_red_1",
                    QUALITY_UNIQUE: "dark_khaki",  # wheat_1 == too pale/yellow
                    QUALITY_RARE: "light_yellow",
                    QUALITY_SET: "light_green",
                    QUALITY_MAGIC: "dodger_blue_1",  # 'blue_1' == too dark, 'blue_3b' == too dark
                }.get(self.quality, "white")
            ),
        )

    @property
    def equipped_location(self):
        return EQUIPPED_LOCATIONS[self.equipped]

    @property
    def is_amulet(self):
        return self.type_string == "Amulet"

    @property
    def is_armor(self):
        return bool(self.type_id & TYPE_ARMOR)

    @property
    def is_crafted_quality(self):
        return self.quality == QUALITY_CRAFTED

    @property
    def is_gem(self):
        return self.code in GEM_CODES

    @property
    def is_low_quality(self):
        return self.quality == QUALITY_LOW

    @property
    def is_high_quality(self):
        return self.quality == QUALITY_HIGH

    @property
    def is_magic_quality(self):
        return self.quality == QUALITY_MAGIC

    @property
    def is_rare_quality(self):
        return self.quality == QUALITY_RARE

    @property
    def is_ring(self):
        return self.type_string == "Ring"

    @property
    def is_rune(self):
        return self.code in RUNE_CODES

    @property
    def is_set_quality(self):
        return self.quality == QUALITY_SET

    @property
    def is_shield(self):
        return bool(self.type_id & TYPE_SHIELD)

    @property
    def is_unique_quality(self):
        return self.quality == QUALITY_UNIQUE

    @property
    def is_weapon(self):
        return bool(self.type_id & TYPE_WEAPON)

    @property
    def has_defense(self):
        return self.type_id & (TYPE_ARMOR | TYPE_SHIELD)

    @property
    def has_durability(self):
        return self.type_id & (TYPE_ARMOR | TYPE_SHIELD | TYPE_WEAPON)

    @property
    def has_quantity(self):
        return has_quantity(self.code)

    @property
    def quality_string(self):
        return QUALITY_STRINGS[self.quality]

    @property
    def pretty_name(self):
        return f"{self.color_name} ({self.quality_string} {self.type_string})"

    #
    # 	functions
    #

    def from_handle(self, handle):

        # ensure an item is expected
        start = handle.tell()
        magic = handle.read(2)
        assert b"\x4a\x4d" == magic, "Invalid magic: %s" % magic

        # read information from the handle
        bitio = BitIO(handle, rread=True, rvalues=True)

        # 0 bits along
        self.quest_item = bool(bitio.read(1, "bit"))
        bitio.read(3, "bits")
        self.identified = bool(bitio.read(1, "bit"))
        bitio.read(5, "bits")

        # sometimes potions have this bit set when another potion will fill this spot upon use
        self.autofill = bitio.read(1, "bit")

        self.socketed = bool(bitio.read(1, "bit"))
        bitio.read(1, "bit")
        self.new = bool(bitio.read(1, "bit"))
        self.autoequip = bitio.read(2, "bits")  # this is probably 2, smaller bitflags
        self.ear = bool(bitio.read(1, "bit"))
        self.starter = bool(bitio.read(1, "bit"))

        bitio.read(3, "bits")
        # print('Unknown: %d' % bitio.read(3, 'bits'))

        self.simple = bool(bitio.read(1, "bit"))
        self.ethereal = bool(bitio.read(1, "bit"))

        bitio.read(1, "bit")
        # logging.debug('Weird code: %d', bitio.read(1, 'bit'))

        self.personalized = bool(bitio.read(1, "bit"))

        bitio.read(1, "bit")
        # print('WEIRD: %d' % bitio.read(1, 'bit'))

        self.runeword = bool(bitio.read(1, "bit"))

        # TODO: result 3233 was found on an amazon, equipped
        # quiver with 238 arrows, normal otherwise
        self.unknown = bitio.read(15, "bits")  # 3232

        self.parent = bitio.read(3, "bits")
        self.equipped = bitio.read(4, "bits")  # this should be zero if the parent is not 'ITEM_EQUIPPED'
        self.x = bitio.read(4, "bits")
        self.y = bitio.read(3, "bits")
        bitio.read(1, "bit")
        self.stored = bitio.read(3, "bits")

        self.set_code(bitio.read(4, "chars")[:-1].decode())

        # this sets a default "name" for the object (name is custom defined, for our use)
        self.name = self.type_string

        # this has to be stored, as some items will set 1 without having
        self.sockets_filled = bitio.read(3, "bits")

        if self.simple:
            if bitio.remaining:
                bitio.read(bitio.remaining, "bits")

            # test handle match
            end = handle.tell()
            handle.seek(start)
            self.original_binary = handle.read(end - start)
            result = self.to_bytes()
            if self.original_binary != result:
                print("[RECREATION_FAILURE]")
                print(self.name)
                bin_diff(self.original_binary, result)

            return self.original_binary == result

        # read complex information
        self.id = bitio.read(32, "bits")
        self.level = bitio.read(7, "bits")
        self.quality = bitio.read(4, "bits")

        self.multipic = bool(bitio.read(1, "bit"))
        if self.multipic:
            self.pic_id = bitio.read(3, "bits")

        self.class_specific = bool(bitio.read(1, "bit"))
        if self.class_specific:
            self.class_info = bitio.read(11, "bits")

        # TODO
        if self.ear:
            pass

        # quality switch
        if self.is_low_quality or self.is_high_quality:
            self.quality_info = bitio.read(3, "bits")

        elif self.is_magic_quality:
            self.name_id_first = bitio.read(11, "bits")
            self.name_id_last = bitio.read(11, "bits")
            self.name = ""
            if 0 < self.name_id_first:
                self.name += MAGIC_PREFIX_STRINGS[self.name_id_first] + " "
            self.name += self.type_string
            if 0 < self.name_id_last:
                self.name += " of " + MAGIC_SUFFIX_STRINGS[self.name_id_last]

        elif self.is_set_quality:
            self.name_id_first = bitio.read(12, "bits")
            self.name = SET_STRINGS[self.name_id_first]

        elif self.is_crafted_quality or self.is_rare_quality:
            self.name_id_first = bitio.read(8, "bits")
            self.name_id_last = bitio.read(8, "bits")
            self.name = RARE_NAMES[self.name_id_first] + " " + RARE_NAMES[self.name_id_last]

            for _ in range(3):
                if bool(bitio.read(1, "bit")):
                    self.magical_name_prefixes.append(bitio.read(11, "bits"))
                else:
                    self.magical_name_prefixes.append(0)
                if bool(bitio.read(1, "bit")):
                    self.magical_name_suffixes.append(bitio.read(11, "bits"))
                else:
                    self.magical_name_suffixes.append(0)

        elif self.is_unique_quality:
            self.name_id_first = bitio.read(12, "bits")
            self.name = UNIQUE_STRINGS[self.name_id_first]

        if self.runeword:
            self.runeword_id = bitio.read(12, "bits")
            self.runeword_name = RUNEWORD_STRINGS[self.runeword_id]
            self.name = f'"{self.runeword_name}" {self.type_string}'
            bitio.read(4, "bits")  # always seems to be 5 ?

        # read a null-terminated 7-bit string
        if self.personalized:
            name = ""
            c = bitio.read(7, "bits")
            while c:
                name += chr(c)
                c = bitio.read(7, "bits")
            self.personalized_name = name
            self.name = name + "'s " + self.name

        # TODO: if the item is a tome, read another 5 bits
        if self.code in TOME_KEYS:
            self.tome_info = bitio.read(5, "bits")

        # strange timestamp bit
        bitio.read(1, "bit")
        # self.unusual_bit = bitio.read(1, 'bit')

        if self.has_defense:
            self.defense = bitio.read(11, "bits")

        if self.has_durability:
            self.durability_max = bitio.read(8, "bits")
            if 0 < self.durability_max:
                self.durability_current = bitio.read(8, "bits")
                bitio.read(1, "bit")

        if self.has_quantity:
            self.quantity = bitio.read(9, "bits")

        # if socketed, initialize the sockets to the given count
        if self.socketed:
            socket_count = bitio.read(4, "bits")
            self.sockets = [None for _ in range(socket_count)]

        # if the item is set quality, determine how many set magical traits to read
        if self.is_set_quality:
            # actually houses the number of times to read magical traits
            self.name_id_last = bitio.read(5, "bits")

        self.magical_props = MagicalProperties(bitio)

        # if the item is set quality, we must read additional magical properties
        if self.is_set_quality:
            self.set_props = []
            for _ in range(SET_LIST_MAP[self.name_id_last]):
                mp = MagicalProperties(bitio)
                self.set_props.append(mp)

        # if this is a runeword, there are runeword properties here
        if self.runeword:
            self.runeword_props = MagicalProperties(bitio)

        # read socketed items
        if self.socketed:
            for i in range(self.sockets_filled):
                self.sockets[i] = Item(handle)

        # test handle match
        end = handle.tell()
        handle.seek(start)
        self.original_binary = handle.read(end - start)
        result = self.to_bytes()

        if self.original_binary != result:
            print("[RECREATION_FAILURE]")
            bin_diff(self.original_binary, result)

    def to_bytes(self):
        def binstrings2bytes(*binary_strings):

            binstring = "".join(binary_strings).encode()
            n = len(binstring) % 8
            if 0 < n:
                binstring += (8 - n) * b"0"

            # join all of the binary strings together and reverse each in the process
            # int(binstring[i:i + 8][::-1], 2).to_bytes(1, 'little')
            return b"JM" + b"".join(
                int(binstring[i : i + 8][::-1], 2).to_bytes(1, "little") for i in range(0, len(binstring), 8)
            )

        parts = []

        def rbinapp(value, length):
            parts.append("{:0{width}b}".format(value, width=length)[::-1])

        # add each value into the parts, the specified number of bytes
        parts = []
        for value, bit_length in [
            (1 if self.quest_item else 0, 1),
            (0, 3),
            (self.identified, 1),
            (0, 5),
            # 10
            (self.autofill, 1),
            (1 if self.socketed else 0, 1),  # (0 < len(self.sockets), 1),
            (0, 1),
            (self.new, 1),
            (self.autoequip, 2),  # autoequip if the item is on a corpse (should be corpse-items only, it seems)
            (self.ear, 1),
            (self.starter, 1),
            (0, 3),
            # 21
            (1 if self.simple else 0, 1),
            (self.ethereal, 1),
            (1, 1),
            (self.personalized, 1),
            (0, 1),
            (self.runeword, 1),
            # 27
            # notes from: https://github.com/nickshanks/Alkor/blob/master/Source/Item.m#L103
            # 	(unknown 5 bits)
            # 	(version: 8 bits)
            # 		0 = pre-1.08; 1 = 1.08/1.09 normal; 2 = 1.10 normal; 100 = 1.08/1.09 expansion; 101 = 1.10 expansion
            # 	(unknown: 2 bits)
            (self.unknown, 15),  # frequently seen as 3232 (though this is probably multiple, smaller fields)
            # (3232, 15),
            # 42
            (self.parent, 3),
            (self.equipped, 4),
            (self.x, 4),
            (self.y, 3),
            (0, 1),
            (self.stored, 3),
            # self.code contains the 3 characters that identify the base item type (ex: 'buc' -> Buckler)
            (ord(self.code[0]), 8),
            (ord(self.code[1]), 8),
            (ord(self.code[2]), 8),
            (32, 8),
            # (len(self.sockets) - self.sockets.count(None), 3)
        ]:
            rbinapp(value, bit_length)

        # old method added these bits no matter what?
        rbinapp(self.sockets_filled, 3)

        # new method -- fails on Mephisto's Soulstone which reports sockets_filled == 1
        # rbinapp(len(self.sockets) - self.sockets.count(None), 3)

        if self.simple:
            return binstrings2bytes(*parts)

        rbinapp(self.id, 32)
        rbinapp(self.level, 7)
        rbinapp(self.quality, 4)
        rbinapp(self.multipic, 1)

        if self.multipic:
            rbinapp(self.pic_id, 3)

        rbinapp(self.class_specific, 1)
        if self.class_specific:
            rbinapp(self.class_info, 11)

        # TODO
        if self.ear:
            pass

        # different types of quality information
        if self.is_low_quality or self.is_high_quality:
            # if (QUALITY_LOW == self.quality) or (QUALITY_HIGH == self.quality):
            rbinapp(self.quality_info, 3)

        elif self.is_magic_quality:
            # elif QUALITY_MAGIC == self.quality:
            rbinapp(self.name_id_first, 11)
            rbinapp(self.name_id_last, 11)

        elif self.is_set_quality:
            # elif QUALITY_SET == self.quality:
            # set item name_id_last houses info for the set list map
            rbinapp(self.name_id_first, 12)  # old: rbinapp(self.name_id_last, 12)
            # print('\n\nSet id: {}\n\n'.format(self.name_id_last))
            # print('Level?: {}'.format(self.level))

        elif self.is_crafted_quality or self.is_rare_quality:
            rbinapp(self.name_id_first, 8)
            rbinapp(self.name_id_last, 8)

            for index in range(3):
                for fixes in (self.magical_name_prefixes, self.magical_name_suffixes):
                    fix = fixes[index]
                    if fix:
                        rbinapp(1, 1)
                        rbinapp(fix, 11)
                    else:
                        rbinapp(0, 1)

        elif self.is_unique_quality:
            # elif QUALITY_UNIQUE == self.quality:
            rbinapp(self.name_id_first, 12)

        if self.runeword:
            rbinapp(self.runeword_id, 12)
            rbinapp(5, 4)
            # rbinapp(self.runeword_info, 16)
            # rbinapp(self.runeword_bits, 16)

        if self.personalized:
            for c in self.personalized_name + "\x00":
                rbinapp(ord(c), 7)

        if self.type_id == TYPE_TOME:
            rbinapp(self.tome_info, 5)

        # WARNING: sometimes this is 1 and sometimes 0?
        # 1 bit timestamp?
        # parts.append('1')
        # parts.append('0')
        # print('Unusual bit:', self.unusual_bit)
        rbinapp(self.unusual_bit, 1)

        if self.has_defense:
            rbinapp(self.defense, 11)

        if self.has_durability:
            rbinapp(self.durability_max, 8)
            if self.durability_max:
                rbinapp(self.durability_current, 8)
                rbinapp(0, 1)

        # write the quantity of this item, if applicable
        if self.has_quantity:
            rbinapp(self.quantity, 9)

        # write the number of sockets this object has
        if self.sockets:
            rbinapp(len(self.sockets), 4)

        # set_list_count = SET_LIST_MAP[set_list_value]
        if QUALITY_SET == self.quality:
            rbinapp(self.name_id_last, 5)

        parts.append(self.magical_props.to_binstring())

        # each item in set_properties is a list?
        if QUALITY_SET == self.quality:
            if self.set_props is not None:
                for props in self.set_props:
                    parts.append(props.to_binstring())

        # write runeword properties
        if self.runeword:
            # logging.warning('Writing runeword properties ...')
            parts.append(self.runeword_props.to_binstring())

        # write the socketed items here
        result = binstrings2bytes(*parts)
        for s in self.sockets:
            if s is None:
                break
            result += s.to_bytes()

        return result

    #
    # 	convenience functions
    #

    def move(self, parent, stored, x, y):
        """Move this item to another location in the character's inventory. (not for equip)."""
        self.equipped = 0
        self.parent = parent
        self.equipped = 0
        self.x, self.y = x, y
        self.stored = stored

    def move_to_cube(self, x, y):
        """Syntactic sugar to move an item to the horadric cube."""
        self.move(parent=ITEM_STORED, stored=STORED_CUBE, x=x, y=y)

    def move_to_inventory(self, x, y):
        """Syntactic sugar to move an item to a position in the inventory."""
        self.move(parent=ITEM_STORED, stored=STORED_INVENTORY, x=x, y=y)

    def move_to_stash(self, x, y):
        """Syntactic sugar to move an item to a position in the private stash."""
        self.move(parent=ITEM_STORED, stored=STORED_STASH, x=x, y=y)

    def personalize(self, name):
        """Personalize an item by adding a character's name to the beginning, when presented in game."""
        # i do not believe items can be simple and personalized
        self.simple = False
        self.personalized = 1
        self.personalized_name = name

    def set_code(self, code):
        """Set the item code, type id, and type string values."""
        self.code = code
        self.type_id = get_type_id(code)
        self.type_string = get_type_string(code)


class Items(list):

    MAGIC = b"\x4a\x4d"

    def __init__(self, handle=None):

        self.corpse_items = False
        self.corpse_data = None
        if handle is not None:
            self.from_handle(handle)

    def from_handle(self, handle):

        # read the magic header and ensure it is good
        magic = handle.read(2)
        assert self.MAGIC == magic, "Invalid magic: %s" % magic

        # determine how many items there are to read
        items_to_read = struct.unpack("<H", handle.read(2))[0]

        # probable corpse data header, example: b'JM\x01\x00|\x00\xf8\x02\xb4\x16\x00\x00Z\x11\x00\x00'
        if items_to_read == 1:
            self.corpse_items = True
            self.corpse_data = handle.read(12)
            self.from_handle(handle)

        else:
            # read items from the handle
            items_read = 0
            while items_read < items_to_read:
                item = Item(handle)
                if item.parent != ITEM_SOCKETED:
                    items_read += 1
                self.append(item)

    def to_bytes(self):
        # write the items back to bytes format

        bio = BytesIO()

        # if these are corpse items, we must write the corpse header first
        if self.corpse_items:
            bio.write(self.MAGIC)
            bio.write(struct.pack("<H", 1))
            bio.write(self.corpse_data)

        # header that describes the amount of items
        bio.write(self.MAGIC)
        bio.write(struct.pack("<H", self.count))

        # write each of the items to the bio
        for item in self:
            bio.write(item.to_bytes())

        # seek 0 and return the bytes
        bio.seek(0)
        return bio.read()

    @property
    def count(self):
        # count the number of items contained that are not socketed
        return sum(1 if item.parent != ITEM_SOCKETED else 0 for item in self)
