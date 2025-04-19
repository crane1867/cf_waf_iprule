#!/usr/bin/env python3

import requests
import json

# === 用户自定义 ===
CF_API_TOKEN = "你的API Token"
ZONE_ID = "你的Zone ID"

def check_token():
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}"

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✅ Token有效，且具有Zone访问权限：{data['result']['name']}")
            else:
                print(f"❌ Token存在，但查询失败：{data['errors']}")
        elif response.status_code == 403:
            print("❌ Token无权限访问这个Zone（权限不足）")
        elif response.status_code == 401:
            print("❌ Token无效（认证失败）")
        else:
            print(f"⚠️ 未知错误：HTTP {response.status_code}，返回：{response.text}")
    except Exception as e:
        print(f"⚠️ 请求失败：{e}")

if __name__ == "__main__":
    check_token()
