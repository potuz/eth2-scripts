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
from systemd import journal
from datetime import datetime

beacon_service = "beacon-chain.service"
genesis = 1606824023

def main(argv):
    j = journal.Reader()
    j.log_level(journal.LOG_INFO)
    j.add_match(_SYSTEMD_UNIT=beacon_service)
    j.add_match(MESSAGE="Synced new block")
    j.add_match(SLOT=int(argv[1]))
    msg = j.get_next()
    ts = msg['_SOURCE_REALTIME_TIMESTAMP']
    tg = datetime.fromtimestamp(genesis)
    delta = ts - tg
    print("Delay: {} seconds".format(delta.total_seconds()-12*int(argv[1])))

if __name__  == "__main__":
    main(sys.argv)
