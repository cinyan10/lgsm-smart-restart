#!/bin/bash

python3 /path/to/your/1.py > /path/to/your/text.txt

current_date_time=$(date '+%Y-%m-%d-%H-%M-%S')

mv /home/csgo/log/server_reboot/text.txt /home/csgo/log/server_reboot/reboot-${current_date_time}.txt
