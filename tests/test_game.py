# standard imports
import os
import sys

# module imports
from pyd2s.Game import Game
from pyd2s.utilities import get_character_save_file


def test_game_restore(characters):
    for name in characters:
        print('Testing game restore for character: "{}"'.format(name))
        save_file = get_character_save_file(name)
        game = Game()
        game.from_file(save_file)
        assert game.original_binary == game.to_bytes()
