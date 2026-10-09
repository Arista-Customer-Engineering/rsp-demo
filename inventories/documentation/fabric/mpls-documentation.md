# mpls

## Table of Contents

- [Fabric Switches and Management IP](#fabric-switches-and-management-ip)
  - [Fabric Switches with inband Management IP](#fabric-switches-with-inband-management-ip)
- [Fabric Topology](#fabric-topology)
- [Fabric IP Allocation](#fabric-ip-allocation)
  - [Fabric Point-To-Point Links](#fabric-point-to-point-links)
  - [Point-To-Point Links Node Allocation](#point-to-point-links-node-allocation)
  - [Loopback Interfaces (BGP EVPN Peering)](#loopback-interfaces-bgp-evpn-peering)
  - [Loopback0 Interfaces Node Allocation](#loopback0-interfaces-node-allocation)
  - [ISIS CLNS interfaces](#isis-clns-interfaces)
  - [VTEP Loopback VXLAN Tunnel Source Interfaces (VTEPs Only)](#vtep-loopback-vxlan-tunnel-source-interfaces-vteps-only)
  - [VTEP Loopback Node allocation](#vtep-loopback-node-allocation)

## Fabric Switches and Management IP

| POD | Type | Node | Management IP | Platform | Provisioned in CloudVision | Serial Number |
| --- | ---- | ---- | ------------- | -------- | -------------------------- | ------------- |
| RSP | pe | ALPHA-EDGE-01 | 192.168.128.1/24 | 7280SR3 | Provisioned | - |
| RSP | pe | ALPHA-PE-01 | 192.168.128.3/24 | 7280SR3 | Provisioned | - |
| RSP | pe | ALPHA-PE-02 | 192.168.128.4/24 | 7280SR3 | Provisioned | - |
| RSP | pe | ALPHA-PE-03 | 192.168.128.5/24 | 7280SR3 | Provisioned | - |
| RSP | pe | BETA-EDGE-01 | 192.168.128.2/24 | 7280SR3 | Provisioned | - |
| RSP | pe | BETA-PE-01 | 192.168.128.6/24 | 7280SR3 | Provisioned | - |
| RSP | pe | BETA-PE-02 | 192.168.128.7/24 | 7280SR3 | Provisioned | - |
| RSP | pe | DELTA-PE-01 | 192.168.128.8/24 | 7280SR3 | Provisioned | - |
| RSP | pe | DELTA-PE-02 | 192.168.128.9/24 | 7280SR3 | Provisioned | - |
| RSP | pe | GAMMA-PE-01 | 192.168.128.10/24 | 7280SR3 | Provisioned | - |
| RSP | pe | GAMMA-PE-02 | 192.168.128.11/24 | 7280SR3 | Provisioned | - |
| RSP | pe | THETA-PE-01 | 192.168.128.12/24 | 7280SR3 | Provisioned | - |
| RSP | pe | THETA-PE-02 | 192.168.128.13/24 | 7280SR3 | Provisioned | - |

> Provision status is based on Ansible inventory declaration and do not represent real status from CloudVision.

### Fabric Switches with inband Management IP

| POD | Type | Node | Management IP | Inband Interface |
| --- | ---- | ---- | ------------- | ---------------- |

## Fabric Topology

| Type | Node | Node Interface | Peer Type | Peer Node | Peer Interface |
| ---- | ---- | -------------- | --------- | --------- | -------------- |
| pe | ALPHA-EDGE-01 | Ethernet9 | pe | ALPHA-PE-02 | Ethernet8 |
| pe | ALPHA-EDGE-01 | Ethernet10 | pe | ALPHA-PE-01 | Ethernet8 |
| pe | ALPHA-PE-01 | Ethernet6 | pe | DELTA-PE-02 | Ethernet6 |
| pe | ALPHA-PE-01 | Ethernet7 | pe | ALPHA-PE-03 | Ethernet10 |
| pe | ALPHA-PE-01 | Ethernet9 | pe | ALPHA-PE-02 | Ethernet9 |
| pe | ALPHA-PE-01 | Ethernet10 | pe | ALPHA-PE-02 | Ethernet10 |
| pe | ALPHA-PE-02 | Ethernet6 | pe | BETA-PE-01 | Ethernet6 |
| pe | ALPHA-PE-02 | Ethernet7 | pe | ALPHA-PE-03 | Ethernet9 |
| pe | BETA-EDGE-01 | Ethernet9 | pe | BETA-PE-02 | Ethernet8 |
| pe | BETA-EDGE-01 | Ethernet10 | pe | BETA-PE-01 | Ethernet8 |
| pe | BETA-PE-01 | Ethernet9 | pe | BETA-PE-02 | Ethernet9 |
| pe | BETA-PE-01 | Ethernet10 | pe | BETA-PE-02 | Ethernet10 |
| pe | BETA-PE-02 | Ethernet6 | pe | GAMMA-PE-01 | Ethernet6 |
| pe | DELTA-PE-01 | Ethernet5 | pe | THETA-PE-01 | Ethernet10 |
| pe | DELTA-PE-01 | Ethernet6 | pe | GAMMA-PE-02 | Ethernet6 |
| pe | DELTA-PE-01 | Ethernet9 | pe | DELTA-PE-02 | Ethernet9 |
| pe | DELTA-PE-01 | Ethernet10 | pe | DELTA-PE-02 | Ethernet10 |
| pe | DELTA-PE-02 | Ethernet5 | pe | THETA-PE-02 | Ethernet10 |
| pe | GAMMA-PE-01 | Ethernet9 | pe | GAMMA-PE-02 | Ethernet9 |
| pe | GAMMA-PE-01 | Ethernet10 | pe | GAMMA-PE-02 | Ethernet10 |
| pe | THETA-PE-01 | Ethernet9 | pe | THETA-PE-02 | Ethernet9 |

## Fabric IP Allocation

### Fabric Point-To-Point Links

| Uplink IPv4 Pool | Available Addresses | Assigned addresses | Assigned Address % |
| ---------------- | ------------------- | ------------------ | ------------------ |

### Point-To-Point Links Node Allocation

| Node | Node Interface | Node IP Address | Peer Node | Peer Interface | Peer IP Address |
| ---- | -------------- | --------------- | --------- | -------------- | --------------- |

### Loopback Interfaces (BGP EVPN Peering)

| Loopback Pool | Available Addresses | Assigned addresses | Assigned Address % |
| ------------- | ------------------- | ------------------ | ------------------ |
| 172.16.0.0/24 | 256 | 13 | 5.08 % |

### Loopback0 Interfaces Node Allocation

| POD | Node | Loopback0 |
| --- | ---- | --------- |
| RSP | ALPHA-EDGE-01 | 172.16.0.1/32 |
| RSP | ALPHA-PE-01 | 172.16.0.3/32 |
| RSP | ALPHA-PE-02 | 172.16.0.4/32 |
| RSP | ALPHA-PE-03 | 172.16.0.5/32 |
| RSP | BETA-EDGE-01 | 172.16.0.2/32 |
| RSP | BETA-PE-01 | 172.16.0.6/32 |
| RSP | BETA-PE-02 | 172.16.0.7/32 |
| RSP | DELTA-PE-01 | 172.16.0.10/32 |
| RSP | DELTA-PE-02 | 172.16.0.11/32 |
| RSP | GAMMA-PE-01 | 172.16.0.8/32 |
| RSP | GAMMA-PE-02 | 172.16.0.9/32 |
| RSP | THETA-PE-01 | 172.16.0.12/32 |
| RSP | THETA-PE-02 | 172.16.0.13/32 |

### ISIS CLNS interfaces

| POD | Node | CLNS Address |
| --- | ---- | ------------ |
| RSP | ALPHA-EDGE-01 | 49.0001.1720.1600.0001.00 |
| RSP | ALPHA-PE-01 | 49.0001.1720.1600.0003.00 |
| RSP | ALPHA-PE-02 | 49.0001.1720.1600.0004.00 |
| RSP | ALPHA-PE-03 | 49.0001.1720.1600.0005.00 |
| RSP | BETA-EDGE-01 | 49.0001.1720.1600.0002.00 |
| RSP | BETA-PE-01 | 49.0001.1720.1600.0006.00 |
| RSP | BETA-PE-02 | 49.0001.1720.1600.0007.00 |
| RSP | DELTA-PE-01 | 49.0001.1720.1600.0010.00 |
| RSP | DELTA-PE-02 | 49.0001.1720.1600.0011.00 |
| RSP | GAMMA-PE-01 | 49.0001.1720.1600.0008.00 |
| RSP | GAMMA-PE-02 | 49.0001.1720.1600.0009.00 |
| RSP | THETA-PE-01 | 49.0001.1720.1600.0012.00 |
| RSP | THETA-PE-02 | 49.0001.1720.1600.0013.00 |

### VTEP Loopback VXLAN Tunnel Source Interfaces (VTEPs Only)

| VTEP Loopback Pool | Available Addresses | Assigned addresses | Assigned Address % |
| ------------------ | ------------------- | ------------------ | ------------------ |

### VTEP Loopback Node allocation

| POD | Node | Loopback1 |
| --- | ---- | --------- |
