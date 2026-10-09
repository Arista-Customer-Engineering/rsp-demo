# RSP Demo Lab — Walkthrough Guide

A containerlab-based MPLS service provider network built with [Arista AVD](https://avd.arista.com/). The lab models a regional broadband provider with IS-IS Segment Routing, BGP EVPN, CG-NAT, DHCP relay, transit peering, VPWS mobile backhaul, and PON subscriber access — all generated from AVD data models and deployed to cEOS containers.

## Quick Start

```bash
make clab          # bring up the containerlab topology
make build         # generate EOS intended configs from AVD
make deploy        # push configs to all nodes via eAPI
```

Package management is handled by [uv](https://docs.astral.sh/uv/) via the Makefile. `make build` installs everything automatically — `ansible-core`, the AVD collection, and the [`sonic-com/arista.eos`](https://github.com/sonic-com/arista.eos) fork needed for eAPI config pushes.

## Topology Overview

```
                         TRAFFIC-GEN
                              |
                           TRANSIT
                     (AS 1299 / 13760 / 2711)
                        /           \
               ALPHA-EDGE-01    BETA-EDGE-01         <-- Edge / Route Reflectors
               (RR, transit)    (RR, transit)
                  |    \           /    |
              CG-NAT-01  \     /  CG-NAT-02          <-- CG-NAT Appliances
                  |        \  /        |
   ALPHA-PE-01--ALPHA-PE-02  BETA-PE-01--BETA-PE-02   <-- Provider Edge (Ring)
        |             |          |    \       |
   ALPHA-PE-03   DELTA-PE-02  BETA-PON-01  MNO-CSR    <-- Leaf / PON / MNO
        |         /       \      / \
    ALPHA-DHCP   /      OMNI-PON-01 \                 <-- DHCP Server
     (Kea)      /        /    \      \
         DELTA-PE-01  CPE-PUB CPE-NAT CPE-PUB/NAT    <-- Subscribers
              |
         GAMMA-PE-01--GAMMA-PE-02                     <-- POP Ring continues
              |
         THETA-PE-01--THETA-PE-02                     <-- MNO Aggregation POP
              |
           MNO-AGG
```

**26 nodes** across 5 POPs (ALPHA, BETA, GAMMA, DELTA, THETA), with 13 cEOS MPLS fabric nodes, 2 CG-NAT appliances, 1 transit router, 2 PON shelves, 4 CPE containers, 1 DHCP server, and 3 auxiliary Linux nodes.

### Management Network

| Setting | Value |
|---------|-------|
| Management VRF | `OOB` |
| Subnet | `192.168.128.0/24` |
| Gateway | `192.168.128.254` |

---

## 1. IS-IS Underlay

The MPLS fabric runs IS-IS level-2 as the IGP. All PE and Edge nodes participate in a single IS-IS instance `CORE` within area `49.0001`.

| Parameter | Value |
|-----------|-------|
| IS-IS Instance | `CORE` |
| IS-type | `level-2` |
| NET format | `49.0001.1720.1600.00XX.00` |
| Default metric | `1000` |
| Authentication | MD5 on all P2P links |
| TI-LFA | Node protection, 10s local convergence delay |

### Verify IS-IS Adjacencies

Log into any PE or Edge node and confirm all expected neighbors are up:

```
show isis neighbors
```

You should see level-2 adjacencies to all directly connected MPLS nodes. Each POP pair (e.g., ALPHA-PE-01 and ALPHA-PE-02) has intra-POP links, plus inter-POP ring links connecting POPs in sequence.

### Verify IS-IS Database

```
show isis database detail
```

Confirm every fabric node appears in the LSDB. There should be 13 LSPs (one per fabric node).

### Verify IS-IS Routes

```
show ip route isis
```

Every node's Loopback0 (`172.16.0.x/32`) should appear as an IS-IS route. These loopbacks are the BGP next-hops for the overlay.

### Router IDs and Loopback0 Assignments

| Node | ID | Loopback0 | IS-IS NET |
|------|----|-----------|-----------|
| ALPHA-EDGE-01 | 1 | 172.16.0.1/32 | 49.0001.1720.1600.0001.00 |
| BETA-EDGE-01 | 2 | 172.16.0.2/32 | 49.0001.1720.1600.0002.00 |
| ALPHA-PE-01 | 3 | 172.16.0.3/32 | 49.0001.1720.1600.0003.00 |
| ALPHA-PE-02 | 4 | 172.16.0.4/32 | 49.0001.1720.1600.0004.00 |
| ALPHA-PE-03 | 5 | 172.16.0.5/32 | 49.0001.1720.1600.0005.00 |
| BETA-PE-01 | 6 | 172.16.0.6/32 | 49.0001.1720.1600.0006.00 |
| BETA-PE-02 | 7 | 172.16.0.7/32 | 49.0001.1720.1600.0007.00 |
| GAMMA-PE-01 | 8 | 172.16.0.8/32 | 49.0001.1720.1600.0008.00 |
| GAMMA-PE-02 | 9 | 172.16.0.9/32 | 49.0001.1720.1600.0009.00 |
| DELTA-PE-01 | 10 | 172.16.0.10/32 | 49.0001.1720.1600.0010.00 |
| DELTA-PE-02 | 11 | 172.16.0.11/32 | 49.0001.1720.1600.0011.00 |
| THETA-PE-01 | 12 | 172.16.0.12/32 | 49.0001.1720.1600.0012.00 |
| THETA-PE-02 | 13 | 172.16.0.13/32 | 49.0001.1720.1600.0013.00 |

---

## 2. Segment Routing MPLS Transport

SR-MPLS is the label distribution protocol — no LDP. Each node advertises a node segment index via IS-IS, and the SRGB is used to derive transport labels.

### Verify Segment Routing Configuration

```
show isis segment-routing prefix-segments
```

Each node's Loopback0 should have an SR prefix-SID. The node SID index equals the node ID (e.g., ALPHA-EDGE-01 = index 1, BETA-PE-01 = index 6).

### Verify MPLS Label Forwarding

```
show mpls lfib route
```

You should see SR labels for every Loopback0 prefix in the fabric. These labels provide the transport tunnels that EVPN services ride on.

### Verify MPLS Reachability

From any PE, confirm you can reach every other PE's Loopback0 via an MPLS LSP:

```
ping 172.16.0.6 source 172.16.0.3
```

### Verify TI-LFA Protection

```
show isis ti-lfa path
```

TI-LFA provides sub-50ms failover with node protection. Each prefix should show a backup path with a repair label stack.

---

## 3. BGP EVPN Overlay

The overlay control plane uses iBGP (AS 65000) with EVPN address family and MPLS encapsulation. Two route reflectors (ALPHA-EDGE-01, BETA-EDGE-01) serve all 11 PE clients.

| Parameter | Value |
|-----------|-------|
| BGP AS | `65000` |
| Route Reflectors | ALPHA-EDGE-01, BETA-EDGE-01 |
| RR Cluster ID | `172.16.0.0` |
| EVPN encapsulation | MPLS |
| RT-membership (RTC) | Enabled |

### Verify BGP EVPN Sessions

On any PE node:

```
show bgp evpn summary
```

Each PE should have two established sessions — one to each route reflector. On a route reflector:

```
show bgp evpn summary
```

The RR should show sessions to all 11 PE clients plus the other RR.

### Verify EVPN Route Types

```
show bgp evpn
```

You should see a mix of route types depending on which services are active:

| Type | Purpose |
|------|---------|
| Type-1 | Ethernet Auto-Discovery (EVPN A/A, ES membership) |
| Type-2 | MAC/IP advertisement |
| Type-3 | Inclusive Multicast (IMET) |
| Type-4 | Ethernet Segment (ES route for DF election) |
| Type-5 | IP Prefix (inter-subnet routing) |

### Verify RT-Membership

RT-membership (RTC) constrains which EVPN routes each PE receives — a PE only gets routes for VRFs it participates in:

```
show bgp rt-membership summary
show bgp rt-membership route-target
```

---

## 4. Services

The lab deploys several service types, each in its own VRF with EVPN providing the multi-site fabric. The services are layered from bottom to top:

| VRF | VRF ID | Purpose |
|-----|--------|---------|
| `INTERNET` | 30000 | Public internet — transit peering, subscriber public IPs |
| `DHCP` | 40000 | DHCP relay — cross-VRF relay path to centralized Kea server |
| `CGNAT` | 50000 | CG-NAT — subscriber CGNAT pools routed to NAT appliances |
| `PON_MGMT` | 10000 | PON shelf management |
| `CPE_MGMT` | 20000 | CPE management |

### 4a. INTERNET VRF — Transit Peering

The INTERNET VRF provides upstream connectivity through three transit providers peered at the Edge routers.

| Peer | ASN | Node | Interface |
|------|-----|------|-----------|
| AS1299 Arelion | 1299 | ALPHA-EDGE-01 | Ethernet1 |
| AS13760 Uniti | 13760 | ALPHA-EDGE-01 | Ethernet2 |
| AS2711 Segra | 2711 | BETA-EDGE-01 | Ethernet1 |

The RSP's own ASN toward transit providers is **3791**.

#### Verify Transit BGP Sessions

```
show bgp vrf INTERNET summary
```

On ALPHA-EDGE-01 you should see three eBGP sessions (two transit + one CG-NAT appliance). On BETA-EDGE-01, two (one transit + one CG-NAT).

#### Verify Transit Routes

```
show ip route vrf INTERNET
show ip route vrf INTERNET summary
```

Routes in the `80.0.0.0/16`, `81.0.0.0/16`, and `82.0.0.0/16` ranges should be learned from the transit providers.

#### Verify EVPN Type-5 Prefix Routes for INTERNET

```
show bgp evpn route-type ip-prefix vrf INTERNET
```

### 4b. Public Subscriber Access (SVI 1001)

Public subscribers connect through PON shelves and receive addresses from `2.3.4.0/24` via DHCP. Traffic routes directly through the INTERNET VRF — no NAT.

```
show vlan 1001
show interfaces vlan 1001
show ip interface vlan 1001
```

The virtual gateway is `2.3.4.1/24`. Verify the SVI is up and has the correct VRF assignment:

```
show vrf INTERNET
```

### 4c. CG-NAT Subscriber Access (SVI 1002 / 1004)

CGNAT subscribers receive addresses from RFC 6598 space (`100.64.0.0/22` for BETA, `100.64.4.0/22` for OMNI). Traffic routes through the CGNAT VRF to the CG-NAT appliances.

```
show interfaces vlan 1002
show ip route vrf CGNAT
show bgp vrf CGNAT summary
```

#### CG-NAT Appliance Peering

Each Edge router peers with its local CG-NAT appliance in both the INTERNET and CGNAT VRFs, using sub-interfaces on a shared physical link:

| VRF | Node | Interface | Local IP | Peer IP | Local AS | Remote AS |
|-----|------|-----------|----------|---------|----------|-----------|
| INTERNET | ALPHA-EDGE-01 | Eth3.10 | 198.51.100.7/31 | .6 | 3791 | 65100 |
| CGNAT | ALPHA-EDGE-01 | Eth3.20 | 198.51.100.15/31 | .14 | 64496 | 65100 |
| INTERNET | BETA-EDGE-01 | Eth3.10 | 198.51.100.9/31 | .8 | 3791 | 65100 |
| CGNAT | BETA-EDGE-01 | Eth3.20 | 198.51.100.17/31 | .16 | 64496 | 65100 |

#### CG-NAT HA Failover

A VPWS pseudowire connects the two CG-NAT appliances for HA state synchronization:

```
show patch panel
show bgp evpn route-type auto-discovery
```

On ALPHA-PE-01 or BETA-PE-01, look for the `CGNAT_HA_FAILOVER` patch panel entry connecting Port-Channel5 to the VPWS pseudowire.

### 4d. DHCP Relay

All subscriber DHCP requests are relayed cross-VRF through the DHCP VRF to a centralized Kea DHCPv4/v6 server at `192.168.100.10` (ALPHA-DHCP, connected via ALPHA-PE-03).

#### Verify DHCP Relay Configuration

```
show ip dhcp relay
```

You should see option 82 enabled with circuit-id sub-option, and relay entries for Vlan1001 and Vlan1002 pointing to `192.168.100.10 vrf DHCP`.

#### Verify DHCP Leases on the Server

```bash
docker exec clab-sp-ALPHA-DHCP cat /var/lib/kea/dhcp4.leases
docker exec clab-sp-ALPHA-DHCP cat /var/lib/kea/dhcp6.leases
```

#### Verify CPE Addresses

```bash
docker exec clab-sp-BETA-CPE-PUB ip addr show eth1
docker exec clab-sp-BETA-CPE-NAT ip addr show eth1
docker exec clab-sp-OMNI-CPE-PUB ip addr show eth1
docker exec clab-sp-OMNI-CPE-NAT ip addr show eth1
```

Public CPEs should have addresses in `2.3.4.0/24`. CGNAT CPEs should have addresses in `100.64.0.0/22` or `100.64.4.0/22`.

#### DHCP Relay Path

The relay path crosses VRFs using the DHCP VRF as a transit:

```
Subscriber (Vlan1001/1002) → ip helper-address 192.168.100.10
  → source-interface Loopback40, source-vrf DHCP
  → DHCP VRF routes to ALPHA-PE-03 (Ethernet2, 192.168.100.1/24)
  → ALPHA-DHCP (eth1, 192.168.100.10)
```

EOS inserts option 82 with:
- **Circuit-ID** — ASCII SVI name (e.g., `Vlan1001`)
- **Link-Selection** (RFC 3527) — SVI network address (e.g., `2.3.4.0`)
- **VRF name** — sub-option 151 (e.g., `INTERNET`)

Kea uses the link-selection address for subnet matching, which naturally distinguishes public (`2.3.4.0/24`) from CGNAT (`100.64.0.0/22`) requests without client classification.

#### DHCPv6 Prefix Delegation

CPEs also request IPv6 prefix delegation (/56) via DHCPv6. The PE pairs synchronize delegated prefix routes:

```
show ipv6 dhcp relay binding
show ipv6 route vrf INTERNET
```

On BETA-PE-01/02, the `dhcp relay ipv6 routes sync neighbor` configuration keeps PD routes consistent across the EVPN A/A pair.

### 4e. VPWS — Mobile Backhaul (MNO)

Two E-LINE pseudowires carry mobile backhaul traffic between a cell-site router (MNO-CSR off BETA-PE-01) and the MNO aggregation site (MNO-AGG off THETA-PE-01/02):

| Service | VLAN | From | To |
|---------|------|------|----|
| MNO-EVC1001 | 1001 | BETA-PE-01:Eth4 | THETA-PE-01:Eth1 |
| MNO-EVC1002 | 1002 | BETA-PE-01:Eth4 | THETA-PE-01:Eth1 |

#### Verify VPWS

```
show patch panel
show bgp evpn route-type auto-discovery esi 0000:0000:0000:0000:0063
```

On BETA-PE-01, confirm the patch panel maps Ethernet4 sub-interfaces to VPWS pseudowires.

---

## 5. PON Shelf Architecture

PON shelves simulate optical line terminals. Each shelf connects to a pair of PEs via EVPN Active-Active dual-homing over a Port-Channel with dot1q sub-interfaces.

| PON Shelf | PE Pair | Port-Channel | CPEs |
|-----------|---------|--------------|------|
| BETA-PON-01 | BETA-PE-01, BETA-PE-02 | Po2 | BETA-CPE-PUB, BETA-CPE-NAT |
| OMNI-PON-01 | DELTA-PE-02, GAMMA-PE-01 | Po2 | OMNI-CPE-PUB, OMNI-CPE-NAT |

OMNI-PON-01 is notable because it is dual-homed **cross-POP** — one link to DELTA-PE-02, one to GAMMA-PE-01.

### Sub-interface to Service Mapping

| Sub-interface | VLAN | Service | VRF |
|---------------|------|---------|-----|
| Po2.1001 | 1001 | Public Internet | INTERNET |
| Po2.1002 | 1002 | CG-NAT Data | CGNAT |
| Po2.1003 | 1003 | PON Management | PON_MGMT |

### Verify EVPN Ethernet Segments

```
show bgp evpn route-type ethernet-segment
show bgp evpn route-type auto-discovery
```

Each sub-interface has its own ESI. Confirm that both PEs in the pair show the same ES routes and that DF election has completed.

### Verify EVPN A/A Forwarding

```
show port-channel 2 detailed
```

---

## 6. Monitoring and Troubleshooting

### Connectivity Monitoring

The Edge routers run `monitor connectivity` with ICMP probes (7000-byte payload) to every PE's Loopback0:

```
show monitor connectivity
```

### sFlow

All PE nodes export sFlow samples to 127.0.0.1 (local collector) sourced from Loopback0:

```
show sflow
```

### Useful Debug Commands

```
# Full MPLS forwarding table
show mpls lfib route

# All VRFs and their interfaces
show vrf

# EVPN routes for a specific VRF
show bgp evpn route-type ip-prefix vrf INTERNET

# EVPN route detail for a specific RD
show bgp evpn rd 172.16.0.6:30000

# Ethernet segment status
show bgp evpn instance

# DHCP relay statistics
show ip dhcp relay counters

# CoPP policy hits
show traffic-policy counters CPU-PROTECT
```

---

## 7. Accessing Nodes

### cEOS Fabric Nodes (EOS CLI)

```bash
# Via docker exec
docker exec -it clab-sp-BETA-PE-01 Cli

# Via SSH (admin / password from host_vars)
ssh admin@192.168.128.6
```

### Linux Nodes

```bash
docker exec -it clab-sp-ALPHA-DHCP bash
docker exec -it clab-sp-BETA-CPE-PUB sh
```

### Kea DHCP Server

```bash
# Check Kea processes
docker exec clab-sp-ALPHA-DHCP sh -c 'ls /run/kea/'

# View DHCPv4 leases
docker exec clab-sp-ALPHA-DHCP cat /var/lib/kea/dhcp4.leases

# Live packet capture on DHCP server interface
docker exec clab-sp-ALPHA-DHCP tcpdump -i eth1 -n port 67 or port 68
```

---

## Project Structure

```
rsp-demo/
  sp.clab.yml                          # Containerlab topology
  Makefile                             # Build, deploy, clab targets
  requirements.yml                     # Ansible collection requirements
  dhcp/
    kea-dhcp4.conf                     # Kea DHCPv4 configuration
    kea-dhcp6.conf                     # Kea DHCPv6 configuration
    startup.sh                         # ALPHA-DHCP container entrypoint
  cpe/
    dhcpcd.conf                        # CPE DHCPv6-PD client config
  inventories/
    inventory.yml                      # Ansible inventory
    group_vars/
      all.yml                          # Global settings (AAA, NTP, DNS, etc.)
      mpls/
        fabric.yml                     # IS-IS, SR, BGP, node definitions
        services.yml                   # Network services keys
      services/
        _svi_profiles.yml              # Shared DHCP relay SVI profiles
        _db_esi.yml                    # ESI allocation database
        services_internet.yml          # INTERNET VRF (transit, public SVIs)
        services_cg_nat.yml            # CGNAT VRF (CGNAT pools, HA VPWS)
        services_dhcp_relay.yml        # DHCP VRF (relay infrastructure)
        services_vpws.yml              # MNO mobile backhaul pseudowires
        endpoints_pon_shelves.yml       # PON shelf endpoint definitions
    host_vars/                         # Per-node overrides (PON, CG-NAT, etc.)
    intended/
      configs/                         # Generated EOS configs (.cfg)
      structured_configs/              # Generated structured YAML
    documentation/                     # Generated device docs
```
