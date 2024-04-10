import asyncio
import logging
import os
import re
import socket
import time
import subprocess
from rcon.source import rcon


LGSM_PATH = '/home/csgoserver/lgsm/config-lgsm/csgoserver/'
CFG_PATH = '/home/csgoserver/serverfiles/csgo/cfg/'

# 设置为 True 可以显示在线玩家名
SHOW_PLAYER_NAMES = True

logger = logging.getLogger(__name__)

def read_servers_port() -> dict:
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} 正在获取读取服务器端口')
    server_dict = {}
    matching_files = [file for file in os.listdir(LGSM_PATH) if file.startswith('csgoserver')]
    for filename in matching_files:
        filepath = os.path.join(LGSM_PATH, filename)
        with open(filepath, 'r') as file:
            for line in file:
                if line.strip().startswith('port='):
                    port_value = line.strip().split('=')[1].strip('"')
                    server_name = filename.split('.')[0]
                    server_dict[server_name] = {'address': ('127.0.0.1', int(port_value))}
    return server_dict


def read_rcon_password(server_dict: dict) -> dict:
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} 正在获取读取服务器rcon密码')
    matching_files = [file for file in os.listdir(CFG_PATH) if file.startswith('csgoserver') and file.endswith('.cfg')]
    for filename in matching_files:
        filepath = os.path.join(CFG_PATH, filename)
        with open(filepath, 'r') as file:
            for line in file:
                if line.strip().startswith('rcon_password'):
                    rcon_password = line.strip().split('"')[1]
                    server_name = filename.split('.')[0]
                    if server_name in server_dict:
                        server_dict[server_name]['rcon_password'] = rcon_password
    return server_dict


async def send_rcon_async(address: tuple, command, *args, password):
    ip, port = address
    try:
        response = await rcon(command, *args, host=ip, port=port, passwd=password, timeout=2)
        return response
    except socket.timeout:
        logger.info(f"querying {address} timeout")
        return None
    except ConnectionRefusedError:
        logger.info(f"Connection refused when querying {address}")
        return None
    

async def rcon_server_status(address: tuple, password):
    response = await send_rcon_async(address, 'status', password=password)
    if response:
        status_data = parse_status_string(response)
        status_data['address'] = f"{address[0]}:{address[1]}"
        return status_data
    else:
        return None


async def rcon_servers_info(servers: dict):
    tasks = [(server, rcon_server_status(info['address'], info['rcon_password'])) for server, info in servers.items()]
    responses = await asyncio.gather(*[task[1] for task in tasks])
    for i, response in enumerate(responses):
        servers[tasks[i][0]]['status'] = response
    return servers


def parse_status_string(status_string) -> dict:
    """
    This function parses a server status string from a Source engine game server (like CS:GO) and returns a dictionary with the following keys:
    - 'server_name': The name of the server.
    - 'version': The version of the server.
    - 'os': The operating system the server is running on.
    - 'type': The type of the server (e.g., 'community dedicated').
    - 'map': The current map on the server.
    - 'player_count': The number of human players currently on the server.
    - 'max_players': The maximum number of players that the server can accommodate.
    - 'bot_count': The number of dc_bot players currently on the server.
    - 'players': A list of dictionaries, each representing a player currently on the server. Each dictionary has the following keys:
        - 'name': The name of the player.
        - 'steamid': The Steam ID of the player.
        - 'duration': The time the player has been connected to the server.
        - 'ping': The player's ping.
        - 'loss': The player's packet loss.
        - 'state': The player's state (e.g., 'active').
        - 'rate': The player's rate.
        - 'ip': The IP address of the player.
    """
    result = {}

    match = re.search(r'hostname: (.+)', status_string)
    if match:
        result['server_name'] = match.group(1)

    match = re.search(r'version : (.+?)/', status_string)
    if match:
        result['version'] = match.group(1)

    match = re.search(r'os {6}: {2}(.+)', status_string)
    if match:
        result['os'] = match.group(1)

    match = re.search(r'type {4}: {2}(.+)', status_string)
    if match:
        result['type'] = match.group(1)

    match = re.search(r'map {5}: (.+)', status_string)
    if match:
        result['map'] = match.group(1)

    match = re.search(r'players : (\d+) humans', status_string)
    if match:
        result['player_count'] = int(match.group(1))

    match = re.search(r'players : .+ \((\d+)/', status_string)
    if match:
        result['max_players'] = int(match.group(1))

    match = re.search(r'players : .+ (\d+) bots', status_string)
    if match:
        result['bot_count'] = int(match.group(1))

    player_data = re.findall(r'#*"(.+)" (STEAM_.+?) (.+)', status_string)
    result['players'] = [
        {
            'name': name,
            'steamid': uniqueid,
            'duration': connected.split()[0],
            'ping': connected.split()[1],
            'loss': connected.split()[2],
            'state': connected.split()[3],
            'rate': connected.split()[4],
            'ip': connected.split()[5].split(':')[0]
        }
        for name, uniqueid, connected in player_data
    ]

    return result


async def restart_server(name):
    command = [f'./{name}', 'restart']
    process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    print(stdout.decode().strip())


async def main():
    server_dict = read_servers_port()
    server_dict = read_rcon_password(server_dict)
    server_dict = await rcon_servers_info(server_dict)
    tasks = []
    for name, data in server_dict.items():
        if 'status' not in data or data['status'] is None or data['status']['player_count'] == 0:
            print(f"{data.get('status', {}).get('server_name', 'Unknown server') if 'status' in data and data['status'] is not None else 'Unknown server'} 服务器为空或关闭，准备重启...")
            tasks.append(restart_server(name))
        elif data['status']['player_count'] > 0:
            print(f"{data['status']['server_name']} 服务器有 {data['status']['player_count']} 名玩家，不重启")
            if SHOW_PLAYER_NAMES:
                print('  ', end='')
                for player in data['status']['players']:
                    print(player['name'], end=' ')
                print()
    await asyncio.gather(*tasks)
    

if __name__ == '__main__':
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} 开始重启！")
    asyncio.run(main())
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} 重启完成！")
