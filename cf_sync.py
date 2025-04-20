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
    ipv4 = set()
    ipv6 = set()
    for domain in domains:
        try:
            for info in socket.getaddrinfo(domain, None):
                ip = info[4][0]
                if ':' in ip:
                    ipv6.add(ip)  # 保留原始 IPv6 地址
                else:
                    ipv4.add(ip)
        except Exception as e:
            log(f"解析 {domain} 出错: {e}")
    return list(ipv4), list(ipv6)  # 返回分离的列表

def get_filter_id(config):
    api_url = f"https://api.cloudflare.com/client/v4/zones/{config['ZONE_ID']}/firewall/rules/{config['RULE_ID']}"
    headers = {
        "Authorization": f"Bearer {config['CF_API_TOKEN']}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(api_url, headers=headers)
        # 在 get_filter_id() 函数增加权限校验
        if resp.status_code == 403:
            log(f"❌ 权限不足！请检查 Token 是否具备 Zone:Firewall Services:Edit 权限")
            return None
        if resp.ok:
            rule_data = resp.json()
            filter_id = rule_data['result']['filter']['id']
            log(f"✅ 获取filter.id成功：{filter_id}")
            return filter_id
        else:
            log(f"❌ 查询规则失败: {resp.text}")
    except Exception as e:
        log(f"⚠️ 获取filter.id时异常: {e}")
    return None

def update_existing_rule(ipv4_list, ipv6_list, config, filter_id):
    headers = {
        "Authorization": f"Bearer {config['CF_API_TOKEN']}",
        "Content-Type": "application/json"
    }

    all_ips = ipv4_list + ipv6_list
    items_str = " ".join(all_ips)
    expression = (
        f'(http.host eq "{config["RULE_NAME"]}" '
        f'and not ip.src in {{{items_str}}})'
    )

    # === 添加调试日志 ===
    log(f"DEBUG - 生成的表达式: {expression}")

    # 更新 filter 内容
    update_filter_url = f"https://api.cloudflare.com/client/v4/zones/{config['ZONE_ID']}/filters/{filter_id}"
    filter_body = {
        "id": filter_id,
        "expression": expression,
        "paused": False,
        "description": f"同步更新：允许解析IP访问 {config['RULE_NAME']}，其余拦截",
        "ref": "auto-sync-script"
    }

    try:
        f_response = requests.put(update_filter_url, headers=headers, json=filter_body)
        if not f_response.ok:
            log(f"❌ 更新filter表达式失败: {f_response.text}")
            return

         # === 更新 Rule ===
        rule_data = {
            "filter": {"id": filter_id},
            "action": "block",
            "description": f"自动同步更新规则：{config['RULE_NAME']}"
        }
        # 正确定义 Rule 更新 URL
        rule_url = f"https://api.cloudflare.com/client/v4/zones/{config['ZONE_ID']}/firewall/rules/{config['RULE_ID']}"
        r_response = requests.put(rule_url, headers=headers, json=rule_data)
        
        if r_response.ok:
            log("✅ Cloudflare规则已成功更新！")
        else:
            log(f"❌ 更新规则失败: {r_response.text}")
    except Exception as e:
        log(f"⚠️ 更新规则时出现异常: {e}")

def main():
    config = load_config()
    ipv4, ipv6 = resolve_ips(config['DOMAIN_NAMES'])  # 获取分离的列表
    log(f"解析完成：IPv4 {len(ipv4)} 个，IPv6 {len(ipv6)} 个")

    filter_id = get_filter_id(config)
    if filter_id:
        update_existing_rule(ipv4, ipv6, config, filter_id)
    else:
        log("❌ 无法获取filter.id，规则未更新。")
           

if __name__ == '__main__':
    main()
