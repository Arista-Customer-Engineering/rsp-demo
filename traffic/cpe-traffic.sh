#!/bin/bash
# --------------------------------------------------------------------
# CPE subscriber traffic simulator
#
# Generates realistic application flows through the SP fabric so
# sFlow on ALPHA/BETA-EDGE-01 captures representative traffic.
#
# Each flow type uses the hostname — dnsmasq on ALPHA-DHCP resolves
# these to well-known public IPs with PTR records, so CloudVision
# shows the actual company name in sFlow analytics.
#
# Servers listening on TRAFFIC-GEN for each flow type:
#   iperf3 -s -p 443     (YouTube, Netflix, web)
#   iperf3 -s -p 80      (web browsing HTTP)
#   iperf3 -s -u -p 3074 (Xbox Live)
#   iperf3 -s -u -p 8801 (Zoom audio)
# --------------------------------------------------------------------

LOG=/var/log/cpe-traffic.log
mkdir -p /var/log
exec >> "$LOG" 2>&1

log() { echo "[$(date '+%H:%M:%S')] [traffic] $*"; }

# ------------------------------------------------------------------
# Wait for a data-plane address on eth1
# ------------------------------------------------------------------
log "Waiting for DHCPv4 on eth1..."
until ip -4 addr show eth1 2>/dev/null | grep -q 'inet '; do
    sleep 3
done
MY_IP=$(ip -4 addr show eth1 | awk '/inet /{print $2}')
log "Got address: $MY_IP"

# ------------------------------------------------------------------
# Wait for DNS + fabric routing to converge.
# Resolving netflix.com requires DNS to reach ALPHA-DHCP which
# requires the relay chain to be up — a good canary.
# ------------------------------------------------------------------
log "Waiting for routing and DNS convergence..."
until dig +short +time=3 +tries=1 netflix.com | grep -q '[0-9]'; do
    sleep 10
done
log "Convergence confirmed. Launching flow generators."

# ------------------------------------------------------------------
# Netflix — bulk streaming
# Large long-lived TCP/443, CUBIC congestion control.
# Simulates 4K ABR video: ~8 Mbps sustained.
# ------------------------------------------------------------------
(
    while true; do
        log "Netflix stream →  1.1.1.1:443 @ 8M for 60s"
        iperf3 -4 -c netflix.com -p 443 -b 8M -t 60 -C cubic 2>/dev/null
        sleep $(( RANDOM % 20 + 10 ))
    done
) &

# ------------------------------------------------------------------
# YouTube — bulk streaming
# Slightly smaller than Netflix; same port.
# Simulates HD video: ~5 Mbps, shorter segments (ABR chunks).
# ------------------------------------------------------------------
(
    while true; do
        log "YouTube stream → 8.8.8.8:443 @ 5M for 45s"
        iperf3 -4 -c youtube.com -p 443 -b 5M -t 45 -C cubic 2>/dev/null
        sleep $(( RANDOM % 30 + 15 ))
    done
) &

# ------------------------------------------------------------------
# Web browsing — real HTTP request/response (TCP/80)
# 6 parallel connections mimics a browser's concurrent object fetches.
# Random pause simulates think time between page loads.
# ------------------------------------------------------------------
(
    while true; do
        log "Web browse → 8.8.4.4:80"
        iperf3 -4 -c apple.com -p 80 -b 2M -t 4 -P 6 2>/dev/null
        sleep $(( RANDOM % 45 + 15 ))
    done
) &

# ------------------------------------------------------------------
# Bursty web — short parallel flows across multiple destinations
# High flow count, good for demonstrating flow table turnover.
# Cycles through Google, YouTube, social — common in real browsing.
# ------------------------------------------------------------------
(
    BURST_DESTS=("google.com" "youtube.com" "facebook.com" "reddit.com")
    while true; do
        log "Bursty web — ${#BURST_DESTS[@]} destinations, 4 parallel each"
        for dest in "${BURST_DESTS[@]}"; do
            iperf3 -4 -c "$dest" -p 443 -b 1M -t 3 -P 4 2>/dev/null &
        done
        wait
        sleep $(( RANDOM % 90 + 30 ))
    done
) &

# ------------------------------------------------------------------
# Discord — chat/voice app, Cloudflare-fronted
# Bursty TCP/443, smaller than the web-browsing burst set.
# ------------------------------------------------------------------
(
    while true; do
        log "Discord → 1.1.1.1:443 @ 1M for 5s"
        iperf3 -4 -c discord.com -p 443 -b 1M -t 5 -P 2 2>/dev/null
        sleep $(( RANDOM % 60 + 20 ))
    done
) &

# ------------------------------------------------------------------
# Xbox Live — UDP/3074, sustained, small frames
# 250 Kbps, 512-byte packets ≈ ~60 pps
# Simulates an active multiplayer session.
# ------------------------------------------------------------------
(
    while true; do
        log "Xbox Live → 208.67.222.222:3074 UDP @ 250K"
        iperf3 -4 -c xbox.com -u -p 3074 -b 250K -l 512 -t 120 2>/dev/null
        sleep $(( RANDOM % 60 + 30 ))
    done
) &

# ------------------------------------------------------------------
# Zoom VoIP — UDP/8801, G.711 profile
# 64 kbps codec, 20ms frames = 160 bytes/frame = 50 pps
# Two-party call: one upstream flow.
# ------------------------------------------------------------------
(
    while true; do
        log "Zoom VoIP → 9.9.9.9:8801 UDP 160B frames @ 64K"
        iperf3 -4 -c zoom.us -u -p 8801 -b 64K -l 160 -t 120 2>/dev/null
        sleep $(( RANDOM % 120 + 60 ))
    done
) &

log "All 7 flow generators running. Output: $LOG"
wait
