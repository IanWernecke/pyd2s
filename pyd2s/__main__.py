# standard imports
import os
from cmd import Cmd
from collections import defaultdict
from functools import wraps

# package imports
from pyd2s.Game import Game
from pyd2s.Storage import Storage
from pyd2s.constants import (
    GEM_CODES,
    ITEM_BELT,
    ITEM_EQUIPPED,
    ITEM_STORED,
    MISC_STRINGS,
    RUNE_CODES,
    RUNE_STRINGS,
    RUNEWORDS,
    STORED_CUBE,
    STORED_INVENTORY,
    STORED_STASH
)
from pyd2s.decorators import Main
from pyd2s.utilities import create_backup, get_backups, get_characters, get_character_save_file, restore_backup


def display_items(items, title, attribute):
    """Display the items in a list whose given attribute is 'true'."""
    print(f'{title}\n{"=" * 50}')
    for index, item in enumerate(items):
        if hasattr(item, attribute) and getattr(item, attribute):
            print(f'  [{index:03}] {item.pretty_name}')
    print()


def parse_item_indexes(raw_string, max_index):
    """Parse desired item indexes from the given string."""
    indexes = []
    for int_str in raw_string.split(' '):
        if not int_str.isdigit():
            print(f'Parse integer string is invalid: {int_str}')
            return False, []
        indexes.append(int(int_str))

    if not indexes:
        print(f'The index string was too short: {raw_string}')
        return False, []

    if max(indexes) > max_index:
        print(f'Index {max(indexes)} is too high.')
        return False, []

    return True, indexes


class GameCommands(Cmd):

    def __init__(self, character):
        """Set up this class object to handle various commands related to handling the saved game."""
        self.prompt = f'pyd2s>{character}> '
        super(GameCommands, self).__init__()

        self.character = character
        self.game = Game(character)
        self.game.from_file()
        self.altered = False

    def do_attr(self, arg):
        """Show the attributes of the character."""
        print("Attributes:")
        print(f'{"="*20} {"="*20}')
        for key in self.game.attributes.keys():
            print(f'{key:>20}: {self.game.attributes[key]}')

    def do_backup(self, arg):
        """Create a backup for the current character (for use with 'restore')."""
        zip_file = create_backup(self.character)
        print(f'Created backup: "{zip_file}"')

    def do_close(self, arg):
        """Close the open save file, prompting if a change has been made."""
        # if the game has been altered, determine whether the file should be written back to disk
        if self.altered:
            answer = ''
            while answer not in ('y', 'n'):
                answer = input("Do you wish to write your changes? (y/n) ").lower().strip()
                if answer == 'y':
                    result = self.game.to_file()
                    print(f'Wrote bytes: {result}')
                    self.altered = False
        return 1

    def complete_item(self, text, line, begidx, endidx):
        """Return item names that begin with the given text."""
        return [
            item.name
            for item in self.game.items
            if item.name.startswith(text)
        ]

    def do_item(self, arg):
        """Show more details about an item in the inventory (int for item by index, str for word match)."""
        if arg.replace(' ', '').isdigit():
            for index in [int(arg_index) for arg_index in arg.split()]:
                print(f'{self.game.items[index]}\n')
            return 0

        # attempt to find a word match among the items in the inventory
        for item in self.game.items:
            if arg in item.name:
                print(f'{item}\n')

    def do_items(self, arg):
        """Display a short listing of the items on the given character."""
        # TODO: this should be done by equipped, inventory, stash
        equipped_items = []
        belt_items = []
        inv_items = []
        stash_items = []
        cube_items = []
        for index, item in enumerate(self.game.items):
            item_str = f'  [{index:02}] {item.pretty_name}'
            if item.parent == ITEM_STORED:
                if item.stored == STORED_INVENTORY:
                    inv_items.append(item_str)
                elif item.stored == STORED_STASH:
                    stash_items.append(item_str)
                elif item.stored == STORED_CUBE:
                    cube_items.append(item_str)
                else:
                    print(f'Item stored? {item_str}, Parent: {item.parent}, Stored: {item.stored}')
            elif item.parent == ITEM_EQUIPPED:
                equipped_items.append(item_str)
            elif item.parent == ITEM_BELT:
                belt_items.append(item_str)
            else:
                print(f'What is this? \n{item}')

        for title, item_strings in [
                ("Equipped", equipped_items),
                ("Belt", belt_items),
                ("Inventory", inv_items),
                ("Stash", stash_items),
                ("Cube", cube_items),
        ]:
            if not item_strings:
                continue
            print(f'{title}\n{"=" * 50}')
            for item_string in item_strings:
                print(item_string)
            print('')

    def do_reload(self, arg):
        """Load the save file from disk."""
        result = self.game.from_file(self.save_file)
        print(f'Reload result: "{result}"')

    def do_reset_akara(self, arg):
        """This command resets Akara's ability to reset the character's stats and skills."""
        self.game.reset_akara()
        self.altered = True

    def do_restore(self, arg):
        """Restore the character to the most recent backup."""
        zip_file = get_backups(self.character)[-1]
        print(f'Restoring from: "{zip_file}"')
        restore_backup(zip_file)
        self.game.from_file(self.save_file)
        print('Restored.')

    def do_rm(self, arg):
        """Delete items from the inventory."""
        okay, indexes = parse_item_indexes(arg, max_index=len(self.game.items) - 1)
        if not okay:
            return 0

        with Storage() as store:
            for index in sorted(indexes, reverse=True):
                print(f'Removing: {self.game.items[index].pretty_name}')
                self.game.items.pop(index)
                self.altered = True

    def do_store(self, arg):
        """Move an item to storage."""
        okay, indexes = parse_item_indexes(arg, max_index=len(self.game.items) - 1)
        if not okay:
            return 0

        with Storage() as store:
            for index in sorted(indexes, reverse=True):
                print(f'Storing: {self.game.items[index].pretty_name}')
                store.append(self.game.items.pop(index))
                self.altered = True

    def do_store_gems(self, arg):
        """Move gems from the current character's inventory, stash, and cube into a local storage file."""
        with Storage() as store:

            # move gems to the open store
            index = 0
            while index < len(self.game.items):
                if self.game.items[index].is_gem:
                    store.append(self.game.items.pop(index))
                    self.altered = True
                    continue
                index += 1

    def do_store_runes(self, arg):
        """Move runes from the current character's inventory, stash, and cube into a local storage file."""
        with Storage() as store:

            # move runes to the open store
            index = 0
            while index < len(self.game.items):
                if self.game.items[index].is_rune:
                    store.append(self.game.items.pop(index))
                    self.altered = True
                    continue
                index += 1

    def do_write(self, arg):
        """Write any changes made back to disk."""
        result = self.game.to_file()
        print(f'Wrote bytes: {result}')
        self.altered = False


class StorageCommands(Cmd):

    prompt = 'pyd2s>storage> '

    def __init__(self):
        """Access the storage file to read the storage or give items to a player."""
        super(self.__class__, self).__init__()
        self.storage = Storage()
        if os.path.isfile(self.storage.file_path):
            self.storage.read()
        self.altered = False

    def do_amulets(self, arg):
        """Display all of the rings in the storage file."""
        display_items(self.storage, 'Amulets', 'is_amulet')

    def do_armors(self, arg):
        """Display all of the rings in the storage file."""
        display_items(self.storage, 'Armors', 'is_armor')

    def do_close(self, arg):
        """Close the storage container and return."""
        if self.altered:
            answer = ''
            while answer not in ('y', 'n'):
                answer = input("Do you wish to write your changes? (y/n) ").lower().strip()
                if answer == 'y':
                    result = self.storage.write(self.storage.file_path)
                    print(f'Wrote {result} bytes to file "{self.storage.file_path}"!')
                    self.altered = False

        return 1

    def do_crucible(self, arg):
        """Merge two rare items together."""
        okay, indexes = parse_item_indexes(raw_string=arg, max_index=len(self.storage) - 1)
        if not okay:
            return 0

        if len(indexes) < 2:
            print(f'The crucible command requires two arguments. Invalid: "{arg}"')
            return 0

        # append the magical prefixes from the second+ items onto the first
        parent_index = indexes[0]
        child_indexes = indexes[1:]

        for child_index in child_indexes:
            for child_prop in self.storage[child_index].magical_props:
                for parent_prop in self.storage[parent_index].magical_props:

                    # only continue if the parent property is the same type as the child property
                    if parent_prop.flag != child_prop.flag:
                        continue

                    # take the higher values (this could work negatively on some negative effects)
                    for parent_prop_value_index in range(len(parent_prop.values)):
                        parent_prop.values[parent_prop_value_index] = max(
                            parent_prop.values[parent_prop_value_index],
                            child_prop.values[parent_prop_value_index]
                        )
                    break

                # if no match was found for the flag, just append it to the parent
                else:
                    self.storage[parent_index].magical_props.append(child_prop)

        # TODO: remove each of the items that was absorbed into the parent
        self.altered = True

    def complete_give(self, text, line, begidx, endidx):
        """
        text: (string) prefix we are attempting to match
        line: (string) the current input line with leading whitespace removed
        begidx: (int) the beginning index of the prefix text
        endidx: (int) the ending index of the prefix text
        """
        # print(f'Text: "{text}"')
        # print(f'Line: "{line}"')
        # print(f'Indexes: ({begidx}, {endidx})')

        # if it is the first argument, return character names
        if line[:endidx].count(' ') == 1:
            return [
                character
                for character in get_characters()
                if character.startswith(text)
            ]

    def do_gems(self, arg):
        """Display all of the items in the storage container."""
        display_items(self.storage, 'Gems', 'is_gem')

        gems = defaultdict(int)
        first_index = dict()
        for index, item in enumerate(self.storage):
            if not item.is_gem:
                continue
            gems[item.code] += 1
            if item.code not in first_index:
                first_index[item.code] = index

        print(f'Gems: [first index] name (count)\n{"=" * 50}')
        for code in sorted(GEM_CODES):
            if code in gems:
                print(f'  [{first_index[code]:03}] {MISC_STRINGS[code]} ({gems[code]})')
        print()

    def do_give(self, arg):
        """Give a character an item."""
        if arg.count(' ') > 1:
            print(f'Too many arguments: "{arg}"')
            return 0

        # get the character name and the item index from the given arguments
        character, index = arg.split(' ')
        index = int(index)

        # ensure the character is good
        if character not in get_characters():
            print(f'Invalid character: "{character}"')
            return 0

        # ensure the index is good
        if index >= len(self.storage):
            print(f'Index {index} is too high.')
            return 0

        print(f'Giving {character}: {self.storage[index].pretty_name} ...')
        with Game(character) as game:
            item  = self.storage.pop(index)
            item.move_to_inventory(0, 0)
            game.items.append(item)
            self.altered = True
        print('Complete.')

    def do_grep(self, arg):
        """Search the items for a particular trait or attribute."""
        # obtain the text to search for
        text = arg.strip()
        if not text:
            print('Text required.')
            return 0

        # print out the items where the text appears inside of the item description
        print(f'Grep (text: "{text}") (excluded: gems, runes)\n{"=" * 50}')
        for index, item in enumerate(self.storage):
            if item.is_gem or item.is_rune:
                continue
            item_str = str(item)
            if text in item_str:
                print(f'  [{index:03}] {item.pretty_name}')

    def do_info(self, arg):
        """Print information about the storage file."""
        print(f'Storage file location: {self.storage.file_path}')
        print(f'Storage file contains {len(self.storage)} items.')

    def do_item(self, arg):
        """Display an item in full detail."""
        if not arg:
            print("This command requires an index.")
            return 0

        # ensure the given argument is a digit
        if not arg.isdigit():
            print(f'This command requires a number, not {arg}')
            return 0

        # convert the string to an integer and ensure it is within range
        index = int(arg)
        if index >= len(self.storage):
            print(f'Maximum index: {len(self.storage) - 1}')
            return 0

        print(f'{self.storage[index]}\n')

    def do_items(self, arg):
        """Display a short listing of the items in the storage."""
        results = dict()
        for index, item in enumerate(self.storage):
            if item.is_gem or item.is_rune:
                continue
            results[f'{item.name}/{index:003}'] = (index, item)

        print(f'Items (excluded: gems, runes)\n{"=" * 50}')
        for key in sorted(results.keys()):
            index, item = results[key]
            print(f'  [{index:03}] {item.pretty_name}')
        print()

    def do_read(self, arg):
        """Read the save file from disk."""
        self.storage = Storage()
        if not os.path.isfile(self.storage.file_path):
            print(f'Storage file path does not yet exist: {self.storage.file_path}')
            return 0

        result = self.storage.read()
        print(f'Read from file: "{self.storage.file_path}"')

    def do_rings(self, arg):
        """Display all of the rings in the storage file."""
        print(f'Rings\n{"=" * 50}')
        for index, item in enumerate(self.storage):
            if item.is_ring:
                print(f'  [{index:02}] {item.pretty_name}')
        print()

    def do_rm(self, arg):
        """Delete items from the inventory."""
        okay, indexes = parse_item_indexes(raw_string=arg, max_index=len(self.storage) - 1)
        if not okay:
            return 0

        for index in sorted(indexes, reverse=True):
            print(f'Removing: {self.storage[index].pretty_name}')
            self.storage.pop(index)
            self.altered = True

    def do_runes(self, arg):
        """Display all of the runes in the storage container."""
        runes = defaultdict(int)
        first_index = dict()
        for index, item in enumerate(self.storage):
            if not item.is_rune:
                continue
            runes[item.code] += 1
            if item.code not in first_index:
                first_index[item.code] = index

        print(f'Runes: [first index] name (count)\n{"=" * 50}')
        for code in sorted(RUNE_CODES):
            if code in runes:
                print(f'  [{first_index[code]:03}] {MISC_STRINGS[code]} ({runes[code]})')
        print()

    def do_runewords(self, arg):
        """Display the runewords that the storage has enough runes for."""
        # count the rune codes currently in the inventory
        runes_stored = defaultdict(int)
        for index, item in enumerate(self.storage):
            if not item.is_rune:
                continue
            runes_stored[item.code] += 1

        # for each of the runewords, check if we have enough
        for key in RUNEWORDS:

            runeword, recipe, ladder_only = RUNEWORDS[key]

            # do not even bother showing ladder only runewords
            if ladder_only:
                continue

            # count each of the runes required
            runes_needed = defaultdict(int)
            for rune in recipe:
                runes_needed[rune] += 1

            # if the runes_needed is less than or equal to the runes stored, for each, we can craft it
            for rune in runes_needed:
                if runes_stored[rune] < runes_needed[rune]:
                    break
            else:
                print(f'{runeword} ({" ".join(RUNE_STRINGS[rune] for rune in recipe)})')

    def do_uniques(self, arg):
        """Display the unique items in the inventory."""
        display_items(self.storage, 'Uniques', 'is_unique_quality')

    def do_weapons(self, arg):
        """Display all of the rings in the storage file."""
        display_items(self.storage, 'Weapons', 'is_weapon')

    def do_write(self, arg):
        """Write the storage object to the storage file."""
        result = self.storage.write(self.storage.file_path)
        print(f'Wrote {result} bytes to file "{self.storage.file_path}"!')
        self.altered = False


class Commands(Cmd):

    intro = 'Welcome to the python Diablo 2 save file editor. Type help or ? to list comands.\n'
    prompt = 'pyd2s> '

    def __init__(self):
        super(Commands, self).__init__()
        self.characters = get_characters()
        self.character = None
        self.game = None
        self.save_file = None

    #
    #   game operations
    #

    def do_exit(self, arg):
        """Exit the command loop."""
        return 1

    def complete_open(self, text, line, begidx, endidx):
        """
        text: (string) prefix we are attempting to match
        line: (string) the current input line with leading whitespace removed
        begidx: (int) the beginning index of the prefix text
        endidx: (int) the ending index of the prefix text
        """
        # print(f'Text: "{text}"')
        # print(f'Line: "{line}"')
        # print(f'Indexes: ({begidx}, {endidx})')
        return [
            character
            for character in self.characters
            if character.startswith(text)
        ]

    def do_open(self, arg):
        """Open a character's save file for editing."""
        if arg not in self.characters:
            print(f'Characters:')
            for character in self.characters:
                print(f'  {character}')
            return 0

        GameCommands(arg).cmdloop()

    def do_storage(self, arg):
        """Open the shared stash provided by this python module."""
        StorageCommands().cmdloop()


@Main()
def main(args):
    Commands().cmdloop()
    return 0
