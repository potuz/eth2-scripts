#ETH 2.0 scripts

These are some monitoring scripts that are going to be useless for most. But since some expressed interest I am uploading them here. I didn't spend more than a couple of hours with this so take it as such. Eventually I'll actually write them as proper scripts. 

##Usage

You need to run your beacon and validator with `--log-format journald`. You can get help on each command with `-h`

* To get the status of the beacon (replace with `validator` for the validator) 
        
        $ ./log.py beacon status
        Beaconcon status:

              Service   : beacon-chain.service
              Status    : active (running)
              Since     : Mon 2020-11-30 05:59:39 -03
              Uptime    : 1 day 11h ago
              Memory    : 923.5M
              Peers     : 64

        Chain Head:

              headSlot                    : 2413
              headEpoch                   : 75
              headBlockRoot               : 0xc46ea971c7b1
              finalizedSlot               : 2336
              finalizedEpoch              : 73
              finalizedBlockRoot          : 0x8a48ca26604b
              justifiedSlot               : 2368
              justifiedEpoch              : 74
              justifiedBlockRoot          : 0xfd4486b57900
              previousJustifiedSlot       : 2336
              previousJustifiedEpoch      : 73
              previousJustifiedBlockRoot  : 0x8a48ca26604b
     
 * To get the last 13 blocks from testnet
   
		  $ ./log.py -tr 13 beacon blocks
		   Epoch      Slot  Proposer     Att  Dep Slsh           Graffiti
		    3001     96035     92266     128    0  0/0      0Nimbus/v1.0.0-3bdda3dd-stateofus
		    3001     96034     87238     120    0  0/0      0Nimbus/v1.0.0-74da6181-stateofus
		    3001     96033     86202     106    0  0/0      0Nimbus/v1.0.0-3bdda3dd-stateofus
		    3001     96032     46051      82    0  0/0      0prylabs-validator-3
		    3000     96031     89406     102    0  0/0      0Nimbus/v1.0.0-3e4b4946-stateofus
		    3000     96030     22441      71    0  0/0      0Lighthouse/v1.0.0-420f4c7
		    3000     96029     40156      74    0  0/0      0prylabs-validator-0
		    3000     96028     62716     128    0  0/0      0teku/v20.11.1
		    3000     96027     96508      88    0  0/0      0Nimbus/v1.0.0-74da6181-stateofus
		    3000     96026     44079      61    0  0/0      0prylabs-validator-2
		    3000     96025     46709     100    0  0/0      0prylabs-validator-3
		    3000     96024     45930      93    0  0/0      0prylabs-validator-2
		    3000     96023     37822      77    0  0/0      0Lighthouse/v1.0.0-420f4c7
		
		
		
* To get the validator performance in the last 10 attestations:

		$ ./log.py -r 10 validator performance
		   time      pubkey           epoch    source  target  head   inc. dist.
		17:06:35   0x96a6110d6751        74       ✓       ✓      ✓       1
		17:00:11   0x96a6110d6751        73       ✓       ✓      ✓       1
		16:53:51   0x96a6110d6751        72       ✓       ✓      ✓       1
		16:47:23   0x96a6110d6751        71       ✓       ✓      ✓       1
		16:41:03   0x96a6110d6751        70       ✓       ✓      ✓       1
		16:34:35   0x96a6110d6751        69       ✓       ✓      ✓       1
		16:28:11   0x96a6110d6751        68       ✓       ✓      ✓       1
		16:21:47   0x96a6110d6751        67       ✓       ✓      ✓       1
		16:15:23   0x96a6110d6751        66       ✓       ✓      ✓       1
		16:08:59   0x96a6110d6751        65       ✓       ✓      ✓       1