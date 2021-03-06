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

DEFAULT_IPFS_SERVER = '127.0.0.1:5001'
DEFAULT_IPFS_HTTP_GATEWAY = 'http://gateway.ipfs.io'
IPFS_INDEX_PATH = '/ipns/QmRW2PTGpWk2X5sDbAvyDLV8668skcF8ADr1FcaP8VtC1q'

class IPFSFetcher:
  """
  Fetches JSON resources from IPFS.
  Uses an IPFS API daemon or an HTTP gateway, depending on the args to init.
  """
  def __init__(self, daemon=None, gateway=None, force_gateway=False):
    """
    Create an IPFSFetcher object.
    :param daemon: ip/hostname of IPFS API daemon.  Can optionally specify port, e.g: 'localhost:5001'
    :param gateway: the URL for an HTTP gateway for IPFS.  Will be used if `daemon` is not specified.
    """

    self.force_gateway = force_gateway

    if daemon is not None:
      components = daemon.split(':')
      host = components[0]
      if len(components) < 2:
        self.api = ipfsApi.Client(host=host)
      else:
        port = int(components[1])
        self.api = ipfsApi.Client(host=host, port=port)

    if gateway is not None:
      self.gateway = gateway.rstrip('/')

    if self.api is None and self.gateway is None:
      raise AttributeError('Must provide either an ipfs daemon address or an http gateway url')


    if force_gateway or self.api is None:
      print('Using HTTP/IPFS gateway at {}'.format(self.gateway))
    else:
      # Try to get the id of the IPFS daemon to ensure it's reachable
      try:
        daemon_id = self.api.id()
        print('Using IPFS daemon at {}, id: {}'.format(daemon, daemon_id['ID']))
      except requests.exceptions.RequestException as e:
        print('Unable to connect to IPFS daemon, using HTTP gateway at {}'.format(self.gateway))
        self.api = None

  def fetch(self, path):
    if self.api is not None and not self.force_gateway:
      try:
        return self.api.cat(path)
      except requests.exceptions.RequestException:
        # fall back to HTTP gateway
        return self.fetch_via_gateway(path)

    else:
      return self.fetch_via_gateway(path)

  def fetch_via_gateway(self, path):
    if self.gateway is None:
      raise AssertionError('No IPFS gateway configured')

    if not path.startswith('/'):
      path = '/ipfs/' + path
    uri = self.gateway + path
    try:
      r = requests.get(uri, timeout=15)
      return r.json()
    except requests.exceptions.RequestException as e:
      print('Error fetching {} via IPFS gateway: {}'.format(path, e.message))

def dct_hash(filename):
  try:
    return phash.dct_imagehash(filename)
  except Exception as e:
    print('Error hashing image: {}'.format(e))
    return None

def download_to_temp_file(uri):
  """
  Download the contents of `uri` to a temporary file.
  :returns The path to the temporary file.
           The caller is responsible for deleting the file if needed.
  """
  file_handle, filename = mkstemp()
  f = os.fdopen(file_handle, 'wb')
  try:
    r = requests.get(uri, stream=True)
    for chunk in r.iter_content(chunk_size=1024):
      if chunk:
        f.write(chunk)
    f.close()
    return filename
  except requests.exceptions.RequestException as e:
    print('Error downloading image: {}'.format(e))
    f.close()
    os.remove(filename)
    return None
  except IOError as e:
    f.close()
    os.remove(filename)
    print('Error saving image: {}'.format(e))
    return None


def hash_image(path_or_url):
  """
  Get pHash dct hash of image.
  :param path_or_url: If given an http(s) url, downloads to a
                      temporary file before hashing.
  :return: perceptual hash of image file as `int`, or None on error
  """
  parsed = urlparse(path_or_url)
  if parsed.scheme.startswith('http'):
    print('Fetching remote image from {}'.format(path_or_url))
    temp_filename = download_to_temp_file(path_or_url)
    h = hash_image_file(temp_filename)
    os.remove(temp_filename)
    return h
  else:
    return hash_image_file(parsed.path)

def hash_image_file(filepath):
  """
  Get pHash dct hash of local image file.
  :param filepath: path to image file
  :return: perceptual hash of image file, or None on error
  """
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
  """
  Load search index from a local json file
  :param filename: - path to index file
  :return: - parsed index as python dict
  """
  with open(filename) as f:
    return json.load(f, encoding='utf-8')


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
  ipfs_interface = parser.add_mutually_exclusive_group()
  ipfs_interface.add_argument('-g', '--ipfs_gateway',
                              nargs='?',
                              const=DEFAULT_IPFS_HTTP_GATEWAY,
                              help='Use the IPFS gateway at this URL')
  ipfs_interface.add_argument('-s', '--ipfs_server',
                      help="""Use IPFS server at this address.
                            Accepts ip or hostname with optional port, e.g: 127.0.0.1:5001""")
  parser.add_argument_group(ipfs_interface)
  parser.add_argument('-l', '--local_index', help='Load index from local JSON filepath')
  args = parser.parse_args()


  h = hash_image(args.image)
  print('Searching with input image {}'.format(args.image))
  print('perceptual hash: {:0x}'.format(h))

  gateway = args.ipfs_gateway or DEFAULT_IPFS_HTTP_GATEWAY
  daemon = args.ipfs_server or DEFAULT_IPFS_SERVER
  force_gateway = (args.ipfs_gateway is not None)
  fetcher = IPFSFetcher(gateway=gateway, daemon=daemon, force_gateway=force_gateway)

  if args.local_index is not None:
    print('Loading search index from local file {}'.format(args.local_index))
    idx = load_index_file(args.local_index)
  else:
    print('Resolving and downloading search index (this may take a second)...')
    idx = fetcher.fetch(IPFS_INDEX_PATH)

  if idx is None:
    print('Unable to fetch search index :(')
    exit(1)

  res = search_index(idx, h, args.distance)
  if len(res) == 0:
    print('No metadata known for {}'.format(args.image))
  else:
    meta_hash = res[0]
    print('Fetching metadata from /ipfs/{}'.format(meta_hash))
    meta = fetcher.fetch(meta_hash)
    print(json.dumps(meta, indent=2))
