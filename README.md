# perceptive-client

Lookup image metadata locally using pHash index

## Summary

This is a [mediachain](https://medium.com/mine-labs/mediachain-483f49cbe37a)
demo that -- given an image -- will look up its metadata as stored on IPFS. For
the purposes of this demo, image reverse lookup is facilitated by an index
calculated with the [pHash](http://phash.org/) perceptual hashing algorithm and
published to a known [IPNS](https://github.com/ipfs/examples/tree/master/examples/ipns) address.

## Requirements

### Mac OS X

`brew install imagemagick phash`

Install IPFS from source: https://github.com/ipfs/go-ipfs#build-from-source

### Ubuntu

`sudo apt-get install libmagickwand-dev imagemagick`

Compile & install pHash from http://phash.org/download/

Install IPFS from source: https://github.com/ipfs/go-ipfs#build-from-source

**Mac OS X**

`brew install imagemagick phash`

## Usage

```bash
usage: perceptive-client [-h] [-d DISTANCE] [-g IPFS_GATEWAY | -s IPFS_SERVER]
                         [-l LOCAL_INDEX]
                         image
```

Some usage notes:

When using the `-s` option, specify only the IPv4 address of the server.
Furthermore, when using the `-s` option (recommended), you should run a local
IPFS daemon with the command `ipfs daemon`.
