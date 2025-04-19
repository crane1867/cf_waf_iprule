#!/bin/bash

echo "=== Cloudflare WAF 域名同步工具 安装助手 ==="
echo "💡 本程序将自动安装依赖、配置API信息、设置定时任务和快捷命令。"

# 确保目标路径存在
INSTALL_DIR="/root/cf_Rules"
mkdir -p $INSTALL_DIR

# 提示用户输入配置信息
read -p "请输入 Cloudflare API Token: " api_token
read -p "请输入 Cloudflare Account ID: " account_id
read -p "请输入 Cloudflare WAF Ruleset ID: " ruleset_id
read -p "请输入 允许访问的主域名（例如：cjpnz.581404.xyz）: " rule_name
read -p "请输入需要同步的域名列表 (用空格隔开): " domain_input

# 自动写入 JSON 配置文件
cat > $INSTALL_DIR/cf_config.json <<EOF
{
  "CF_API_TOKEN": "$api_token",
  "ACCOUNT_ID": "$account_id",
  "RULESET_ID": "$ruleset_id",
  "RULE_NAME": "$rule_name",
  "DOMAIN_NAMES": [$(
    for domain in $domain_input; do
        printf '"%s",' "$domain"
    done | sed 's/,$//'
  )]
}
EOF

echo "✅ 配置文件已生成：$INSTALL_DIR/cf_config.json"

# 安装依赖
echo "🚀 正在安装 Python3 与 requests 库..."
apt update && apt install -y python3 python3-pip
pip3 install requests --break-system-packages

# 下载核心同步脚本 & 管理脚本
wget -O $INSTALL_DIR/cf_sync.py https://raw.githubusercontent.com/crane1867/cf_waf_iprule/main/cf_sync.py
wget -O $INSTALL_DIR/cf_manager.py https://raw.githubusercontent.com/crane1867/cf_waf_iprule/main/cf_manager.py

chmod +x $INSTALL_DIR/*.py

# 快捷键设置：alias cf
if ! grep -q "alias cf=" /root/.bashrc; then
    echo "alias cf='python3 /root/cf_Rules/cf_manager.py'" >> /root/.bashrc
    source /root/.bashrc
fi
echo "⚡️ 已设置快捷命令：cf（输入cf即可快速打开管理菜单）"

# 添加定时任务（每5分钟同步）
if ! crontab -l 2>/dev/null | grep -q 'cf_sync.py'; then
    (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/bin/python3 /root/cf_Rules/cf_sync.py >> /root/cf_waf_sync.log 2>&1") | crontab -
    echo "✅ 定时任务已添加，5分钟自动同步一次。"
fi

echo "🎉 安装完成！直接输入 cf 即可管理，或等待系统每5分钟自动同步！"
