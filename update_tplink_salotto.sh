#!/bin/bash

/home/pi/tplink-smartplug/tplink_smartplug.py -t 192.168.88.51 -j "{\"time\":{\"set_timezone\":{\"year\":$(date +%Y),\"month\":$(date +%m),\"mday\":$(date +%d),\"hour\":$(date +%H),\"min\":$(date +%M),\"sec\":$(date +%S),\"index\":41}}}"
