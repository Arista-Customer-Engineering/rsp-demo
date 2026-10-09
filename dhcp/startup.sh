#!/bin/bash
set -e

# -------------------------------------------------------------------
# Configure the data-plane interface facing ALPHA-PE-03.
# Matches the intended EOS config on the former cEOS ALPHA-DHCP node:
#   interface Ethernet1  ->  ip address 192.168.100.10/24
#   ip route 0.0.0.0/0 192.168.100.1
# ALPHA-PE-03 is expected to hold 192.168.100.1 on its side.
# -------------------------------------------------------------------
echo "[ALPHA-DHCP] Waiting for eth1 ..."
until ip link show eth1 &>/dev/null; do sleep 1; done
echo 0 > /proc/sys/net/ipv6/conf/eth1/accept_dad
ip link set eth1 up
echo "[ALPHA-DHCP] Waiting for carrier on eth1 ..."
until ip link show eth1 | grep -q "state UP"; do sleep 1; done
ip link set eth1 down && ip link set eth1 up
sleep 1
echo "[ALPHA-DHCP] Configuring eth1 ..."
ip addr replace 192.168.100.10/24        dev eth1
ip addr replace 2001:db8:8000:2::100/64  dev eth1
ip route    replace default via 192.168.100.1       dev eth1
ip -6 route replace default via 2001:db8:8000:2::1  dev eth1

echo "[ALPHA-DHCP] Starting dnsmasq..."
dnsmasq --conf-file=/etc/dnsmasq.conf &

echo "[ALPHA-DHCP] Starting Kea DHCPv4..."
kea-dhcp4 -c /etc/kea/kea-dhcp4.conf &

echo "[ALPHA-DHCP] Waiting for global IPv6 address on eth1..."
until ip -6 addr show dev eth1 scope global | grep -q "preferred"; do sleep 1; done
echo "[ALPHA-DHCP] Starting Kea DHCPv6..."
kea-dhcp6 -c /etc/kea/kea-dhcp6.conf &

# Keep container alive
wait
