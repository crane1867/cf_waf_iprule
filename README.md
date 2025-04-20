🌐 Cloudflare WAF 域名解析ip,自动同步WAF自定义规则。
自动解析指定域名的IP，并同步更新到 Cloudflare 的 WAF 自定义规则，实现：

💡仅允许解析出的最新IP访问指定域名

🚫所有其他IP一律拦截
```
wget -O /root/install_cfwaf.sh https://raw.githubusercontent.com/crane1867/cf_waf_iprule/main/install_cfwaf.sh && chmod +x /root/install_cfwaf.sh && /root/install_cfwaf.sh
```
