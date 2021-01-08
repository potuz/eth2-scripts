#!/usr/bin/env python
#******************************************************************************
#       Copyright (C) 2020 potuz <potuz@potuz.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  http://www.gnu.org/licenses/
#*****************************************************************************


import sys
import argparse
import requests
import json
import base64
from systemd import journal
from datetime import datetime as dt
from time import time as Time
import subprocess, re

## Adjust these to your need

#  The API endpoints
base_url = "http://localhost:"
endpoint_prefix = "/eth/v1alpha1"
chainhead_endpoint = "/beacon/chainhead"
peers_endpoint = "/node/peers"
blocks_endpoint = "/beacon/blocks"
stream_blocks_endpoint = "/beacon/blocks/stream"
participation_endpoint = "/validators/participation"
testnet_port = "3501"
mainnet_port = "3500"

# The systemd services
validator_service = "validator.service"
validator_testnet_service = "validator-goerli.service"
beacon_service = "beacon-chain.service"
beacon_testnet_service = "beacon-chain-goerli.service"
geth_service = "geth.service"
geth_testnet_service = "geth-goerli.service"

genesis_testnet = 1605700807
genesis_mainnet = 1606824023

def read_status(service):
    p =  subprocess.Popen(["systemctl", "status",  service], stdout=subprocess.PIPE)
    (output, err) = p.communicate()
    output = output.decode('utf-8')

    service_regx = r"Loaded:.*\/(.*service);"
    status_regx= r"Active:(.*) since (.*);(.*)"
    memory_regx= r"Memory:(.*)"
    service_status = {}
    for line in output.splitlines():
        service_search = re.search(service_regx, line)
        status_search = re.search(status_regx, line)
        memory_search = re.search(memory_regx, line)

        if service_search:
            service_status['Service'] = service_search.group(1)
            #print("service:", service)

        elif status_search:
            service_status['Status'] = status_search.group(1).strip()
            #print("status:", status.strip())
            service_status['Since'] = status_search.group(2).strip()
            #print("since:", since.strip())
            service_status['Uptime'] = status_search.group(3).strip()
            #print("uptime:", uptime.strip())
        elif memory_search:
            service_status['Memory'] = memory_search.group(1).strip()

    return service_status

def balances(j, td=None):
    bals = {}
    if not td:
        j.seek_tail()
    else:
        j.seek_realtime(td)

    while True:
        msg = j.get_previous()
        if not msg:
            break
        pubkey = msg['PUBKEY']
        if pubkey in bals:
            break
        try: 
            balance = float(msg['NEWBALANCE'])
        except ValueError:
            balance = 0
        bals[pubkey] = balance
    return bals

def log_validator(args):
    today = dt.today().date()
    if args.testnet:
        service = validator_testnet_service
        genesis = genesis_testnet
    else:
        service = validator_service
        genesis = genesis_mainnet

    tg = dt.fromtimestamp(genesis)

    j = journal.Reader()
    j.log_level(journal.LOG_INFO)
    j.add_match(_SYSTEMD_UNIT=service)

    if args.subcommand == "schedule":
        j.add_match(MESSAGE="Proposal schedule")
        j.add_match(MESSAGE="Attestation schedule")
        j.seek_tail()
        i = 0
        print("Duty                     Pubkey        Slot     Epoch")
        while i < args.rows:
            msg = j.get_previous()
            if not msg:
                i += 1
                continue
            slot = int(msg['SLOT'])
            if args.epoch and slot > args.epoch * 32:
                continue
            if msg['MESSAGE']=="Attestation schedule":
                duty = "Attestation" 
                pubkeys = [k for k in msg['PUBKEYS'][1:-1].split()]
            else:
                duty = "Proposal"
                pubkeys = [msg['PUBKEY'],]
            for key in pubkeys:
                print("{:<20} {}   {:<8} {:>6}".format(duty, key, slot, slot // 32))
            i += 1

    if args.subcommand == "proposals":
        j.add_match(MESSAGE="Submitted new block")
        j.seek_tail()
        print("  Date        Slot        Pubkey            Root           Atts   Deps      Graffiti")
        j.seek_tail()
        i = 0
        while i < args.rows:
            msg = j.get_previous()
            if not msg:
                i += 1
                continue
            slot = int(msg['SLOT'])
            if args.epoch and slot > args.epoch * 32:
                continue
            root = msg['BLOCKROOT']
            pubkey = msg['PUBKEY']
            atts = msg['NUMATTESTATIONS']
            deps = msg['NUMDEPOSITS']
            #graffiti_temp = base64.b64decode(msg["GRAFFITI"])
            graffiti = msg['GRAFFITI']
#            graffiti = graffiti_temp.decode('utf8').replace("\00", " ")
            datetime = msg['_SOURCE_REALTIME_TIMESTAMP']
            if datetime.date() >= today:
                time = datetime.strftime("%H:%M:%S")
            else:
                time = datetime.strftime("%D")

            print("{}   {:>7}    {}   {}       {:>2}     {:>2}       {}".format(time, slot, pubkey, root,
                                                        atts, deps, graffiti))

            i += 1

    if args.subcommand == "attestations":
        j.add_match(MESSAGE="Submitted new attestations")
        j.seek_tail()
        print("  time      source   target     slot    index  agr  committee      sourceroot       targetroot       beaconroot{ts}".format(ts = "      delay" if args.timestamp else ""))
        i = 0
        while i < args.rows:
            msg = j.get_previous()
            if not msg:
                i += 1
                continue
            slot = int(msg['SLOT'])
            if args.epoch and slot > args.epoch * 32:
                continue

            aggidx = [int(m) for m in msg["AGGREGATORINDICES"][1:-1].split()]
            attidx = [int(m) for m in msg["ATTESTERINDICES"][1:-1].split()]
            source = int(msg['SOURCEEPOCH'])
            target = int(msg['TARGETEPOCH'])
            commitee = int(msg['COMMITTEEINDEX'])
            targetroot = msg['TARGETROOT']
            sourceroot = msg['SOURCEROOT']
            beaconroot = msg['BEACONBLOCKROOT']
            datetime = msg['_SOURCE_REALTIME_TIMESTAMP']
            if args.timestamp:
                delta = datetime - tg
                delay = delta.total_seconds() - 12*slot
                
            if datetime.date() >= today:
                time = datetime.strftime("%H:%M:%S")
            else:
                time = datetime.strftime("%D")

            for idx in attidx:
                print("{} {:>8} {:>8} {:>9} {:>8}   {agr} {:>8}       {}   {}   {}{ts}".format(
                      time, source, target, slot, idx, 
                      commitee, sourceroot,
                      targetroot, beaconroot, agr='✓' if idx in aggidx else ' ',
                      ts="   {:.4f}".format(delay) if args.timestamp else ""))
            i += 1

    if args.subcommand == "performance":
        j.add_match(MESSAGE="Previous epoch voting summary")
        j.seek_tail() 
        print("   time      pubkey           epoch    source  target  head   inc. dist.   Balance Chg.")
        i = 0
        last_epoch = args.epoch
        while i < args.rows:
            msg = j.get_previous()
            if not msg:
                i += 1
                continue
            epoch = int(msg['EPOCH'])
            if args.epoch and epoch > args.epoch:
                continue
            if last_epoch and epoch < last_epoch - 1:
                for lostepoch in range(last_epoch - epoch - 1):
                    i += 1
                    print("{}   {}  {:>8}     {:^5}   {:^5}  {:^5} {:>5}".format(
                          time, pubkey, last_epoch - lostepoch -1,"⨯" , "⨯", "⨯", "miss"))

            inclusion = int(msg['INCLUSIONDISTANCE'])
            if msg['CORRECTLYVOTEDSOURCE'] == "true":
                source = "✓"
            else:
                source = "⨯"
            if msg['CORRECTLYVOTEDTARGET'] == "true":
                target = "✓"
            else:
                target = "⨯"
            if msg['CORRECTLYVOTEDHEAD'] == "true":
                head = "✓"
            else:
                head = "⨯"
            pubkey = msg['PUBKEY']
            oldbal = float(msg['OLDBALANCE'])
            newbal = float(msg['NEWBALANCE'])
            balchg = int((newbal-oldbal)*10**9)
            datetime = msg['_SOURCE_REALTIME_TIMESTAMP']
            if datetime.date() >= today:
                time = datetime.strftime("%H:%M:%S")
            else:
                time = datetime.strftime("%D")
            if inclusion < 33:
                print("{}   {}  {:>8}     {:^5}   {:^5}  {:^5} {:>5}       {:>9}".format(
                      time, pubkey, epoch, source, target, head, inclusion, balchg))
            else:
                print("{}   {}  {:>8}     {:^5}   {:^5}  {:^5} {:>5}       {:>9}".format(
                      time, pubkey, epoch, source, target, head, "miss", balchg))
            last_epoch = epoch
            i += 1

    if args.subcommand == "status":
        print("Validator summary since last launch:\n")
        resp = read_status(service)
        for key in resp:
            print('{:<10}: {}'.format(key, resp[key]))

        j.add_match(MESSAGE="Vote summary since launch")
        j.seek_tail()
        msg = j.get_previous()
        if not msg:
            return
        source = msg['CORRECTLYVOTEDSOURCEPCT']
        target = msg['CORRECTLYVOTEDTARGETPCT']
        head = msg['CORRECTLYVOTEDHEADPCT']
        inclusion = msg['AVERAGEINCLUSIONDISTANCE']
        attinclusion = msg['ATTESTATIONSINCLUSIONPCT']
        epochs = msg['NUMBEROFEPOCHS']
        
        print("\n")
        print("Average Inclusion Distance  : {}".format(inclusion))
        print("Correctly Voted Source      : {}".format(source))
        print("Correctly Voted Target      : {}".format(target))
        print("Correctly Voted Head        : {}".format(head))
        print("Attestations Inclusion      : {}".format(attinclusion))
        print("\n")
        print("Number of Epochs running    : {}".format(epochs))

        j.flush_matches()
        j.add_match(_SYSTEMD_UNIT=service)
        j.add_match(MESSAGE="Previous epoch voting summary")
        bals_now = balances(j)
        td = Time()-3600
        bals_hour = balances(j, td)
        td = td - 82800
        bals_day = balances(j, td)
        td = td - 86400*6
        bals_week = balances(j, td)

        hourly = {pubkey: (bal - bals_hour.get(pubkey,32)) * 8760 / bals_hour.get(pubkey,32)\
                   for pubkey, bal in bals_now.items() }
        daily = {pubkey: (bal - bals_day.get(pubkey,32)) * 365 / bals_day.get(pubkey,32)\
                   for pubkey, bal in bals_now.items() }
        weekly = {pubkey: (bal - bals_week.get(pubkey,32)) * 365 / 7 / bals_week.get(pubkey,32)\
                   for pubkey, bal in bals_now.items() }

        time_fraction = 31536000 / (Time() - genesis)
        print("\n   Public Key            Balance     Hourly    Daily     Weekly")
        for pubkey,bal in bals_now.items():
            print("{:<20}{:>.9f}     {:6.2%}    {:6.2%}    {:6.2%}".format(pubkey,
                            bal, hourly[pubkey], daily[pubkey], weekly[pubkey] ))
    
        total = sum([val for (key,val) in bals_now.items()])
        total_hour = sum([ int((bal - bals_hour.get(pubkey,32))*1000000000) for pubkey, bal in bals_now.items()])
        total_day = sum([ bal - bals_day.get(pubkey,32) for pubkey,bal in bals_now.items()])
        total_week = sum([ bal - bals_week.get(pubkey,32) for pubkey,bal in bals_now.items()])
        print("{:<20}{:>.9f}     {:>}    {:>.4f}    {:>.4f}".format("Totals",
                            total, total_hour, total_day, total_week ))

def get_participation(testnet):
    if testnet:
        port = testnet_port
    else:
        port = mainnet_port
    response = requests.get(base_url+port+endpoint_prefix+participation_endpoint)
    data = response.content.decode()
    chainhead = json.loads(data)
    return chainhead['participation']['globalParticipationRate']

def get_chainhead(testnet):
    #Get chainhead
    if testnet:
        port = testnet_port
    else:
        port = mainnet_port
    response = requests.get(base_url+port+endpoint_prefix+chainhead_endpoint)
    data = response.content.decode()
    chainhead = json.loads(data)
    return chainhead

def get_peers(testnet):
    if testnet:
        port = testnet_port
    else:
        port = mainnet_port
    response = requests.get(base_url+port+endpoint_prefix+peers_endpoint)
    data = response.content.decode()
    peerlist = json.loads(data)
    peers = peerlist["peers"]
    return peers
 
def print_block(container, prev, down):
    block = container['block']['block']
    rootbytes = container.get('blockRoot', b'\00')
    root = base64.b64decode(rootbytes).hex()
    slot = int(block["slot"])
    epoch = slot // 32
    proposer = int(block["proposerIndex"])
    body = block["body"]
    graffiti_temp = base64.b64decode(body["graffiti"])
    graffiti = graffiti_temp.decode('utf8').replace("\00", " ")
    attestations = len(body["attestations"])
    deposits = len(body["deposits"])
    exits = len(body["voluntaryExits"])
    proposerSlashings = len(body["proposerSlashings"])
    attesterSlashings = len(body["attesterSlashings"])
    if down:
        while (prev > 0) and prev > (slot + 1):
            prev -= 1
            print("{:<6} {:>8}  \033[93mMISSING\033[0m".format(prev // 32, prev))
    else:
        if slot < prev:
            return
        while (prev > 0) and prev < (slot - 1):
            prev += 1
            print("{:<6} {:>8}  \033[93mMISSING\033[0m".format(prev // 32, prev))

    print("{:<6} {:>8}  {:>6}     {:>3}  {:>4}  {:>1}/{:<1}  {:>4}    {:<32}   0x{:<9}".format(epoch, slot, proposer,
                                                attestations, deposits,
                                                proposerSlashings,
                                                attesterSlashings,
                                                exits,  graffiti, root[0:9]))
    return slot


def print_epoch_blocks(epoch, testnet, rows):
    if testnet:
        port = testnet_port
    else:
        port = mainnet_port

    #Get this epoch's blocks
    query = "?epoch=%d" % (epoch)
    headResp = requests.get(base_url+port+endpoint_prefix+blocks_endpoint+query) 
    data = headResp.content.decode()
    resp_json = json.loads(data)
    containers = resp_json["blockContainers"]
    containers.reverse()

    i = rows
    slot=0
    for c in containers:
        slot = print_block(c, slot, True)
        i -= 1
        if i == 0:
            break
    return i

def stream_blocks(args):
    if args.testnet:
        port = testnet_port
    else:
        port = mainnet_port

    #Get this epoch's blocks
    req = requests.get(base_url+port+endpoint_prefix+stream_blocks_endpoint, stream=True)
    slot = 0
    for line in req.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            json_line = json.loads(decoded_line)
            block = {'block': json_line['result']}
            slot = print_block(block, slot, False)
     
def log_beacon(args):
    today = dt.today().date()
    if args.testnet:
        service = beacon_testnet_service
    else:
        service = beacon_service

    j = journal.Reader()

    if args.subcommand == "warn":
        j.log_level(journal.LOG_WARNING)
    else:
        j.log_level(journal.LOG_INFO)

    j.add_match(_SYSTEMD_UNIT=service)

    if args.subcommand == "warn":
        j.seek_tail()
        for i in range(args.rows):
            msg = j.get_previous()
            if not msg:
                continue
            message = msg['MESSAGE']
            errormsg = msg.get('ERR', '')
            if not errormsg:
                errormsg = msg.get('ERROR', '')
            if errormsg:
                errormsg = "Error :"+errormsg
            block = msg.get('BLOCKSLOT', '')
            if block:
                block = "Slot : "+block
            datetime = msg['_SOURCE_REALTIME_TIMESTAMP']
            if datetime.date() >= today:
                time = datetime.strftime("%H:%M:%S")
            else:
                time = datetime.strftime("%D")

            print("{} -- {} {} {}".format(time, message, errormsg, block))
            return
            
    if args.subcommand == "status":
        print("Beacon status:\n")
        resp = read_status(service)
        for key in resp:
            print('          {:<10}: {}'.format(key, resp[key]))

        peers = get_peers(args.testnet)
        numpeers = len([1 for m in peers if m['connectionState'] == "CONNECTED"])
        print ("          Peers     : {}".format(numpeers))
        
        particip = get_participation(args.testnet)
        print ( "          {:<10}: {:.2%}".format("Particip.", particip))
        
        print("\nChain Head:\n")
        chainhead = get_chainhead(args.testnet)
        slot = int(chainhead['headSlot'])
        slot = "{}   {:>2}/32".format(slot, slot%32)
        chainhead['headSlot'] = slot
        chainhead['headBlockRoot'] = "0x"+base64.b64decode(chainhead['headBlockRoot']).hex()[:12]
        chainhead['finalizedBlockRoot'] = "0x"+base64.b64decode(chainhead['finalizedBlockRoot']).hex()[:12]
        chainhead['justifiedBlockRoot'] = "0x"+base64.b64decode(chainhead['justifiedBlockRoot']).hex()[:12]
        chainhead['previousJustifiedBlockRoot'] = "0x"+base64.b64decode(chainhead['previousJustifiedBlockRoot']).hex()[:12]
        for key, val in chainhead.items():
            print ( "          {:<27} : {}".format(key, val))
        return

    if args.subcommand == "blocks":
        if args.stream:
            print("Epoch      Slot  Proposer    Att  Dep Slsh  Exits          Graffiti                   root") 
            stream_blocks(args)
        else:
            chainhead = get_chainhead(args.testnet)
            if args.epoch == -1:
                epoch = int(chainhead['headEpoch'])
            else:
                epoch = args.epoch
            print("Epoch      Slot  Proposer    Att  Dep Slsh  Exits           Graffiti                    root") 
            ret = args.rows
            while ret:
                ret = print_epoch_blocks(epoch, args.testnet, ret)
                epoch -= 1
            return
        
def log_geth(args):
    return 


def main(argv):
    parser = argparse.ArgumentParser(description="Important logs from ETH2",
                                    epilog="Copyright (2020) potuz@potuz.net")

    parser.add_argument('-t', '--testnet', action="store_true",
                        help="Show logs from testnet (default: False)" )

    parser.add_argument('-r', '--rows', type=int, default=24,
                        help="How many rows of data to include (default: 24)")

    subparsers = parser.add_subparsers(required=True, metavar="COMMAND")

    #The validator command arguments
    parser_validator = subparsers.add_parser("validator", help='Logs from the validator client')
    parser_validator.set_defaults(func=log_validator)
    subparser_val = parser_validator.add_subparsers(required=True, metavar="SUBCOMMAND", dest="subcommand")
    atts_parser = subparser_val.add_parser("attestations", help="Info from submitted attestations")
    atts_parser.add_argument('-e', '--epoch', type=int, default=0, 
                                help="report attestations starting from the given epoch (default: latest head")
    atts_parser.add_argument('-T', '--timestamp', action="store_true", 
                                help="report timestamps for the given attestation (default: False")

    sched_parser = subparser_val.add_parser("schedule", help="Info about validator duties")
    sched_parser.add_argument('-e', '--epoch', type=int, default=0, 
                                help="report duties starting from the given epoch (default: latest head")

    performance_parser = subparser_val.add_parser("performance", help="Performance of last few epochs")
    performance_parser.add_argument('-e', '--epoch', type=int, default=0, 
                                help="report performance starting from the given epoch (default: latest head")

    proposals_parser = subparser_val.add_parser("proposals", help="Info from submitted proposals")
    subparser_val.add_parser("status", help="Satus overview of the validator")
    proposals_parser.add_argument('-e', '--epoch', type=int, default=0, 
                                help="report proposals starting from the given epoch (default: latest head")


    #The beacon command arguments
    parser_beacon = subparsers.add_parser("beacon", help="Logs from the beacon node")
    parser_beacon.set_defaults(func=log_beacon)
    subparser_beacon = parser_beacon.add_subparsers(required=True, metavar="SUBCOMMAND", dest="subcommand")
    subparser_beacon.add_parser("status", help="Satus overview of the beacon node")
    subparser_beacon.add_parser("warn", help="Warnings from the beacon node")
    blocks_parser = subparser_beacon.add_parser(
        "blocks", help="Information about last few blocks in the beaconchain")
    blocks_parser.add_argument('-s', '--stream', action="store_true",
                                help="Stream blocks as they are seen (default: False)")
    blocks_parser.add_argument('-e', '--epoch', type=int, default=-1, 
                                help="report blocks starting from the given epoch (default: latest head")



    parser_geth = subparsers.add_parser("geth", help="Logs from geth")
    parser_geth.set_defaults(func=log_geth)
    args = parser.parse_args()
    args.func(args)

if __name__  == "__main__":
    main(sys.argv)
