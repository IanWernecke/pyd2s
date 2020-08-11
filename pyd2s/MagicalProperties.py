# module imports
from pyd2s.constants import CLASS_STRINGS, MAGICAL_PROPERTIES
from pyd2s.utilities import binstring, to_binstring


class MagicalProperty(object):
    def __init__(self, flag):

        # # if the flag appears invalid, dump some debugging information
        # if flag not in MAGICAL_PROPERTIES.keys():
        # 	data = bitio.read_remaining()
        # 	if b'JM' in data:
        # 		data = data[:data.index(b'JM')]
        # 	bin_data = binstring(data, len(data))
        # 	print(f'Bytes remaining: {data}')
        # 	print(f'Length of bytes remaining: {len(data)}')
        # 	print(f'Binary remaining: {bin_data}')
        # 	print(f'Length of binary remaining: {len(bin_data)}')
        # 	raise ValueError(f'Invalid flag {flag} in bitio!')

        self.flag = flag
        self.lengths, self.bias, self.mstring = MAGICAL_PROPERTIES[flag]
        self.values = [0 for _ in enumerate(self.lengths)]

    def __str__(self):
        """Display this magical property in a nice format."""
        if self.flag in (83, 84):
            return f"[ {self.mstring.format(CLASS_STRINGS[self.values[0]], self.values[1])} ]"

        # +1 to Summoning Skills (Necromancer Only)
        # if self.flag == 188:
        # 	return f'[ {self.mstring.format(CLASS_STRINGS[self.values[0]], self.values[1])} ]'

        return "[ " + self.mstring.format(*self.values) + " ]"

    def max(self):
        """Set this magical property to the maximum value allowed by the number of bits."""
        values = [int("1" * length, 2) for length in self.lengths]
        if self.bias is not None:
            for index, value in enumerate(values):
                values[index] = value - self.bias
        self.values = values

    def from_bitio(self, bitio):
        """Load the data for this magical property from a BitIO class object."""
        nums = [bitio.read(l, "bits") for l in self.lengths]
        if self.bias is not None:
            nums = [n - self.bias for n in nums]
        self.values = nums

    def to_binstring(self):

        parts = ["{:09b}".format(self.flag)[::-1]]
        parts.extend(
            "{:0{width}b}".format(value if self.bias is None else value + self.bias, width=self.lengths[index])[::-1]
            for index, value in enumerate(self.values)
        )
        return "".join(parts)


class MagicalProperties(list):
    def __init__(self, bitio):
        super(MagicalProperties, self).__init__()
        while True:

            flag = bitio.read(9, "bits")
            if flag == 0x1FF:
                break

            mp = MagicalProperty(flag)
            mp.from_bitio(bitio)
            self.append(mp)
            # self.append(MagicalProperty(flag, bitio))

    def __str__(self):
        return "Magical Properties:\n\t{}".format("\n\t".join("%s" % magical_property for magical_property in self))

    def max(self):
        """Maximize all of the properties in this collection."""
        return len(mp.max() for mp in self)

    def to_binstring(self):

        return "".join(mp.to_binstring() for mp in self) + ("1" * 9)
