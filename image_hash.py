#!/usr/bin/env DYLD_FALLBACK_LIBRARY_PATH=/usr/local/lib:/usr/lib python

import os
import phash
from wand.image import Image
from tempfile import mkstemp
from sys import argv

def dct_hash(file_path):
  try:
    return phash.dct_imagehash(file_path)
  except:
    return None


def hash_image(file_path):
  if not os.path.exists(file_path):
    print("File {0} does not exist".format(file_path))
    return None

  img = Image(filename=file_path)
  if not img.alpha_channel:
    return dct_hash(file_path)

  # strip alpha channel and write to temp file before hashing
  _, without_alpha = mkstemp()
  img.alpha_channel = False
  img.save(filename=without_alpha)
  h = dct_hash(without_alpha)
  os.remove(without_alpha)
  return h



if __name__ == '__main__':
  file_path = argv[1]
  hash = hash_image(file_path)
  print('Hash of {0}: {1}'.format(file_path, hash))