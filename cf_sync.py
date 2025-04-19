#!/usr/bin/env python3
# /root/cf_Rules/cf_sync.py

import requests
import socket
import ipaddress
import json
import os
import datetime

CONFIG_FILE = "/root/cf_Rules/cf_config.py"
LOG_FILE = "/root/cf_Rules/sync.log"

# === 日志 ===
def log(msg):
    now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, 'a') as f:
        f.write(f"{now} {msg}\n")
    print(f"{now} {msg}")

# === 加载配置 ===
def load_config():
    if not os.path.exists(CONFIG_FILE):
        log("未找到配置文件，无法运行！")
        exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

# === 域名解析 ===
def resolve_ips(domains):
    ipv4, ipv6 = set(), set()
    for domain in domains:
        try:
            for info in socket.getaddrinfo(domain, None):
                ip = info[4][0]
                if ':' in ip:
                    try:
                        network = ipaddress.IPv6Network(ip + '/64', strict=False)
                        ipv6.add(str(network))
                    except:
                        log(f"IPv6格式错误: {ip}")
                else:
                    ipv4.add(ip)
        except Exception as e:
            log(f"解析 {domain} 失败：{e}")
    return list(ipv4 | ipv6)

# === 更新WAF规则 ===
def update_waf(ips, config):
    api = f"https://api.cloudflare.com/client/v4/accounts/{config['ACCOUNT_ID']}/rulesets/{config['RULESET_ID']}/rules"

    headers = {
        "Authorization": f"Bearer {config['CF_API_TOKEN']}",
        "Content-Type": "application/json"
    }

    rule = {
        "expression": f"(http.host eq \"{config['RULE_NAME']}\" and not ip.src in {{{', '.join(ips)}}})",
        "action": "block",
        "description": "自动同步：允许解析IP访问，其余拦截"
    }

    try:
        resp = requests.put(api, headers=headers, json={"rules": [rule]})
        if resp.ok:
            log("✅ Cloudflare WAF规则已更新成功。")
        else:
            log(f"❌ 更新失败: {resp.text}")
    except Exception as e:
        log(f"请求异常: {e}")

# === 主程序 ===
def main():
    config = load_config()
    ips = resolve_ips(config['DOMAIN_NAMES'])
    log(f"本次解析共{len(ips)}个IP：{ips}")
    update_waf(ips, config)

if __name__ == '__main__':
    main()
