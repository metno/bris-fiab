import os
import json


DEFAULT_API_KEY_FILE = '.opentopographyrc'

def find_api_key_file(filename: str=DEFAULT_API_KEY_FILE):
  # Check current working directory
  cwd_path = os.path.join(os.getcwd(), filename)
  if os.path.exists(cwd_path):
    return cwd_path
  # Check home directory
  home_path = os.path.join(os.path.expanduser('~'), filename)
  if os.path.exists(home_path):
    return home_path
  return None

def read_api_key(filepath: str|None = None) -> str:
  if filepath is None:
    filepath = find_api_key_file()
    if filepath is None:
      raise FileNotFoundError("API key file not found in current or home directory.")

  with open(filepath, 'r') as f:
    data = json.load(f)
  return data.get('api_key')
