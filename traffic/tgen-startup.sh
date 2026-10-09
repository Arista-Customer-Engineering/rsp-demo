#!/bin/bash
# --------------------------------------------------------------------
# TRAFFIC-GEN startup script
#
# One VLAN subinterface per content provider on eth1 (TRANSIT:Ethernet4).
# Carrier routing (Arelion/Uniti/Segra) lives entirely on TRANSIT now —
# TRAFFIC-GEN only needs to know about content:
#
#   eth1         default VRF  — 198.51.100.7/31  (backward compat)
#   eth1.100     GOOGLE       — 10.255.0.7/31    AS15169
#   eth1.200     CLOUDFLARE   — 10.255.0.9/31    AS13335
#   eth1.300     NETFLIX      — 10.255.0.11/31   AS2906
#   eth1.400     XBOX         — 10.255.0.13/31
#   eth1.500     ZOOM         — 10.255.0.15/31
#
# Service IPs are bound inside per-VRF dummy interfaces so iperf3
# and HTTP servers respond correctly from within each VRF context.
# --------------------------------------------------------------------

set -e
log() { echo "[$(date '+%H:%M:%S')] [tgen] $*"; }

# ====================================================================
# eth1 parent — trunk, keep default-VRF IP for backward compat
# ====================================================================
log "Bringing up eth1 trunk (198.51.100.7/31, gw 198.51.100.6)..."
ip link set eth1 up
ip addr add 198.51.100.7/31 dev eth1 2>/dev/null || true
ip route add default via 198.51.100.6 dev eth1 2>/dev/null || true

# ====================================================================
# Linux VRFs — one per content provider (table ID matches VLAN ID)
# ====================================================================
log "Creating Linux VRFs..."
for spec in "GOOGLE:100" "CLOUDFLARE:200" "NETFLIX:300" "XBOX:400" "ZOOM:500"; do
    VRF=${spec%:*}; TABLE=${spec#*:}
    ip link add "${VRF}" type vrf table "${TABLE}" 2>/dev/null || true
    ip link set "${VRF}" up
    # Unreachable default so VRF-local traffic doesn't leak to global table
    ip route add table "${TABLE}" unreachable default metric 4278198272 2>/dev/null || true
done

# ====================================================================
# VLAN subinterfaces — assigned to their Linux VRF
# ====================================================================
log "Creating VLAN subinterfaces..."

# CPE subscriber address space (RFC 6598 CGNAT range covering every PON
# pool), TRANSIT's own internal carrier<->content-provider peering links
# (10.98.101.0/31-10.98.106.0/31, see TRANSIT.yml's Ethernet5.1xx/
# Ethernet6.1xx), the 198.51.100.0/24 point-to-point block used throughout
# the fabric for EDGE<->TRANSIT and EDGE<->CG-NAT uplinks, and the whole
# 172.16.0.0/16 fabric loopback range (Lo0 system loopbacks, Lo40 DHCP
# relay, Lo50 CG-NAT - which lives *inside* the CGNAT vrf on each PE/edge
# router and is what EOS sources locally-generated ICMP like
# TTL-exceeded from within that vrf). Each VRF's "unreachable default"
# below would otherwise blackhole replies to any of these - this punches
# the four holes each VRF needs.
CPE_AGGREGATE="100.64.0.0/10"
TRANSIT_PEERING_AGGREGATE="10.98.0.0/16"
FABRIC_P2P_AGGREGATE="198.51.100.0/24"
FABRIC_LOOPBACK_AGGREGATE="172.16.0.0/16"

setup_vlan() {
    local VLAN=$1 VRF=$2 IP=$3 TABLE=$4 TRANSIT_PEER=$5
    ip link add link eth1 name "eth1.${VLAN}" type vlan id "${VLAN}" 2>/dev/null || true
    ip link set "eth1.${VLAN}" master "${VRF}" up
    # clab's default veth MTU (9500) doesn't match TRANSIT's real EOS
    # interface (1500, no jumbo config) - without this, TCP negotiates a
    # jumbo MSS that gets silently blackholed past the handshake (no
    # PMTUD ICMP makes it back), so small packets/short writes work but
    # any real transfer (iperf3, real payloads) stalls after the first
    # burst with zero throughput and zero retransmits.
    ip link set "eth1.${VLAN}" mtu 1500
    ip addr add "${IP}" dev "eth1.${VLAN}" 2>/dev/null || true
    ip route add table "${TABLE}" "${CPE_AGGREGATE}" via "${TRANSIT_PEER}" 2>/dev/null || true
    ip route add table "${TABLE}" "${TRANSIT_PEERING_AGGREGATE}" via "${TRANSIT_PEER}" 2>/dev/null || true
    ip route add table "${TABLE}" "${FABRIC_P2P_AGGREGATE}" via "${TRANSIT_PEER}" 2>/dev/null || true
    ip route add table "${TABLE}" "${FABRIC_LOOPBACK_AGGREGATE}" via "${TRANSIT_PEER}" 2>/dev/null || true
    log "  eth1.${VLAN} → ${VRF} (${IP}), return routes ${CPE_AGGREGATE} + ${TRANSIT_PEERING_AGGREGATE} + ${FABRIC_P2P_AGGREGATE} + ${FABRIC_LOOPBACK_AGGREGATE} via ${TRANSIT_PEER}"
}

setup_vlan 100  GOOGLE      "10.255.0.7/31"  100  "10.255.0.6"
setup_vlan 200  CLOUDFLARE  "10.255.0.9/31"  200  "10.255.0.8"
setup_vlan 300  NETFLIX     "10.255.0.11/31" 300  "10.255.0.10"
setup_vlan 400  XBOX        "10.255.0.13/31" 400  "10.255.0.12"
setup_vlan 500  ZOOM        "10.255.0.15/31" 500  "10.255.0.14"

# ====================================================================
# Service IPs — dummy interfaces per VRF
#
# Each VRF gets a dummy (loopback-style) interface holding the service
# destination IPs that CPE traffic and mno-agg.py target.
# ====================================================================
log "Binding service IPs per VRF..."

add_service_ips() {
    local VRF=$1; shift
    local DUMMY="lo-${VRF,,}"   # e.g. lo-google, lo-cloudflare
    ip link add "${DUMMY}" type dummy 2>/dev/null || true
    ip link set "${DUMMY}" master "${VRF}" up
    for IP in "$@"; do
        ip addr add "${IP}" dev "${DUMMY}" 2>/dev/null || true
        log "  ${VRF}: ${IP}"
    done
}

add_service_ips GOOGLE \
    "8.8.8.8/32"           \
    "8.8.4.4/32"           \
    "142.250.0.1/32"       \
    "172.217.0.1/32"

add_service_ips CLOUDFLARE \
    "1.1.1.1/32"           \
    "1.0.0.1/32"           \
    "104.16.0.1/32"

add_service_ips NETFLIX \
    "45.57.0.1/32"         \
    "198.38.96.1/32"       \
    "23.246.0.1/32"

add_service_ips XBOX \
    "208.67.222.222/32"

add_service_ips ZOOM \
    "9.9.9.9/32"

# ====================================================================
# iperf3 servers — TCP/443 TCP/80 UDP/3074 UDP/8801 per VRF
# ====================================================================
log "Starting iperf3 servers..."

start_servers() {
    local VRF=$1
    log "  ${VRF}: TCP/443 TCP/80 UDP/3074 UDP/8801"
    ip vrf exec "${VRF}" iperf3 -s -p 443  --logfile "/var/log/iperf3-${VRF}-443.log"  --daemon
    ip vrf exec "${VRF}" iperf3 -s -p 80   --logfile "/var/log/iperf3-${VRF}-80.log"   --daemon
    ip vrf exec "${VRF}" iperf3 -s -p 3074 --logfile "/var/log/iperf3-${VRF}-3074.log" --daemon
    ip vrf exec "${VRF}" iperf3 -s -p 8801 --logfile "/var/log/iperf3-${VRF}-8801.log" --daemon
}

for VRF in GOOGLE CLOUDFLARE NETFLIX XBOX ZOOM; do
    start_servers "${VRF}"
done

# Default VRF servers for backward-compat (cross-VRF nexthop routes)
log "  default: TCP/443 TCP/80 UDP/3074 UDP/8801"
iperf3 -s -p 443  --logfile /var/log/iperf3-default-443.log  --daemon
iperf3 -s -p 80   --logfile /var/log/iperf3-default-80.log   --daemon
iperf3 -s -p 3074 --logfile /var/log/iperf3-default-3074.log --daemon
iperf3 -s -p 8801 --logfile /var/log/iperf3-default-8801.log --daemon

# ====================================================================
# HTTP content server — default VRF, reachable via 198.51.100.7
# ====================================================================
log "Starting HTTP content server on TCP/8080..."
mkdir -p /srv/http
dd if=/dev/urandom bs=1k count=50 2>/dev/null | base64 > /srv/http/index.html
python3 -m http.server 8080 --directory /srv/http &

log ""
log "TRAFFIC-GEN ready."
log "  eth1           198.51.100.7/31   default VRF"
log "  eth1.100       10.255.0.7/31     GOOGLE     (AS15169)"
log "  eth1.200       10.255.0.9/31     CLOUDFLARE (AS13335)"
log "  eth1.300       10.255.0.11/31    NETFLIX    (AS2906)"
log "  eth1.400       10.255.0.13/31    XBOX"
log "  eth1.500       10.255.0.15/31    ZOOM"

# Keep container alive
wait
