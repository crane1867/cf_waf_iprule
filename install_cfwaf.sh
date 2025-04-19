#!/bin/bash

echo "=== Cloudflare WAF 域名同步工具 安装助手 ==="
echo "💡 本程序将自动安装依赖、配置API信息、设置定时任务和快捷命令。"

# 确保路径正确
INSTALL_DIR="/root/cf_Rules"
mkdir -p $INSTALL_DIR

# 提示输入配置信息
read -p "请输入 Cloudflare API Token: " api_token
read -p "请输入 Cloudflare Account ID: " account_id
read -p "请输入 Cloudflare WAF Ruleset ID: " ruleset_id
read -p "请输入 允许访问的主域名（如：cjpnz.581404.xyz）: " rule_name
read -p "请输入需要同步的域名列表 (用空格隔开): " domain_input

# 格式化域名列表
domains=$(echo $domain_input | sed "s/ /', '/g")
domain_array="['$domains']"

# 写入配置文件
cat > $INSTALL_DIR/cf_config.py <<EOF
CF_API_TOKEN = '$api_token'
ACCOUNT_ID = '$account_id'
RULESET_ID = '$ruleset_id'
RULE_NAME = '$rule_name'
DOMAIN_NAMES = $domain_array
EOF

echo "✅ 配置文件已生成：$INSTALL_DIR/cf_config.py"

# 自动安装依赖
echo "🚀 正在安装 Python3 和 requests 库..."
apt update && apt install -y python3 python3-pip
pip3 install requests --break-system-packages

# 下载核心脚本（从你的GitHub替换链接）
wget -O $INSTALL_DIR/cf_sync.py https://raw.githubusercontent.com/crane1867/cf_waf_iprule/main/cf_sync.py
wget -O $INSTALL_DIR/cf_manager.py https://raw.githubusercontent.com//crane1867/cf_waf_iprule/main/cf_manager.py
wget -O $INSTALL_DIR/sync.log https://raw.githubusercontent.com//crane1867/cf_waf_iprule/main/sync.log

chmod +x $INSTALL_DIR/*.py

# 设置快捷命令 cf
if ! grep -q "alias cf=" /root/.bashrc; then
    echo "alias cf='python3 $INSTALL_DIR/cf_manager.py'" >> /root/.bashrc
    source /root/.bashrc
fi
echo "⚡️ 已设置快捷命令：cf（输入cf即可打开管理菜单）"

# 添加定时任务
if ! crontab -l 2>/dev/null | grep -q 'cf_sync.py'; then
    (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/bin/python3 $INSTALL_DIR/cf_sync.py >> /root/cf-waf-sync.log 2>&1") | crontab -
    echo "✅ 已添加到crontab，5分钟自动同步一次。"
fi

echo "🎉 安装完成！输入 cf 随时管理域名列表、配置和同步任务。"
