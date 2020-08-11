# module imports
from pyd2s.Items import Items
from pyd2s.Game import Game
from pyd2s.constants import ITEM_STORED
from pyd2s.decorators import Main
from pyd2s.utilities import get_character_save_file


@Main(
    (['from_character'], {'help': 'The character to load.'}),
    (['to_character'], {'help': 'The character to write to.'}),
    (['item_name'], dict(help='All or part of an item name to be found in the first character.')),
    (['-w', '--write'], dict(default=False, action='store_true', help='Whether to perform the write.'))
)
def main(args):

    src_file = get_character_save_file(args.from_character)
    dst_file = get_character_save_file(args.to_character)

    assert src_file is not None
    assert dst_file is not None

    src_game = Game()
    src_game.from_file(src_file)
    for item in src_game.items:
        # print('ITEM NAME: {}'.format(item.name))
        if args.item_name == item.type_name:
            print(item)
            break
        if item.name is None:
            continue
        if args.item_name in item.name:
            print(item)
            break

    else:
        print('Unable to find item name that contains: "{}"'.format(args.item_name))
        return 1

    # item.x = 0
    # item.y = 0
    # item.parent = ITEM_STORED
    # item.equipped = 0
    print(item)

    # return 0

    dst_game = Game()
    dst_game.from_file(dst_file)
    # item.x = 0
    # item.y = 0
    # item.parent = ITEM_STORED
    # item.equipped = 0
    dst_game.items.append(item)
    print(dst_game.original_binary)
    print(dst_game.to_string())
    test_game = Game()
    test_game.from_string(dst_game.to_string())
    # dst_game.corpse = Items()
    # dst_game.corpse.append(item)

    # print(dst_game)

    if args.write:
        dst_game.to_file(dst_file)

    return 0
