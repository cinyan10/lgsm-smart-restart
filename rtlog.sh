#!/bin/bash

python3 /home/csgo/a2s_restart.py > /home/csgo/log/server_reboot/text.tx

current_date_time=$(date '+%Y-%m-%d-%H-%M-%S')

mv /home/csgo/log/server_reboot/text.txt /home/csgo/log/server_reboot/reboot-${current_date_time}.txt
