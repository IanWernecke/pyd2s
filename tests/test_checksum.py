import os
import sys

import pytest

# installed imports
from pyd2s.Game import Game, create_checksum_bytes, patch_checksum
from pyd2s.utilities import get_characters, get_character_save_file


def test_checksum_bytes(characters):
    for name in characters:
        save_file = get_character_save_file(name)
        game = Game()
        game.from_file(save_file)
        checksum = create_checksum_bytes(game.original_binary)
        assert game.original_binary[12:16] == checksum


def test_checksum_patch(characters):
    for name in characters:
        save_file = get_character_save_file(name)
        game = Game()
        game.from_file(save_file)
        assert game.original_binary == patch_checksum(game.original_binary)
