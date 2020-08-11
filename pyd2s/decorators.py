#!python3
"""This file is designed to provide decorators for other files."""


import argparse
import inspect
import logging
import sys

from functools import wraps


#
#   Standard Decorators
#

def args2keywords(function):
    """
    Wrap a function such that is converts given NameSpace objects into keywords.

    :param function: the decorated function that requires keywords
    :return: a wrapped function that accepts args
    """
    @wraps(function)
    def wrapper(args, **kwargs):
        kwargs.update(**vars(args))
        return function(**kwargs)
    return wrapper


#
#   Create Parser Decorators
#

class CreateParserRoot(object):
    """The root CreateParser decorator."""

    def __init__(self):
        """Create a parser object."""
        self.parser = argparse.ArgumentParser()

    def __call__(self, function):
        """Parse the arguments for the function and pass the result."""
        @wraps(function)
        def wrapper(arguments):

            if (arguments is None) or isinstance(arguments, list):
                args = self.parser.parse_args(arguments)

            elif isinstance(arguments, unicode) or isinstance(arguments, str):
                args = self.parser.parse_args(shlex.split(arguments))

            else:
                raise RuntimeError('Unhandled arguments type: "{}"'.format(type(arguments)))

            return function(args)

        return wrapper


class CreateParser(CreateParserRoot):
    """Decorator to create a basic (args, kwargs) parser."""

    def __init__(self, *tuples):
        """Add all of the arguments to the parser."""
        super(CreateParser, self).__init__()
        for args, kwargs in tuples:
            self.parser.add_argument(*args, **kwargs)


class CreateParserCommands(CreateParserRoot):
    """Decorator to create a compound (cmd_name, cmd_help, (args, kwargs)) parser."""

    def __init__(self, *command_tuples):
        """Add all of the subparsers to the parser."""
        super(CreateParserCommands, self).__init__()
        subparsers = self.parser.add_subparsers(dest='command')
        for cmd_name, cmd_help, tuples in command_tuples:
            option = subparsers.add_parser(cmd_name, help=cmd_help)
            for args, kwargs in tuples:
                option.add_argument(*args, **kwargs)


#
#   Parse Decorators
#

class ParseRoot(object):
    """Parse the arguments given to the decorated function and pass the resulting NameSpace."""

    # overwrite these in children
    main_class = False
    main_actual = False
    create_parser = CreateParserRoot

    # Main Decorators require this for verbosity tuple injection
    verbosity_tuple = (
        ['-v', '--verbosity'],
        {
            'action': 'count',
            'default': 0,
            'dest': 'verbosity',
            'help': 'Configure how verbose the logger should be.'
        }
    )

    def __init__(self, *tuples):
        """Assign the tuples to self, to be passed in upon calling."""
        self.tuples = tuples

    def __call__(self, function):
        """Intercept the given arguments and pass them to the parser."""
        @self.create_parser(*self.tuples)
        @wraps(function)
        def wrapper(args):

            # logging should be configured if this is a main class and we are inside '__main__'.
            if self.main_actual:

                level = logging.WARNING - (10 * args.verbosity)
                logging.basicConfig(
                    format='%(asctime)s [%(levelname)9s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=level
                )
                logging.debug('Logging level set to: %d', level)

            return function(args)

        # return the function if this is not a main class
        if not self.main_class:
            return wrapper

        # return the function if the parent frame is not main
        if inspect.currentframe().f_back.f_globals['__name__'] != '__main__':
            return wrapper

        self.main_actual = True

        # call the decorated function and exit with the system code if possible.
        result = wrapper(None)
        if isinstance(result, int):
            sys.exit(result)
        sys.exit(0)


class Parse(ParseRoot):
    """Parse the given arguments with CreateParser."""

    main_class = False
    create_parser = CreateParser


class ParseCommands(ParseRoot):
    """Parse the given arguments with CreateParserCommands."""

    main_class = False
    create_parser = CreateParserCommands


#
#   Main Decorators
#

class Main(ParseRoot):
    """Parse and call the decorated function."""

    main_class = True
    create_parser = CreateParser

    def __init__(self, *tuples):
        """Inject the verbosity tuple into the (args, kwargs) tuples."""
        super(Main, self).__init__(self.verbosity_tuple, *tuples)


class MainCommands(ParseRoot):
    """ParseCommands and call the decorated function."""

    main_class = True
    create_parser = CreateParserCommands

    def __init__(self, *command_tuples):
        """Inject the verbosity tuple into the command tuples."""
        super(MainCommands, self).__init__(
            (cmd_name, cmd_help, tuple(list(tuples) + [self.verbosity_tuple]))
            for cmd_name, cmd_help, tuples in command_tuples
        )


#
#   Logging Class Decorators
#

class LogLevelContainer(object):
    """A class object to hold a logging level, for use when inherited."""

    def __init__(self, level=logging.NOTSET):
        """Store a log level."""
        self.level = level


class LogSteps(LogLevelContainer):
    """A class object to hold a logging level and report when a function is entered and exited."""

    def __call__(self, function):
        """Report when a function enters and exits."""
        @wraps(function)
        def wrapper(*args, **kwargs):
            logging.log(self.level, 'Function: %s, Enter', function.__name__)
            result = function(*args, **kwargs)
            logging.log(self.level, 'Function: %s, Exit', function.__name__)
            return result
        return wrapper


class LogArguments(LogLevelContainer):
    """A class object to hold a logging level and report the args and kwargs of a decorated function."""

    def __call__(self, function):
        """Log the args and kwargs of the decorated function."""
        @wraps(function)
        def wrapper(*args, **kwargs):
            for arg in args:
                logging.log(self.level, 'Function: %s, Arg: %r', function.__name__, arg)
            for k in kwargs:
                logging.log(self.level, 'Function: %s, Key: %r, Value: %r', function.__name__, k, kwargs[k])
            return function(*args, **kwargs)
        return wrapper


class LogResult(LogLevelContainer):
    """A class object to hold a logging level and report the result of a function at that level."""

    def __call__(self, function):
        """Log the result of a decorated function."""
        @wraps(function)
        def wrapper(*args, **kwargs):
            result = function(*args, **kwargs)
            logging.log(self.level, 'Function: %s, Result: %r', function.__name__, result)
            return result
        return wrapper


class LogAll(LogLevelContainer):
    """A class object to log entry, args, kwargs, result, and exit of a function."""

    def __call__(self, function):
        """Wrap a bunch of decorators around the given function so information is logged."""
        @LogSteps(self.level)
        @LogArguments(self.level)
        @LogResult(self.level)
        @wraps(function)
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)
        return wrapper


class LogDecoratorContainer(object):
    """An object to be created that houses decorator functions."""

    def __init__(self, level=logging.NOTSET):
        """Assign the decorations to self."""
        self.steps = LogSteps(level)
        self.args = LogArguments(level)
        self.result = LogResult(level)
        self.all = LogAll(level)


# define some convenient decorator containers
notset = LogDecoratorContainer(logging.NOTSET)
debug = LogDecoratorContainer(logging.DEBUG)
info = LogDecoratorContainer(logging.INFO)
warning = LogDecoratorContainer(logging.WARNING)
error = LogDecoratorContainer(logging.ERROR)
critical = LogDecoratorContainer(logging.CRITICAL)


@Main()
@info.all
def main(args):
    """
    When this script is the main one executed, this function will be performed.

    :param args: a Namespace object
    :return: a system exit code
    """
    # write code here
    return 0
