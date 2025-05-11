#!/usr/bin/env python3
# /root/cf_Rules/cf_sync.py

import requests
import socket
# import ipaddress # ipaddress 库在当前脚本中似乎未被直接使用，如果确实不需要可以考虑移除
import json
import os
import datetime

CONFIG_FILE = "/root/cf_Rules/cf_config.json"
LOG_FILE = "/root/cf_Rules/sync.log"

# === Telegram 通知函数 ===
def send_telegram_message(bot_token, chat_id, message):
    if not bot_token or not chat_id:
        log("🔶 Telegram Bot Token 或 Chat ID 未配置，无法发送通知。")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown' # 或者 'HTML'，根据消息内容选择
    }
    try:
        response = requests.post(url, json=payload, timeout=10) # 设置超时
        if response.status_code == 200:
            log("✉️ Telegram 通知已发送。")
        else:
            log(f"⚠️ 发送 Telegram 通知失败: {response.status_code} - {response.text}")
    except Exception as e:
        log(f"🔥 发送 Telegram 通知时发生错误: {e}")

def log(msg):
    now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, 'a') as f:
        f.write(f"{now} {msg}\n")
    print(f"{now} {msg}")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        log("❌ 配置文件未找到，无法运行！")
        # 尝试发送Telegram通知（如果配置了）
        # 注意：这里可能无法获取到 bot_token 和 chat_id，因为配置文件加载失败
        # 如果希望在配置文件缺失时也能尝试通知，需要硬编码或通过其他方式获取凭证
        return None # 返回 None 以便主程序处理
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
                    ipv6.add(ip)
                else:
                    ipv4.add(ip)
        except Exception as e:
            log(f"解析 {domain} 出错: {e}")
            # 可以考虑在这里也发送Telegram通知
            # config = load_config() # 需要重新加载配置以获取Telegram凭证
            # if config and config.get("TELEGRAM_BOT_TOKEN") and config.get("TELEGRAM_CHAT_ID"):
            #     send_telegram_message(config["TELEGRAM_BOT_TOKEN"], config["TELEGRAM_CHAT_ID"], f"⚠️ 解析域名 {domain} 失败: {e}")
    return list(ipv4), list(ipv6)

def get_filter_id(config):
    api_url = f"https://api.cloudflare.com/client/v4/zones/{config['ZONE_ID']}/firewall/rules/{config['RULE_ID']}"
    headers = {
        "Authorization": f"Bearer {config['CF_API_TOKEN']}",
        "Content-Type": "application/json"
    }
    bot_token = config.get("TELEGRAM_BOT_TOKEN")
    chat_id = config.get("TELEGRAM_CHAT_ID")

    try:
        resp = requests.get(api_url, headers=headers, timeout=15) # 设置超时
        if resp.status_code == 403:
            log(f"❌ 权限不足！请检查 Token 是否具备 Zone:Firewall Services:Edit 权限")
            send_telegram_message(bot_token, chat_id, "❌ Cloudflare API 权限不足！请检查 Token 是否具备 Zone:Firewall Services:Edit 权限。")
            return None
        if resp.ok:
            rule_data = resp.json()
            filter_id = rule_data['result']['filter']['id']
            log(f"✅ 获取filter.id成功：{filter_id}")
            return filter_id
        else:
            log(f"❌ 查询规则失败: {resp.status_code} - {resp.text}")
            send_telegram_message(bot_token, chat_id, f"❌ 查询 Cloudflare 规则失败: {resp.status_code} - {resp.text}")
    except requests.exceptions.RequestException as e: # 更具体的异常捕获
        log(f"⚠️ 获取filter.id时网络请求异常: {e}")
        send_telegram_message(bot_token, chat_id, f"⚠️ 获取 Cloudflare filter.id 时网络请求异常: {e}")
    except Exception as e:
        log(f"⚠️ 获取filter.id时发生未知异常: {e}")
        send_telegram_message(bot_token, chat_id, f"⚠️ 获取 Cloudflare filter.id 时发生未知异常: {e}")
    return None

def update_existing_rule(ipv4_list, ipv6_list, config, filter_id):
    headers = {
        "Authorization": f"Bearer {config['CF_API_TOKEN']}",
        "Content-Type": "application/json"
    }
    bot_token = config.get("TELEGRAM_BOT_TOKEN")
    chat_id = config.get("TELEGRAM_CHAT_ID")

    all_ips = ipv4_list + ipv6_list
    if not all_ips: # 如果没有解析到任何IP
        log("⚠️ 没有解析到任何 IP 地址，规则可能不会按预期工作。")
        send_telegram_message(bot_token, chat_id, f"⚠️ Cloudflare WAF 同步：未解析到任何 IP 地址，规则 {config['RULE_NAME']} 可能未正确更新。")
        # 根据需求决定是否继续更新一个空的IP列表或者直接返回
        # return

    items_str = " ".join(all_ips)
    expression = (
        f'(http.host eq "{config["RULE_NAME"]}" '
        f'and not ip.src in {{{items_str}}})'
    )

    log(f"DEBUG - 生成的表达式: {expression}")

    update_filter_url = f"https://api.cloudflare.com/client/v4/zones/{config['ZONE_ID']}/filters/{filter_id}"
    filter_body = {
        "id": filter_id,
        "expression": expression,
        "paused": False,
        "description": f"同步更新：允许解析IP访问 {config['RULE_NAME']}，其余拦截",
        "ref": "auto-sync-script"
    }

    try:
        f_response = requests.put(update_filter_url, headers=headers, json=filter_body, timeout=15)
        if not f_response.ok:
            log(f"❌ 更新filter表达式失败: {f_response.status_code} - {f_response.text}")
            send_telegram_message(bot_token, chat_id, f"❌ 更新 Cloudflare filter 表达式失败 (规则: {config['RULE_NAME']}): {f_response.status_code} - {f_response.text}")
            return

        rule_data = {
            "filter": {"id": filter_id},
            "action": "block", # 确保 action 与您期望的一致
            "description": f"自动同步更新规则：{config['RULE_NAME']}"
        }
        rule_url = f"https://api.cloudflare.com/client/v4/zones/{config['ZONE_ID']}/firewall/rules/{config['RULE_ID']}"
        r_response = requests.put(rule_url, headers=headers, json=rule_data, timeout=15)

        if r_response.ok:
            log("✅ Cloudflare规则已成功更新！")
            send_telegram_message(bot_token, chat_id, f"✅ Cloudflare 防火墙规则 '{config['RULE_NAME']}' 已成功更新！\nIPv4s: {len(ipv4_list)}, IPv6s: {len(ipv6_list)}")
        else:
            log(f"❌ 更新规则失败: {r_response.status_code} - {r_response.text}")
            send_telegram_message(bot_token, chat_id, f"❌ 更新 Cloudflare 规则失败 (规则: {config['RULE_NAME']}): {r_response.status_code} - {r_response.text}")
    except requests.exceptions.RequestException as e: # 更具体的异常捕获
        log(f"⚠️ 更新规则时网络请求异常: {e}")
        send_telegram_message(bot_token, chat_id, f"⚠️ 更新 Cloudflare 规则时网络请求异常 (规则: {config['RULE_NAME']}): {e}")
    except Exception as e:
        log(f"⚠️ 更新规则时出现未知异常: {e}")
        send_telegram_message(bot_token, chat_id, f"⚠️ 更新 Cloudflare 规则时出现未知异常 (规则: {config['RULE_NAME']}): {e}")

def main():
    # 在脚本开始时加载配置一次
    config = load_config()
    if not config: # 如果加载配置失败
        # 尝试发送一个通用的失败通知，但这依赖于硬编码的TG凭证或外部配置
        # send_telegram_message("HARDCODED_BOT_TOKEN", "HARDCODED_CHAT_ID", "❌ Cloudflare WAF 同步脚本启动失败：无法加载配置文件。")
        return # 退出脚本

    bot_token = config.get("TELEGRAM_BOT_TOKEN")
    chat_id = config.get("TELEGRAM_CHAT_ID")

    # 可以在脚本开始时发送一条通知
    send_telegram_message(bot_token, chat_id, f"ℹ️ Cloudflare WAF 同步脚本开始运行，目标规则: {config.get('RULE_NAME', '未知规则')}")

    ipv4, ipv6 = resolve_ips(config.get('DOMAIN_NAMES', []))
    log(f"解析完成：IPv4 {len(ipv4)} 个，IPv6 {len(ipv6)} 个")
    # 可以选择在这里发送解析结果的通知
    # send_telegram_message(bot_token, chat_id, f"🔍 IP 解析完成：\nIPv4s ({len(ipv4)}): {ipv4}\nIPv6s ({len(ipv6)}): {ipv6}")


    filter_id = get_filter_id(config)
    if filter_id:
        update_existing_rule(ipv4, ipv6, config, filter_id)
    else:
        log("❌ 无法获取filter.id，规则未更新。")
        send_telegram_message(bot_token, chat_id, f"❌ Cloudflare WAF 同步失败：无法获取 filter.id，规则 '{config.get('RULE_NAME', '未知规则')}' 未更新。")


if __name__ == '__main__':
    main()
