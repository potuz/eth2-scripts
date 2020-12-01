#!/usr/bin/env python

from eth2spec.phase0 import spec
import requests
import json
import sys, getopt
import base64

#The base address of the beacon-node
base_url = 'http://localhost:3500/eth/v1alpha1/'

#Prysm's API calls
blocks_endpoint = "beacon/blocks"
genesis_endpoint = "node/genesis"

def main(argv):
    query = "?genesis=1"
    state_resp = requests.get(base_url+blocks_endpoint+query)
    data = state_resp.content.decode()
    resp_json = json.loads(data)

    containers = resp_json["blockContainers"][0]
    block_container = containers["block"]
    genesis_block_root_bytes = base64.b64decode(containers["blockRoot"])
    genesis_block_root = spec.Root.decode_bytes(genesis_block_root_bytes)

    block = block_container["block"]
    genesis_state_root_bytes = base64.b64decode(block["stateRoot"])
    genesis_state_root = spec.Root.decode_bytes(genesis_state_root_bytes)

    genesis_resp = requests.get(base_url+genesis_endpoint)
    data = genesis_resp.content.decode()
    resp_json = json.loads(data)


    print("Genesis Information:")
    print("state root : {}".format(genesis_state_root))
    print("block root : {}".format(genesis_block_root))
    print("Genesis Time : {}".format(resp_json["genesisTime"]))


if __name__  == "__main__":
    main(sys.argv)
