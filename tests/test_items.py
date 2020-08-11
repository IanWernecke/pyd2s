# standard imports
import os
import sys

# module imports
from pyd2s.Game import Game
from pyd2s.utilities import get_character_save_file


def test_items(characters):
    for name in characters:
        print("Reading character: {}".format(name))
        save_file = get_character_save_file(name)
        game = Game()
        game.from_file(save_file)
        for item in game.items:
            assert item.original_binary == item.to_bytes()
    #
    # name = 'Laenii'
    # save_file = get_character_save_file(name)
    # game = Game()
    # game.from_file(save_file)
    # assert game.original_binary == game.to_string()
