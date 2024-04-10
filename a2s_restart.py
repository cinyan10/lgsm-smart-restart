import asyncio

import a2s
import asyncio
import logging
import os
import time
from rcon.source import rcon

# pip3 install python-a2s

IP_ADDRESS = '填写你的服务器IP'

# LGSM 路径, CSGO服务器的话不需要动
LGSM_PATH = '/home/csgoserver/lgsm/config-lgsm/csgoserver/'

# 设置为 True 可以显示在线玩家名


logger = logging.getLogger(__name__)


def read_servers_port() -> list:
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} 正在获取读取服务器端口')
    server_list = []
    matching_files = [file for file in os.listdir(LGSM_PATH) if file.startswith('csgoserver')]
    for filename in matching_files:
        filepath = os.path.join(LGSM_PATH, filename)
        with open(filepath, 'r') as file:
            for line in file:
                if line.strip().startswith('port='):
                    port_value = line.strip().split('=')[1].strip('"')
                    server_name = filename.split('.')[0]
                    server_list.append({'name': server_name, 'address': (IP_ADDRESS, int(port_value))})
    return server_list


async def query_server_status(address: tuple):
    try:
        status = await a2s.ainfo(address)
        return {'server_name': status.server_name, 'player_count': status.player_count} 
    except asyncio.exceptions.TimeoutError:
        print(f"timeout connect to {address}")
        return {'server_name': {'服务器连接失败'}, 'player_count': None} 
    

async def query_all_servers(servers: list):
    tasks = [query_server_status(server['address']) for server in servers]
    statuses = await asyncio.gather(*tasks)
    
    for server, status in zip(servers, statuses):
        server['status'] = status

    return servers


async def restart_server(name):
    command = [f'./{name}', 'restart']
    process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    print(stdout.decode().strip())


async def main():
    servers = read_servers_port()
    servers = await query_all_servers(servers)
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} 服务器状态查询完成, 准备执行重启...')
    tasks = []
    for server in servers:
        if server['status']['player_count'] is None:
            print(f"{server['name']} 服务器连接失败，准备重启...")
            tasks.append(restart_server(server['name']))
        elif server['status']['player_count'] == 0:
            print(f"{server['status']['server_name']} 服务器为空，准备重启...")
            tasks.append(restart_server(server['name']))
        elif server['status']['player_count'] > 0:
            print(f"{server['status']['server_name']} 服务器有 {server['status']['player_count']} 名玩家，不执行重启...")
    await asyncio.gather(*tasks)
    

if __name__ == '__main__':
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} 开始执行重启脚本...')
    rs = asyncio.run(main())    
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} 重启执行完成!!!')
    