#!/usr/bin/env DYLD_FALLBACK_LIBRARY_PATH=/usr/local/lib:/usr/lib python

import os
import argparse
import phash
import json
import ipfsApi
import requests
from urlparse import urlparse
from wand.image import Image
from tempfile import mkstemp

DEFAULT_IPFS_SERVER = '127.0.0.1'
DEFAULT_IPFS_HTTP_GATEWAY = 'http://gateway.ipfs.io'
IPFS_INDEX_PATH = '/ipns/QmRW2PTGpWk2X5sDbAvyDLV8668skcF8ADr1FcaP8VtC1q'

def dct_hash(filename):
  try:
    return phash.dct_imagehash(filename)
  except:
    return None



def hash_image(path_or_url):
  parsed = urlparse(path_or_url)
  if parsed.scheme.startswith('http'):
    raise NotImplementedError('TODO: download remote images!')

  filepath = parsed.path
  if not os.path.exists(filepath):
    print("File {0} does not exist".format(filepath))
    return None

  img = Image(filename=filepath)
  if not img.alpha_channel:
    return dct_hash(filepath)

  # strip alpha channel and write to temp file before hashing
  _, without_alpha = mkstemp()
  img.alpha_channel = False
  img.save(filename=without_alpha)
  h = dct_hash(without_alpha)
  os.remove(without_alpha)
  return h


def load_index_file(filename):
  with open(filename) as f:
    return json.load(f, encoding='utf-8')

def ipfs_fetch(ipfs_path, gateway=DEFAULT_IPFS_HTTP_GATEWAY, server=None):
  if server is not None:
    ipfs = ipfsApi.Client(server)
    return ipfs.cat(ipfs_path)

  # TODO validation of ipfs_path, better url concat
  uri = gateway + ipfs_path
  r = requests.get(uri, timeout=15)
  return r.json()

def search_index(index, img_hash, max_distance):

  hashes_with_dist = map(lambda h: (phash.hamming_distance(img_hash, int(h, 16)), h),
                         index.keys())
  in_threshold =  filter(lambda t: t[0] <= max_distance, hashes_with_dist)
  ordered = sorted(in_threshold, key=lambda t: t[0])

  return [index[key] for [_, key] in ordered]


if __name__ == '__main__':

  parser = argparse.ArgumentParser('perceptive-client')
  parser.add_argument('image', help='The path to a local image file, or an http url for a remote image')
  parser.add_argument('-d', '--distance', type=int, help='maximum distance', default=8)

  index_source = parser.add_mutually_exclusive_group()
  index_source.add_argument('-g', '--ipfs_gateway', help='Use the IPFS gateway at this URL', default=DEFAULT_IPFS_HTTP_GATEWAY)
  index_source.add_argument('-s', '--ipfs_server', help='Use IPFS server at this address')
  parser.add_argument_group(index_source)
  parser.add_argument('-l', '--local_index', help='Load index from local JSON filepath')
  args = parser.parse_args()


  h = hash_image(args.image)
  print('Searching with input image {}'.format(args.image))
  print('perceptual hash: {:0x}'.format(h))

  if args.local_index is not None:
    idx = load_index_file(args.local_index)
  else:
    idx = ipfs_fetch(IPFS_INDEX_PATH, gateway=args.ipfs_gateway, server=args.ipfs_server)

  res = search_index(idx, h, args.distance)
  if len(res) == 0:
    print('No metadata known for {}'.format(args.image))
  else:
    meta_hash = res[0]
    print('Fetching metadata from /ipfs/{}'.format(meta_hash))
    meta = ipfs_fetch(meta_hash, gateway=args.ipfs_gateway, server=args.ipfs_server)
    print(json.dumps(meta, indent=2))
