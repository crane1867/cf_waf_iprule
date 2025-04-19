#!/usr/bin/env python3
# /root/cf_Rules/cf_manager.py

import os
import json

# === 配置文件路径 ===
CONFIG_FILE = "/root/cf_Rules/cf_config.json"

# === 默认配置模板 ===
def create_default_config():
    return {
        "CF_API_TOKEN": "",
        "ZONE_ID": "",
        "RULE_NAME": "",
        "DOMAIN_NAMES": []
    }

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(create_default_config())
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# === 功能 ===
def edit_config():
    config = load_config()
    print("当前配置:")
    print(json.dumps(config, indent=4))
    config['CF_API_TOKEN'] = input("请输入新的CF_API_TOKEN: ").strip()
    config['ZONE_ID'] = input("请输入新的ZONE_ID: ").strip()
    config['RULE_NAME'] = input("请输入新的WAF规则名称: ").strip()
    save_config(config)
    print("配置已保存。")

def add_domain():
    config = load_config()
    domain = input("请输入要添加的域名: ").strip()
    if domain and domain not in config['DOMAIN_NAMES']:
        config['DOMAIN_NAMES'].append(domain)
        save_config(config)
        print("域名已添加。")
    else:
        print("域名已存在或输入无效。")

def remove_domain():
    config = load_config()
    domain = input("请输入要删除的域名: ").strip()
    if domain in config['DOMAIN_NAMES']:
        config['DOMAIN_NAMES'].remove(domain)
        save_config(config)
        print("域名已删除。")
    else:
        print("域名未找到。")

def uninstall():
    confirm = input("确认要卸载所有脚本和依赖吗？(yes/no): ").lower()
    if confirm == 'yes':
        # 删除crontab同步任务
        os.system("crontab -l | grep -v '/root/cf_Rules/cf_sync.py' | crontab -")
        # 删除整个脚本目录
        os.system("rm -rf /root/cf_Rules")
        # 卸载requests库
        os.system("pip3 uninstall -y requests")
        print("✅ 卸载完成，系统已清理干净。")
    else:
        print("取消卸载。")

def setup_cron():
    os.system('(crontab -l 2>/dev/null; echo "*/5 * * * * python3 /root/cf_Rules/cf_sync.py") | sort - | uniq | crontab -')
    print("✅ 定时任务已添加，每5分钟执行一次。")

def remove_cron():
    os.system("crontab -l | grep -v '/root/cf_Rules/cf_sync.py' | crontab -")
    print("✅ 定时任务已删除。")

def manual_run():
    os.system("python3 /root/cf_Rules/cf_sync.py")

def stop_run():
    os.system("crontab -l | grep -v '/root/cf_Rules/cf_sync.py' | crontab -")
    print("✅ 已停止定时同步任务。")

# === 主菜单 ===
def menu():
    while True:
        print(\"\"\" 
Cloudflare WAF自动同步 - 管理脚本
1) 修改API和配置信息
2) 添加同步域名
3) 删除同步域名
4) 安装定时任务
5) 删除定时任务
6) 手动执行同步
7) 停止同步任务
8) 卸载全部文件
9) 退出
        \"\"\")
        choice = input("请输入选项: ").strip()

        if choice == '1':
            edit_config()
        elif choice == '2':
            add_domain()
        elif choice == '3':
            remove_domain()
        elif choice == '4':
            setup_cron()
        elif choice == '5':
            remove_cron()
        elif choice == '6':
            manual_run()
        elif choice == '7':
            stop_run()
        elif choice == '8':
            uninstall()
            break
        elif choice == '9':
            break
        else:
            print("无效输入，请重新选择。")

if __name__ == "__main__":
    if not os.path.exists("/root/cf_Rules"):
        os.makedirs("/root/cf_Rules")
    menu()
