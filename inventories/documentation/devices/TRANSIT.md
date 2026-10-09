# TRANSIT

## Table of Contents

- [Management](#management)
  - [Management Interfaces](#management-interfaces)
  - [Management API HTTP](#management-api-http)
- [Authentication](#authentication)
  - [Local Users](#local-users)
  - [AAA Authentication](#aaa-authentication)
  - [AAA Authorization](#aaa-authorization)
- [Interfaces](#interfaces)
  - [Ethernet Interfaces](#ethernet-interfaces)
- [Routing](#routing)
  - [Service Routing Protocols Model](#service-routing-protocols-model)
  - [IP Routing](#ip-routing)
  - [IPv6 Routing](#ipv6-routing)
  - [Static Routes](#static-routes)
  - [Router BGP](#router-bgp)
- [VRF Instances](#vrf-instances)
  - [VRF Instances Summary](#vrf-instances-summary)
  - [VRF Instances Device Configuration](#vrf-instances-device-configuration)

## Management

### Management Interfaces

#### Management Interfaces Summary

##### IPv4

| Management Interface | Description | Type | VRF | IP Address | Gateway |
| -------------------- | ----------- | ---- | --- | ---------- | ------- |
| Management0 | OOB_MANAGEMENT | oob | OOB | 192.168.128.220/24 | 192.168.128.254 |

##### IPv6

| Management Interface | Description | Type | VRF | IPv6 Address | IPv6 Gateway | ND RA Disabled | ND RA RX Accept | ND Managed Config Flag | ND Other Config Flag | ND Cache | ND RA DNS Servers |
| -------------------- | ----------- | ---- | --- | ------------ | ------------ | -------------- | --------------- | ---------------------- | -------------------- | -------- | ----------------- |
| Management0 | OOB_MANAGEMENT | oob | OOB | - | - | - | - | - | - | - | - |

#### Management Interfaces Device Configuration

```eos
!
interface Management0
   description OOB_MANAGEMENT
   no shutdown
   vrf OOB
   ip address 192.168.128.220/24
   no lldp transmit
   no lldp receive

```

### Management API HTTP

#### Management API HTTP Summary

| HTTP | HTTPS | UNIX-Socket | Default Services | Session Timeout |
| ---- | ----- | ----------- | ---------------- | --------------- |
| False | True | - | - | 1440 minutes |

#### Management API VRF Access

| VRF Name | IPv4 ACL | IPv6 ACL |
| -------- | -------- | -------- |
| OOB | - | - |

#### Management API HTTP Device Configuration

```eos
!
management api http-commands
   protocol https
   no shutdown
   !
   vrf OOB
      no shutdown
```

## Authentication

### Local Users

#### Local Users Summary

| User | Privilege | Role | Disabled | Shell |
| ---- | --------- | ---- | -------- | ----- |
| admin | 15 | network-admin | False | - |
| dave.watkins | 15 | network-admin | False | - |

#### Local Users Device Configuration

```eos
!
username admin privilege 15 role network-admin secret sha512 <removed>
username dave.watkins privilege 15 role network-admin secret sha512 <removed>
```

### AAA Authentication

#### AAA Authentication Summary

| Type | Sub-type | User Stores |
| ---- | -------- | ---------- |
| Login | default | local |
| Login | console | local |

#### AAA Authentication Device Configuration

```eos
aaa authentication login default local
aaa authentication login console local
!
```

### AAA Authorization

#### AAA Authorization Summary

| Type | User Stores |
| ---- | ----------- |
| Exec | local |

Authorization for configuration commands is disabled.

#### AAA Authorization Device Configuration

```eos
aaa authorization exec default local
!
```

## Interfaces

### Ethernet Interfaces

#### Ethernet Interfaces Summary

##### L2

| Interface | Description | Mode | VLANs | Native VLAN | Trunk Group | Channel-Group |
| --------- | ----------- | ---- | ----- | ----------- | ----------- | ------------- |

*Inherited from Port-Channel Interface

##### Flexible Encapsulation Interfaces

| Interface | Description | Vlan ID | Client Encapsulation | Client Inner Encapsulation | Client VLAN | Client Outer VLAN Tag | Client Inner VLAN Tag | Network Encapsulation | Network Inner Encapsulation | Network VLAN | Network Outer VLAN Tag | Network Inner VLAN Tag |
| --------- | ----------- | ------- | -------------------- | -------------------------- | ----------- | --------------------- | --------------------- | --------------------- | --------------------------- | ------------ | ---------------------- | ---------------------- |
| Ethernet4.100 | GOOGLE content peering | - | dot1q | - | 100 | - | - | - | - | - | - | - |
| Ethernet4.200 | CLOUDFLARE content peering | - | dot1q | - | 200 | - | - | - | - | - | - | - |
| Ethernet4.300 | NETFLIX content peering | - | dot1q | - | 300 | - | - | - | - | - | - | - |
| Ethernet4.400 | XBOX content peering | - | dot1q | - | 400 | - | - | - | - | - | - | - |
| Ethernet4.500 | ZOOM content peering | - | dot1q | - | 500 | - | - | - | - | - | - | - |
| Ethernet5.12 | Arelion-Uniti transit mesh | - | dot1q | - | 12 | - | - | - | - | - | - | - |
| Ethernet5.13 | Arelion-Segra transit mesh | - | dot1q | - | 13 | - | - | - | - | - | - | - |
| Ethernet5.23 | Uniti-Segra transit mesh | - | dot1q | - | 23 | - | - | - | - | - | - | - |
| Ethernet5.101 | Arelion-Google peering | - | dot1q | - | 101 | - | - | - | - | - | - | - |
| Ethernet5.102 | Uniti-Cloudflare peering | - | dot1q | - | 102 | - | - | - | - | - | - | - |
| Ethernet5.103 | Segra-Xbox peering | - | dot1q | - | 103 | - | - | - | - | - | - | - |
| Ethernet5.104 | Arelion-Netflix peering | - | dot1q | - | 104 | - | - | - | - | - | - | - |
| Ethernet5.105 | Uniti-Netflix peering | - | dot1q | - | 105 | - | - | - | - | - | - | - |
| Ethernet5.106 | Segra-Netflix peering | - | dot1q | - | 106 | - | - | - | - | - | - | - |
| Ethernet6.12 | Uniti-Arelion transit mesh | - | dot1q | - | 12 | - | - | - | - | - | - | - |
| Ethernet6.13 | Segra-Arelion transit mesh | - | dot1q | - | 13 | - | - | - | - | - | - | - |
| Ethernet6.23 | Segra-Uniti transit mesh | - | dot1q | - | 23 | - | - | - | - | - | - | - |
| Ethernet6.101 | Google-Arelion peering | - | dot1q | - | 101 | - | - | - | - | - | - | - |
| Ethernet6.102 | Cloudflare-Uniti peering | - | dot1q | - | 102 | - | - | - | - | - | - | - |
| Ethernet6.103 | Xbox-Segra peering | - | dot1q | - | 103 | - | - | - | - | - | - | - |
| Ethernet6.104 | Netflix-Arelion peering | - | dot1q | - | 104 | - | - | - | - | - | - | - |
| Ethernet6.105 | Netflix-Uniti peering | - | dot1q | - | 105 | - | - | - | - | - | - | - |
| Ethernet6.106 | Netflix-Segra peering | - | dot1q | - | 106 | - | - | - | - | - | - | - |

##### IPv4

| Interface | Description | Channel Group | IP Address | VRF | MTU | Shutdown | ACL In | ACL Out |
| --------- | ----------- | ------------- | ---------- | --- | --- | -------- | ------ | ------- |
| Ethernet1 | ALPHA-EDGE-01 Ethernet1 (Arelion uplink) | - | 198.51.100.0/31 | ARELION | - | False | - | - |
| Ethernet2 | ALPHA-EDGE-01 Ethernet2 (Uniti uplink) | - | 198.51.100.2/31 | UNITI | - | False | - | - |
| Ethernet3 | BETA-EDGE-01 Ethernet1 (Segra uplink) | - | 198.51.100.4/31 | SEGRA | - | False | - | - |
| Ethernet4.100 | GOOGLE content peering | - | 10.255.0.6/31 | GOOGLE | - | False | - | - |
| Ethernet4.200 | CLOUDFLARE content peering | - | 10.255.0.8/31 | CLOUDFLARE | - | False | - | - |
| Ethernet4.300 | NETFLIX content peering | - | 10.255.0.10/31 | NETFLIX | - | False | - | - |
| Ethernet4.400 | XBOX content peering | - | 10.255.0.12/31 | XBOX | - | False | - | - |
| Ethernet4.500 | ZOOM content peering | - | 10.255.0.14/31 | ZOOM | - | False | - | - |
| Ethernet5.12 | Arelion-Uniti transit mesh | - | 10.99.12.0/31 | ARELION | - | False | - | - |
| Ethernet5.13 | Arelion-Segra transit mesh | - | 10.99.13.0/31 | ARELION | - | False | - | - |
| Ethernet5.23 | Uniti-Segra transit mesh | - | 10.99.23.0/31 | UNITI | - | False | - | - |
| Ethernet5.101 | Arelion-Google peering | - | 10.98.101.0/31 | ARELION | - | False | - | - |
| Ethernet5.102 | Uniti-Cloudflare peering | - | 10.98.102.0/31 | UNITI | - | False | - | - |
| Ethernet5.103 | Segra-Xbox peering | - | 10.98.103.0/31 | SEGRA | - | False | - | - |
| Ethernet5.104 | Arelion-Netflix peering | - | 10.98.104.0/31 | ARELION | - | False | - | - |
| Ethernet5.105 | Uniti-Netflix peering | - | 10.98.105.0/31 | UNITI | - | False | - | - |
| Ethernet5.106 | Segra-Netflix peering | - | 10.98.106.0/31 | SEGRA | - | False | - | - |
| Ethernet6.12 | Uniti-Arelion transit mesh | - | 10.99.12.1/31 | UNITI | - | False | - | - |
| Ethernet6.13 | Segra-Arelion transit mesh | - | 10.99.13.1/31 | SEGRA | - | False | - | - |
| Ethernet6.23 | Segra-Uniti transit mesh | - | 10.99.23.1/31 | SEGRA | - | False | - | - |
| Ethernet6.101 | Google-Arelion peering | - | 10.98.101.1/31 | GOOGLE | - | False | - | - |
| Ethernet6.102 | Cloudflare-Uniti peering | - | 10.98.102.1/31 | CLOUDFLARE | - | False | - | - |
| Ethernet6.103 | Xbox-Segra peering | - | 10.98.103.1/31 | XBOX | - | False | - | - |
| Ethernet6.104 | Netflix-Arelion peering | - | 10.98.104.1/31 | NETFLIX | - | False | - | - |
| Ethernet6.105 | Netflix-Uniti peering | - | 10.98.105.1/31 | NETFLIX | - | False | - | - |
| Ethernet6.106 | Netflix-Segra peering | - | 10.98.106.1/31 | NETFLIX | - | False | - | - |

##### IPv6

| Interface | Description | Channel Group | IPv6 Addresses | VRF | MTU | Shutdown | ND RA Disabled | ND RA RX Accept | ND Managed Config Flag | ND Other Config Flag | ND Cache | ND RA DNS Servers | IPv6 ACL In | IPv6 ACL Out |
| --------- | ----------- | ------------- | -------------- | --- | --- | -------- | -------------- | --------------- | ---------------------- | -------------------- | -------- | ----------------- | ----------- | ------------ |
| Ethernet1 | ALPHA-EDGE-01 Ethernet1 (Arelion uplink) | - | 2601::0/127 | ARELION | - | False | True | - | - | - | - | - | - | - |
| Ethernet2 | ALPHA-EDGE-01 Ethernet2 (Uniti uplink) | - | 2602::0/127 | UNITI | - | False | True | - | - | - | - | - | - | - |
| Ethernet3 | BETA-EDGE-01 Ethernet1 (Segra uplink) | - | 2603::0/127 | SEGRA | - | False | True | - | - | - | - | - | - | - |

#### Ethernet Interfaces Device Configuration

```eos
!
interface Ethernet1
   description ALPHA-EDGE-01 Ethernet1 (Arelion uplink)
   no shutdown
   no switchport
   vrf ARELION
   ip address 198.51.100.0/31
   ipv6 enable
   ipv6 address 2601::0/127
   ipv6 nd ra disabled
!
interface Ethernet2
   description ALPHA-EDGE-01 Ethernet2 (Uniti uplink)
   no shutdown
   no switchport
   vrf UNITI
   ip address 198.51.100.2/31
   ipv6 enable
   ipv6 address 2602::0/127
   ipv6 nd ra disabled
!
interface Ethernet3
   description BETA-EDGE-01 Ethernet1 (Segra uplink)
   no shutdown
   no switchport
   vrf SEGRA
   ip address 198.51.100.4/31
   ipv6 enable
   ipv6 address 2603::0/127
   ipv6 nd ra disabled
!
interface Ethernet4
   description TRAFFIC-GEN uplink
   no shutdown
   no switchport
!
interface Ethernet4.100
   description GOOGLE content peering
   no shutdown
   encapsulation vlan
      client dot1q 100
   vrf GOOGLE
   ip address 10.255.0.6/31
!
interface Ethernet4.200
   description CLOUDFLARE content peering
   no shutdown
   encapsulation vlan
      client dot1q 200
   vrf CLOUDFLARE
   ip address 10.255.0.8/31
!
interface Ethernet4.300
   description NETFLIX content peering
   no shutdown
   encapsulation vlan
      client dot1q 300
   vrf NETFLIX
   ip address 10.255.0.10/31
!
interface Ethernet4.400
   description XBOX content peering
   no shutdown
   encapsulation vlan
      client dot1q 400
   vrf XBOX
   ip address 10.255.0.12/31
!
interface Ethernet4.500
   description ZOOM content peering
   no shutdown
   encapsulation vlan
      client dot1q 500
   vrf ZOOM
   ip address 10.255.0.14/31
!
interface Ethernet5
   no shutdown
   no switchport
!
interface Ethernet5.12
   description Arelion-Uniti transit mesh
   no shutdown
   encapsulation vlan
      client dot1q 12
   vrf ARELION
   ip address 10.99.12.0/31
!
interface Ethernet5.13
   description Arelion-Segra transit mesh
   no shutdown
   encapsulation vlan
      client dot1q 13
   vrf ARELION
   ip address 10.99.13.0/31
!
interface Ethernet5.23
   description Uniti-Segra transit mesh
   no shutdown
   encapsulation vlan
      client dot1q 23
   vrf UNITI
   ip address 10.99.23.0/31
!
interface Ethernet5.101
   description Arelion-Google peering
   no shutdown
   encapsulation vlan
      client dot1q 101
   vrf ARELION
   ip address 10.98.101.0/31
!
interface Ethernet5.102
   description Uniti-Cloudflare peering
   no shutdown
   encapsulation vlan
      client dot1q 102
   vrf UNITI
   ip address 10.98.102.0/31
!
interface Ethernet5.103
   description Segra-Xbox peering
   no shutdown
   encapsulation vlan
      client dot1q 103
   vrf SEGRA
   ip address 10.98.103.0/31
!
interface Ethernet5.104
   description Arelion-Netflix peering
   no shutdown
   encapsulation vlan
      client dot1q 104
   vrf ARELION
   ip address 10.98.104.0/31
!
interface Ethernet5.105
   description Uniti-Netflix peering
   no shutdown
   encapsulation vlan
      client dot1q 105
   vrf UNITI
   ip address 10.98.105.0/31
!
interface Ethernet5.106
   description Segra-Netflix peering
   no shutdown
   encapsulation vlan
      client dot1q 106
   vrf SEGRA
   ip address 10.98.106.0/31
!
interface Ethernet6
   no shutdown
   no switchport
!
interface Ethernet6.12
   description Uniti-Arelion transit mesh
   no shutdown
   encapsulation vlan
      client dot1q 12
   vrf UNITI
   ip address 10.99.12.1/31
!
interface Ethernet6.13
   description Segra-Arelion transit mesh
   no shutdown
   encapsulation vlan
      client dot1q 13
   vrf SEGRA
   ip address 10.99.13.1/31
!
interface Ethernet6.23
   description Segra-Uniti transit mesh
   no shutdown
   encapsulation vlan
      client dot1q 23
   vrf SEGRA
   ip address 10.99.23.1/31
!
interface Ethernet6.101
   description Google-Arelion peering
   no shutdown
   encapsulation vlan
      client dot1q 101
   vrf GOOGLE
   ip address 10.98.101.1/31
!
interface Ethernet6.102
   description Cloudflare-Uniti peering
   no shutdown
   encapsulation vlan
      client dot1q 102
   vrf CLOUDFLARE
   ip address 10.98.102.1/31
!
interface Ethernet6.103
   description Xbox-Segra peering
   no shutdown
   encapsulation vlan
      client dot1q 103
   vrf XBOX
   ip address 10.98.103.1/31
!
interface Ethernet6.104
   description Netflix-Arelion peering
   no shutdown
   encapsulation vlan
      client dot1q 104
   vrf NETFLIX
   ip address 10.98.104.1/31
!
interface Ethernet6.105
   description Netflix-Uniti peering
   no shutdown
   encapsulation vlan
      client dot1q 105
   vrf NETFLIX
   ip address 10.98.105.1/31
!
interface Ethernet6.106
   description Netflix-Segra peering
   no shutdown
   encapsulation vlan
      client dot1q 106
   vrf NETFLIX
   ip address 10.98.106.1/31
```

## Routing

### Service Routing Protocols Model

Multi agent routing protocol model enabled

```eos
!
service routing protocols model multi-agent
```

### IP Routing

#### IP Routing Summary

| VRF | Routing Enabled |
| --- | --------------- |
| default | True |
| ARELION | True |
| CLOUDFLARE | True |
| GOOGLE | True |
| NETFLIX | True |
| OOB | False |
| SEGRA | True |
| UNITI | True |
| XBOX | True |
| ZOOM | True |

#### IP Routing Device Configuration

```eos
!
ip routing
ip routing vrf ARELION
ip routing vrf CLOUDFLARE
ip routing vrf GOOGLE
ip routing vrf NETFLIX
no ip routing vrf OOB
ip routing vrf SEGRA
ip routing vrf UNITI
ip routing vrf XBOX
ip routing vrf ZOOM
```

### IPv6 Routing

#### IPv6 Routing Summary

| VRF | Routing Enabled |
| --- | --------------- |
| default | False |
| ARELION | False |
| CLOUDFLARE | False |
| GOOGLE | False |
| NETFLIX | False |
| OOB | False |
| SEGRA | False |
| UNITI | False |
| XBOX | False |
| ZOOM | False |

### Static Routes

#### Static Routes Summary

| VRF | Destination Prefix | Next Hop IP | Exit interface | Administrative Distance | Tag | Route Name | Metric |
| --- | ------------------ | ----------- | -------------- | ----------------------- | --- | ---------- | ------ |
| CLOUDFLARE | 1.0.0.1/32 | 10.255.0.9 | - | 1 | - | - | - |
| CLOUDFLARE | 1.1.1.1/32 | 10.255.0.9 | - | 1 | - | - | - |
| CLOUDFLARE | 104.16.0.1/32 | 10.255.0.9 | - | 1 | - | - | - |
| GOOGLE | 8.8.4.4/32 | 10.255.0.7 | - | 1 | - | - | - |
| GOOGLE | 8.8.8.8/32 | 10.255.0.7 | - | 1 | - | - | - |
| GOOGLE | 142.250.0.1/32 | 10.255.0.7 | - | 1 | - | - | - |
| GOOGLE | 172.217.0.1/32 | 10.255.0.7 | - | 1 | - | - | - |
| NETFLIX | 23.246.0.1/32 | 10.255.0.11 | - | 1 | - | - | - |
| NETFLIX | 45.57.0.1/32 | 10.255.0.11 | - | 1 | - | - | - |
| NETFLIX | 198.38.96.1/32 | 10.255.0.11 | - | 1 | - | - | - |
| OOB | 0.0.0.0/0 | 192.168.128.254 | - | 1 | - | - | - |
| XBOX | 208.67.222.222/32 | 10.255.0.13 | - | 1 | - | - | - |
| ZOOM | 9.9.9.9/32 | 10.255.0.15 | - | 1 | - | - | - |

#### Static Routes Device Configuration

```eos
!
ip route vrf CLOUDFLARE 1.0.0.1/32 10.255.0.9
ip route vrf CLOUDFLARE 1.1.1.1/32 10.255.0.9
ip route vrf CLOUDFLARE 104.16.0.1/32 10.255.0.9
ip route vrf GOOGLE 8.8.4.4/32 10.255.0.7
ip route vrf GOOGLE 8.8.8.8/32 10.255.0.7
ip route vrf GOOGLE 142.250.0.1/32 10.255.0.7
ip route vrf GOOGLE 172.217.0.1/32 10.255.0.7
ip route vrf NETFLIX 23.246.0.1/32 10.255.0.11
ip route vrf NETFLIX 45.57.0.1/32 10.255.0.11
ip route vrf NETFLIX 198.38.96.1/32 10.255.0.11
ip route vrf OOB 0.0.0.0/0 192.168.128.254
ip route vrf XBOX 208.67.222.222/32 10.255.0.13
ip route vrf ZOOM 9.9.9.9/32 10.255.0.15
```

### Router BGP

ASN Notation: asplain

#### Router BGP Summary

| BGP AS | Router ID |
| ------ | --------- |
| 65000 | 100.64.255.0 |

#### BGP Neighbors

| Neighbor | Remote AS | VRF | Shutdown | Send-community | Maximum-routes | Maximum-accepted-routes | Maximum-advertised-routes | Allowas-in | BFD | RIB Pre-Policy Retain | Route-Reflector Client | Passive | TTL Max Hops |
| -------- | --------- | --- | -------- | -------------- | -------------- | ----------------------- | ------------------------- | ---------- | --- | --------------------- | ---------------------- | ------- | ------------ |
| 198.51.100.1 | 3791 | ARELION | False | - | - | - | - | - | - | - | - | - | - |
| 2601::1 | 3791 | ARELION | False | - | - | - | - | - | - | - | - | - | - |
| 10.99.12.1 | 13760 | ARELION | False | - | - | - | - | - | - | - | - | - | - |
| 10.99.13.1 | 2711 | ARELION | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.101.1 | 15169 | ARELION | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.104.1 | 2906 | ARELION | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.102.0 | 13760 | CLOUDFLARE | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.101.0 | 1299 | GOOGLE | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.104.0 | 1299 | NETFLIX | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.105.0 | 13760 | NETFLIX | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.106.0 | 2711 | NETFLIX | False | - | - | - | - | - | - | - | - | - | - |
| 198.51.100.5 | 3791 | SEGRA | False | - | - | - | - | - | - | - | - | - | - |
| 2603::1 | 3791 | SEGRA | False | - | - | - | - | - | - | - | - | - | - |
| 10.99.13.0 | 1299 | SEGRA | False | - | - | - | - | - | - | - | - | - | - |
| 10.99.23.0 | 13760 | SEGRA | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.103.1 | 8075 | SEGRA | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.106.1 | 2906 | SEGRA | False | - | - | - | - | - | - | - | - | - | - |
| 198.51.100.3 | 3791 | UNITI | False | - | - | - | - | - | - | - | - | - | - |
| 2602::1 | 3791 | UNITI | False | - | - | - | - | - | - | - | - | - | - |
| 10.99.12.0 | 1299 | UNITI | False | - | - | - | - | - | - | - | - | - | - |
| 10.99.23.1 | 2711 | UNITI | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.102.1 | 13335 | UNITI | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.105.1 | 2906 | UNITI | False | - | - | - | - | - | - | - | - | - | - |
| 10.98.103.0 | 2711 | XBOX | False | - | - | - | - | - | - | - | - | - | - |

#### Router BGP VRFs

| VRF | Route-Distinguisher | Redistribute | Graceful Restart |
| --- | ------------------- | ------------ | ---------------- |
| ARELION | - | connected | - |
| CLOUDFLARE | - | static | - |
| GOOGLE | - | static | - |
| NETFLIX | - | static | - |
| SEGRA | - | connected | - |
| UNITI | - | connected | - |
| XBOX | - | static | - |
| ZOOM | 100.64.255.0:500 | static | - |

#### Router BGP Device Configuration

```eos
!
router bgp 65000
   router-id 100.64.255.0
   !
   vrf ARELION
      router-id 100.64.255.1
      neighbor 10.98.101.1 remote-as 15169
      neighbor 10.98.101.1 local-as 1299 no-prepend replace-as
      neighbor 10.98.101.1 description GOOGLE (AS15169) content peering
      neighbor 10.98.104.1 remote-as 2906
      neighbor 10.98.104.1 local-as 1299 no-prepend replace-as
      neighbor 10.98.104.1 description NETFLIX (AS2906) content peering
      neighbor 10.99.12.1 remote-as 13760
      neighbor 10.99.12.1 local-as 1299 no-prepend replace-as
      neighbor 10.99.12.1 description UNITI (AS13760) transit mesh
      neighbor 10.99.13.1 remote-as 2711
      neighbor 10.99.13.1 local-as 1299 no-prepend replace-as
      neighbor 10.99.13.1 description SEGRA (AS2711) transit mesh
      neighbor 198.51.100.1 remote-as 3791
      neighbor 198.51.100.1 local-as 1299 no-prepend replace-as
      neighbor 198.51.100.1 description ALPHA-EDGE-01 (AS3791)
      neighbor 2601::1 remote-as 3791
      neighbor 2601::1 local-as 1299 no-prepend replace-as
      neighbor 2601::1 description ALPHA-EDGE-01 (AS3791) IPv6
      redistribute connected
      !
      address-family ipv4
         neighbor 10.98.101.1 activate
         neighbor 10.98.104.1 activate
         neighbor 10.99.12.1 activate
         neighbor 10.99.13.1 activate
         neighbor 198.51.100.1 activate
      !
      address-family ipv6
         neighbor 2601::1 activate
   !
   vrf CLOUDFLARE
      neighbor 10.98.102.0 remote-as 13760
      neighbor 10.98.102.0 local-as 13335 no-prepend replace-as
      neighbor 10.98.102.0 description UNITI (AS13760) content peering
      redistribute static
      !
      address-family ipv4
         neighbor 10.98.102.0 activate
   !
   vrf GOOGLE
      neighbor 10.98.101.0 remote-as 1299
      neighbor 10.98.101.0 local-as 15169 no-prepend replace-as
      neighbor 10.98.101.0 description ARELION (AS1299) content peering
      redistribute static
      !
      address-family ipv4
         neighbor 10.98.101.0 activate
   !
   vrf NETFLIX
      neighbor 10.98.104.0 remote-as 1299
      neighbor 10.98.104.0 local-as 2906 no-prepend replace-as
      neighbor 10.98.104.0 description ARELION (AS1299) content peering
      neighbor 10.98.105.0 remote-as 13760
      neighbor 10.98.105.0 local-as 2906 no-prepend replace-as
      neighbor 10.98.105.0 description UNITI (AS13760) content peering
      neighbor 10.98.106.0 remote-as 2711
      neighbor 10.98.106.0 local-as 2906 no-prepend replace-as
      neighbor 10.98.106.0 description SEGRA (AS2711) content peering
      redistribute static
      !
      address-family ipv4
         neighbor 10.98.104.0 activate
         neighbor 10.98.105.0 activate
         neighbor 10.98.106.0 activate
   !
   vrf SEGRA
      router-id 100.64.255.3
      neighbor 10.98.103.1 remote-as 8075
      neighbor 10.98.103.1 local-as 2711 no-prepend replace-as
      neighbor 10.98.103.1 description XBOX (AS8075) content peering
      neighbor 10.98.106.1 remote-as 2906
      neighbor 10.98.106.1 local-as 2711 no-prepend replace-as
      neighbor 10.98.106.1 description NETFLIX (AS2906) content peering
      neighbor 10.99.13.0 remote-as 1299
      neighbor 10.99.13.0 local-as 2711 no-prepend replace-as
      neighbor 10.99.13.0 description ARELION (AS1299) transit mesh
      neighbor 10.99.23.0 remote-as 13760
      neighbor 10.99.23.0 local-as 2711 no-prepend replace-as
      neighbor 10.99.23.0 description UNITI (AS13760) transit mesh
      neighbor 198.51.100.5 remote-as 3791
      neighbor 198.51.100.5 local-as 2711 no-prepend replace-as
      neighbor 198.51.100.5 description BETA-EDGE-01 (AS3791)
      neighbor 2603::1 remote-as 3791
      neighbor 2603::1 local-as 2711 no-prepend replace-as
      neighbor 2603::1 description BETA-EDGE-01 (AS3791) IPv6
      redistribute connected
      !
      address-family ipv4
         neighbor 10.98.103.1 activate
         neighbor 10.98.106.1 activate
         neighbor 10.99.13.0 activate
         neighbor 10.99.23.0 activate
         neighbor 198.51.100.5 activate
      !
      address-family ipv6
         neighbor 2603::1 activate
   !
   vrf UNITI
      router-id 100.64.255.2
      neighbor 10.98.102.1 remote-as 13335
      neighbor 10.98.102.1 local-as 13760 no-prepend replace-as
      neighbor 10.98.102.1 description CLOUDFLARE (AS13335) content peering
      neighbor 10.98.105.1 remote-as 2906
      neighbor 10.98.105.1 local-as 13760 no-prepend replace-as
      neighbor 10.98.105.1 description NETFLIX (AS2906) content peering
      neighbor 10.99.12.0 remote-as 1299
      neighbor 10.99.12.0 local-as 13760 no-prepend replace-as
      neighbor 10.99.12.0 description ARELION (AS1299) transit mesh
      neighbor 10.99.23.1 remote-as 2711
      neighbor 10.99.23.1 local-as 13760 no-prepend replace-as
      neighbor 10.99.23.1 description SEGRA (AS2711) transit mesh
      neighbor 198.51.100.3 remote-as 3791
      neighbor 198.51.100.3 local-as 13760 no-prepend replace-as
      neighbor 198.51.100.3 description ALPHA-EDGE-01 (AS3791)
      neighbor 2602::1 remote-as 3791
      neighbor 2602::1 local-as 13760 no-prepend replace-as
      neighbor 2602::1 description ALPHA-EDGE-01 (AS3791) IPv6
      redistribute connected
      !
      address-family ipv4
         neighbor 10.98.102.1 activate
         neighbor 10.98.105.1 activate
         neighbor 10.99.12.0 activate
         neighbor 10.99.23.1 activate
         neighbor 198.51.100.3 activate
      !
      address-family ipv6
         neighbor 2602::1 activate
   !
   vrf XBOX
      neighbor 10.98.103.0 remote-as 2711
      neighbor 10.98.103.0 local-as 8075 no-prepend replace-as
      neighbor 10.98.103.0 description SEGRA (AS2711) content peering
      redistribute static
      !
      address-family ipv4
         neighbor 10.98.103.0 activate
   !
   vrf ZOOM
      rd 100.64.255.0:500
      route-target export vpn-ipv4 65000:500
      redistribute static
```

## VRF Instances

### VRF Instances Summary

| VRF Name | IP Routing |
| -------- | ---------- |
| ARELION | enabled |
| CLOUDFLARE | enabled |
| GOOGLE | enabled |
| NETFLIX | enabled |
| OOB | disabled |
| SEGRA | enabled |
| UNITI | enabled |
| XBOX | enabled |
| ZOOM | enabled |

### VRF Instances Device Configuration

```eos
!
vrf instance ARELION
   description Arelion (AS1299)
!
vrf instance CLOUDFLARE
   description Cloudflare (AS13335) - leaked into UNITI
!
vrf instance GOOGLE
   description Google (AS15169) - leaked into ARELION
!
vrf instance NETFLIX
   description Netflix (AS2906) - leaked into SEGRA
!
vrf instance OOB
!
vrf instance SEGRA
   description Segra (AS2711)
!
vrf instance UNITI
   description Uniti Fiber (AS13760)
!
vrf instance XBOX
   description Xbox Live - leaked into ARELION
!
vrf instance ZOOM
   description Zoom - leaked into UNITI
```
