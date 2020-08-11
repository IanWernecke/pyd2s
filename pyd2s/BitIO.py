# standard imports
from io import BytesIO

# module imports
from pyd2s.decorators import debug
from pyd2s.utilities import binstring, rbits


UNIT_LENGTHS = {
    "bit": 1,
    "bits": 1,
    "byte": 8,
    "bytes": 8,
    "char": 8,
    "chars": 8,
    "short": 16,
    "shorts": 16,
    "long": 32,
    "longs": 32,
}


class BitIO(object):
    def __init__(self, handle=None, rread=False, rvalues=False):

        self.handle = handle
        self.rread = rread
        self.rvalues = rvalues
        self.binio = BytesIO()
        self.remaining = 0

    def _require(self, count):

        ph = self.binio.tell()
        self.binio.seek(ph + self.remaining)
        while self.remaining < count:
            bs = binstring(self.handle.read(1), 1)
            self.binio.write(bs[::-1] if self.rread else bs)
            # s = '{:08b}'.format(ord(self.handle.read(1)))
            # self.binio.write((s[::-1] if self.rread else s).encode())
            self.remaining += 8

        self.binio.seek(ph)

    def end_byte(self):

        if 0 < self.remaining:
            self.binio.write(b"0" * self.remaining)
            self.remaining = 0

    def read(self, count, unit):

        assert self.handle is not None, "This object requires a handle to read."

        if unit not in UNIT_LENGTHS.keys():
            raise Exception("Invalid unit: %s" % unit)

        required = count * UNIT_LENGTHS[unit]
        self._require(required)

        self.remaining -= required
        data = self.binio.read(required)

        # convert to integer
        if unit in ("bit", "bits", "short", "shorts", "long", "longs"):
            result = int(data, 2)
            if self.rvalues:
                result = rbits(result, required)

        # convert to bytes
        elif unit in ("byte", "bytes", "char", "chars"):

            # result = data
            if self.rvalues:
                result = b"".join(int(data[i : i + 8][::-1], 2).to_bytes(1, "little") for i in range(0, len(data), 8))
            else:
                result = b"".join(int(data[i : i + 8], 2).to_bytes(1, "little") for i in range(0, len(data), 8))

        # unknown
        else:
            raise Exception("Unrecognized unit: %s" % unit)

        return result

    def read_bits(self, count):

        self._require(count)
        self.remaining -= count
        return int(self.binio.read(count), 2)

    def read_bytes(self, count):

        return self.read(count, "bytes")

    def read_remaining(self):

        end = self.handle.tell()
        if 0 < self.remaining:
            self.read_bits(self.remaining)
        bytes_remaining = len(self.handle.read())
        self.handle.seek(end)
        return self.read_bytes(bytes_remaining)

    def to_bytes(self):

        # set a placeholder and prepare to read through the end of the last byte
        ph = self.binio.tell()
        self.end_byte()
        self.binio.seek(0)

        # prepare a place to write the bytes
        result = BytesIO()
        data = self.binio.read(8)
        while 0 < len(data):
            if self.rread:
                data = data[::-1]
            dint = int(data, 2)
            dbytes = dint.to_bytes(1, "little")
            result.write(dbytes)
            data = self.binio.read(8)

        # return the bytes
        self.binio.seek(ph)
        result.seek(0)
        return result.read()

    def write(self, value, count, unit):

        # determine how long the information that we are supposed to write is
        length = count * UNIT_LENGTHS[unit]

        # create a binary string of the specified length, given the value
        bs = binstring(value, length)
        if self.rvalues:
            bs = bs[::-1]
        self.binio.write(bs)
        return length
