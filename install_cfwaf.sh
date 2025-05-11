#!/bin/bash

echo "=== Cloudflare WAF 域名同步工具 安装助手 ==="
echo "💡 本程序将自动安装依赖、配置API信息、设置定时任务和快捷命令。"

# 确保目标路径存在
INSTALL_DIR="/root/cf_Rules"
mkdir -p $INSTALL_DIR

# 提示用户输入配置信息
read -p "请输入 Cloudflare API Token: " api_token
read -p "请输入 Cloudflare ZONE ID: " zone_id
read -p "请输入 Cloudflare RULE ID: " rule_id
read -p "请输入 允许访问的主域名（例如：sese.laosepie.com）: " rule_name
read -p "请输入需要同步的域名列表 (用空格隔开): " domain_input
read -p "请输入 Telegram Bot Token (可选，留空则不启用通知): " telegram_bot_token
read -p "请输入 Telegram Chat ID (可选，如果填写了Bot Token则必须填写): " telegram_chat_id

# 自动写入 JSON 配置文件
cat > $INSTALL_DIR/cf_config.json <<EOF
{
  "CF_API_TOKEN": "$api_token",
  "ZONE_ID": "$zone_id",
  "RULE_ID": "$rule_id",
  "RULE_NAME": "$rule_name",
  "DOMAIN_NAMES": [$(
    for domain in $domain_input; do
        printf '"%s",' "$domain"
    done | sed 's/,$//'
  )],
  "TELEGRAM_BOT_TOKEN": "$telegram_bot_token",
  "TELEGRAM_CHAT_ID": "$telegram_chat_id"
}
EOF

echo "✅ 配置文件已生成：$INSTALL_DIR/cf_config.json"

# 安装依赖
echo "🚀 正在安装 Python3 与 requests 库..."
if ! command -v python3 &> /dev/null || ! command -v pip3 &> /dev/null; then
    apt update && apt install -y python3 python3-pip
else
    echo "Python3 和 pip3 已安装。"
fi

if python3 -c "import requests" &> /dev/null; then
    echo "requests 库已安装。"
else
    pip3 install requests
fi


# 下载核心同步脚本 & 管理脚本
# 确保使用正确的 GitHub Raw URL
CF_SYNC_URL="https://raw.githubusercontent.com/crane1867/cf_waf_iprule/main/cf_sync.py"
CF_MANAGER_URL="https://raw.githubusercontent.com/crane1867/cf_waf_iprule/main/cf_manager.py"

echo "Downloading cf_sync.py from $CF_SYNC_URL"
if wget -O $INSTALL_DIR/cf_sync.py "$CF_SYNC_URL"; then
    echo "cf_sync.py 下载成功。"
else
    echo "❌ cf_sync.py 下载失败。请检查网络和URL。"
    exit 1
fi

echo "Downloading cf_manager.py from $CF_MANAGER_URL"
if wget -O $INSTALL_DIR/cf_manager.py "$CF_MANAGER_URL"; then
    echo "cf_manager.py 下载成功。"
else
    echo "❌ cf_manager.py 下载失败。请检查网络和URL。"
    exit 1
fi

chmod +x $INSTALL_DIR/*.py

# 快捷键设置：alias cf
BASHRC_FILE="/root/.bashrc"
ALIAS_CMD="alias cf='python3 /root/cf_Rules/cf_manager.py'"
if ! grep -qF "$ALIAS_CMD" "$BASHRC_FILE"; then
    echo "$ALIAS_CMD" >> "$BASHRC_FILE"
    # shellcheck source=/dev/null
    source "$BASHRC_FILE"  # source 通常在交互式shell中有用，脚本中可能效果有限
    echo "请运行 'source /root/.bashrc' 或重新登录以使 alias 生效。"
fi
echo "⚡️ 已设置快捷命令：cf（输入cf即可快速打开管理菜单，可能需要重新登录或 source .bashrc）"

# 添加定时任务（每5分钟同步一次）
CRON_JOB="*/5 * * * * /usr/bin/python3 $INSTALL_DIR/cf_sync.py >> $INSTALL_DIR/sync.log 2>&1"
if ! crontab -l 2>/dev/null | grep -qF "$INSTALL_DIR/cf_sync.py"; then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ 定时任务已添加，每5分钟自动同步一次。"
else
    echo "ℹ️ 定时任务已存在。"
fi

# 创建日志文件
touch $INSTALL_DIR/sync.log
echo "📝 日志文件已创建/存在：$INSTALL_DIR/sync.log"

echo "🎉 安装完成！直接输入 cf 即可管理，或等待系统自动同步！"
echo "🔔 如果您配置了Telegram通知，请确保Token和Chat ID正确，并通过管理菜单中的测试功能进行验证。"
