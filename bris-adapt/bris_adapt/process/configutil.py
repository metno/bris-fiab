from typing import Final
import os


def find_config_file(filename: str) -> str:
    '''Find configuration file in current or parent directories.'''
    search_paths: Final = ['.', 'etc',
                           'bris-adapt/etc', '/etc', '/usr/local/etc']
    for path in search_paths:
        full_path = f"{path}/{filename}"

        if os.path.isfile(full_path):
            return full_path
    raise FileNotFoundError(f"Configuration file '{filename}' not found.")
