#!/usr/bin/env python

from eth2spec.phase0 import spec
import requests
import json
import sys, getopt
import base64

#The base address of the beacon-node
base_url = 'http://localhost:3501/eth/v1alpha1/'

#Prysm's API calls
state_endpoint = "debug/state"
chainhead_endpoint = "beacon/chainhead"


def report_voting(slot):
    query = "?slot="+str(slot)
    state_resp = requests.get(base_url+state_endpoint+query)
    data = state_resp.content.decode()
    encoded = json.loads(data)["encoded"]
    ssz_bytes = base64.b64decode(encoded)
    beacon_state = spec.BeaconState.decode_bytes(ssz_bytes)

    voting_dict = {}
    for vote in beacon_state.eth1_data_votes:
        voting_dict[vote.block_hash] = voting_dict.get(vote.block_hash,0)+1

    period_start = slot - slot % int(spec.EPOCHS_PER_ETH1_VOTING_PERIOD * spec.SLOTS_PER_EPOCH)
    period_end = period_start + int(spec.EPOCHS_PER_ETH1_VOTING_PERIOD * spec.SLOTS_PER_EPOCH)
    print("Voting summary for slot: %d\nVoting period starts:%d  ends:%d"
          % (slot, period_start, period_end))
    for hash,count in voting_dict.items():
        print("{} : {}".format(hash,count))

def main(argv):
    progname = argv.pop(0)
    usage_message = "Usage: "+progname+" [options]\n\n"+\
                    "    OPTIONS:\n\n"+\
                    "      -s, --slot : Either a slot number or one of "+\
                    "'finalized', 'head', 'justified' (default: 'head')\n\n"+\
                    "      -h, --help : Print this message.\n"

    slot_id = -1
    #parse command line
    try:
        opts, args = getopt.getopt(argv, "hs:", ["slot=","help"])
    except getopt.GetoptError:
        print (usage_message)
        sys.exit(2)
    for opt,arg in opts:
        if opt in ('-h', "--help"):
            print(usage_message)
            sys.exit()
        elif opt in ("-s", "--slot"):
            slot_id = arg

    #Get chainhead
    response = requests.get(base_url+chainhead_endpoint)
    data = response.content.decode()
    chainhead = json.loads(data)

    if slot_id == -1 or slot_id == "head":
        slot = int(chainhead['headSlot'])
    elif slot_id == "finalized":
        slot = int(chainhead['finalizedSlot'])
    elif slot_id == "justified":
        slot = int(chainhead['justifiedSlot'])
    else:
        try:
            slot = int(slot_id)
        except ValueError:
            print("<slot> has to be either an integer, or one of 'finalized', 'head' or 'justified'")
            sys.exit(2)

        if slot > int(chainhead['headSlot']):
            print ("slot is in the future")
            sys.exit(1)

    report_voting(slot)

if __name__  == "__main__":
    main(sys.argv)
