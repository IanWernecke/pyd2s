# standard imports
import os

# module imports
from pyd2s.Items import Items


# use a file in the current working directory, so the user can move it around easier
DEFAULT_STORAGE_PATH = os.path.abspath("storage.d2i")


class Storage(Items):
    def __init__(self, file_path=DEFAULT_STORAGE_PATH):
        super(self.__class__, self).__init__()
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        self.file_path = file_path

    def __enter__(self):
        if os.path.isfile(self.file_path):
            self.read(self.file_path)
        return self

    def __exit__(self, exc_type=None, exc_value=None, exc_traceback=None):
        if exc_type is None:
            self.write(self.file_path)

    def read(self, file_path=None):
        if file_path is None:
            file_path = self.file_path
        with open(file_path, "rb") as file_handle:
            return self.from_handle(file_handle)

    def write(self, file_path=None):
        if file_path is None:
            file_path = self.file_path
        with open(file_path, "wb") as file_handle:
            return file_handle.write(self.to_bytes())
