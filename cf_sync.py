#!/usr/bin/env python3
# /root/cf_Rules/cf_sync.py

import requests
import socket
import ipaddress
import json
import os
import datetime

CONFIG_FILE = "/root/cf_Rules/cf_config.json"
LOG_FILE = "/root/cf_Rules/sync.log"

def log(msg):
    now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, 'a') as f:
        f.write(f"{now} {msg}\n")
    print(f"{now} {msg}")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        log("❌ 配置文件未找到，无法运行！")
        exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

def resolve_ips(domains):
    ipv4, ipv6 = set(), set()
    for domain in domains:
        try:
            for info in socket.getaddrinfo(domain, None):
                ip = info[4][0]
                if ':' in ip:  # IPv6
                    try:
                        network = ipaddress.IPv6Network(ip + '/64', strict=False)
                        ipv6.add(str(network))
                    except Exception as e:
                        log(f"IPv6转换失败: {ip} -> {e}")
                else:
                    ipv4.add(ip)
        except Exception as e:
            log(f"解析 {domain} 出错: {e}")
    return list(ipv4 | ipv6)

def update_custom_rule(ips, config):
    api_url = f"https://api.cloudflare.com/client/v4/zones/{config['ZONE_ID']}/firewall/rules"

    headers = {
        "Authorization": f"Bearer {config['CF_API_TOKEN']}",
        "Content-Type": "application/json"
    }

    rule = {
        "filter": {
            "expression": f'(http.host eq "{config["RULE_NAME"]}" and not ip.src in {{{", ".join(ips)}}})',
            "paused": False,
            "description": "自动同步域名解析IP，拦截其他IP"
        },
        "action": "block",
        "description": f"自动同步更新规则（{config['RULE_NAME']}）"
    }

    try:
        response = requests.put(api_url, headers=headers, json=[rule])
        if response.ok:
            log("✅ Cloudflare 自定义规则更新成功。")
        else:
            log(f"❌ Cloudflare更新失败: {response.text}")
    except Exception as e:
        log(f"⚠️ API请求失败: {e}")

def main():
    config = load_config()
    ips = resolve_ips(config['DOMAIN_NAMES'])
    log(f"解析完成：共 {len(ips)} 个IP：{ips}")
    update_custom_rule(ips, config)

if __name__ == '__main__':
    main()
