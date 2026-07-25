#!/bin/bash
# 企业知识管理平台 — 防火墙配置
# 用法: bash /opt/enterprise-km/scripts/firewall.sh

set -e

echo "Configuring iptables firewall..."

# 清除现有规则
iptables -F
iptables -X

# 默认策略：DROP 入站，ACCEPT 出站和转发
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# 允许本地回环
iptables -A INPUT -i lo -j ACCEPT

# 允许已建立的连接
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# SSH (22)
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# HTTP/HTTPS (nginx)
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 内网服务（仅 192.168.66.0/24 可访问）
iptables -A INPUT -p tcp -s 192.168.66.0/24 --dport 5055 -j ACCEPT
iptables -A INPUT -p tcp -s 192.168.66.0/24 --dport 5056 -j ACCEPT
iptables -A INPUT -p tcp -s 192.168.66.0/24 --dport 5057 -j ACCEPT
iptables -A INPUT -p tcp -s 192.168.66.0/24 --dport 8000 -j ACCEPT
iptables -A INPUT -p tcp -s 192.168.66.0/24 --dport 9000 -j ACCEPT
iptables -A INPUT -p tcp -s 192.168.66.0/24 --dport 9001 -j ACCEPT

# Docker 转发规则
iptables -A FORWARD -i docker0 -o docker0 -j ACCEPT
iptables -A FORWARD -i docker0 ! -o docker0 -j ACCEPT
iptables -A FORWARD -o docker0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# 保存规则
if command -v iptables-save &>/dev/null; then
    mkdir -p /etc/iptables
    iptables-save > /etc/iptables/rules.v4
    echo "Rules saved to /etc/iptables/rules.v4"
fi

echo "Firewall configured:"
iptables -L -n -v | head -20
