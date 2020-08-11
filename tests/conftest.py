# standard imports
import os
import sys

# installed imports
import pytest


base_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(base_dir, '..'))

# ugly
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


from utilities import get_characters, get_character_save_file


@pytest.fixture(scope='session')
def characters():
    return get_characters()


@pytest.fixture(scope='session')
def character_save_files(characters):
    return [get_character_save_file(name) for name in characters]
