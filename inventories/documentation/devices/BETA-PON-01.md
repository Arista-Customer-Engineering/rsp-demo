# BETA-PON-01

## Table of Contents

- [Management](#management)
  - [Management Interfaces](#management-interfaces)
  - [Management API HTTP](#management-api-http)
- [Authentication](#authentication)
  - [Local Users](#local-users)
- [VLANs](#vlans)
  - [VLANs Summary](#vlans-summary)
  - [VLANs Device Configuration](#vlans-device-configuration)
- [Interfaces](#interfaces)
  - [Ethernet Interfaces](#ethernet-interfaces)
  - [VLAN Interfaces](#vlan-interfaces)
- [Routing](#routing)
  - [IP Routing](#ip-routing)
  - [IPv6 Routing](#ipv6-routing)
  - [Static Routes](#static-routes)
- [VRF Instances](#vrf-instances)
  - [VRF Instances Summary](#vrf-instances-summary)
  - [VRF Instances Device Configuration](#vrf-instances-device-configuration)

## Management

### Management Interfaces

#### Management Interfaces Summary

##### IPv4

| Management Interface | Description | Type | VRF | IP Address | Gateway |
| -------------------- | ----------- | ---- | --- | ---------- | ------- |
| Management0 | OOB Management | oob | OOB | 192.168.128.240/24 | 192.168.128.254 |

##### IPv6

| Management Interface | Description | Type | VRF | IPv6 Address | IPv6 Gateway | ND RA Disabled | ND RA RX Accept | ND Managed Config Flag | ND Other Config Flag | ND Cache | ND RA DNS Servers |
| -------------------- | ----------- | ---- | --- | ------------ | ------------ | -------------- | --------------- | ---------------------- | -------------------- | -------- | ----------------- |
| Management0 | OOB Management | oob | OOB | - | - | - | - | - | - | - | - |

#### Management Interfaces Device Configuration

```eos
!
interface Management0
   description OOB Management
   vrf OOB
   ip address 192.168.128.240/24
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

## VLANs

### VLANs Summary

| VLAN ID | Name | Trunk Groups |
| ------- | ---- | ------------ |
| 1001 | PUBLIC_DATA | - |
| 1002 | CGNAT_DATA | - |
| 1003 | MGMT | - |

### VLANs Device Configuration

```eos
!
vlan 1001
   name PUBLIC_DATA
   state active
!
vlan 1002
   name CGNAT_DATA
   state active
!
vlan 1003
   name MGMT
   state active
```

## Interfaces

### Ethernet Interfaces

#### Ethernet Interfaces Summary

##### L2

| Interface | Description | Mode | VLANs | Native VLAN | Trunk Group | Channel-Group |
| --------- | ----------- | ---- | ----- | ----------- | ----------- | ------------- |
| Ethernet3 | PUBLIC-CUSTOMER | access | 1001 | - | - | - |
| Ethernet4 | CGNAT-CUSTOMER | access | 1002 | - | - | - |

*Inherited from Port-Channel Interface

##### Flexible Encapsulation Interfaces

| Interface | Description | Vlan ID | Client Encapsulation | Client Inner Encapsulation | Client VLAN | Client Outer VLAN Tag | Client Inner VLAN Tag | Network Encapsulation | Network Inner Encapsulation | Network VLAN | Network Outer VLAN Tag | Network Inner VLAN Tag |
| --------- | ----------- | ------- | -------------------- | -------------------------- | ----------- | --------------------- | --------------------- | --------------------- | --------------------------- | ------------ | ---------------------- | ---------------------- |
| Port-Channel1.1001 | CPE PUBLIC | 1001 | dot1q | - | 1001 | - | - | - | - | - | - | - |
| Port-Channel1.1002 | CPE CGNAT | 1002 | dot1q | - | 1002 | - | - | - | - | - | - | - |
| Port-Channel1.1003 | PON Management | 1003 | dot1q | - | 1003 | - | - | - | - | - | - | - |

#### Ethernet Interfaces Device Configuration

```eos
!
interface Ethernet1
   description BETA-PE-01 Uplink
   no shutdown
   channel-group 1 mode active
!
interface Ethernet2
   description BETA-PE-02 Uplink
   no shutdown
   channel-group 1 mode active
!
interface Ethernet3
   description PUBLIC-CUSTOMER
   no shutdown
   switchport access vlan 1001
   switchport mode access
   switchport
!
interface Ethernet4
   description CGNAT-CUSTOMER
   no shutdown
   switchport access vlan 1002
   switchport mode access
   switchport
!
interface Port-Channel1
   description PON SHELF EVPN A/A UPLINK
   no shutdown
   no switchport
!
interface Port-Channel1.1001
   description CPE PUBLIC
   vlan id 1001
   encapsulation vlan
      client dot1q 1001
!
interface Port-Channel1.1002
   description CPE CGNAT
   vlan id 1002
   encapsulation vlan
      client dot1q 1002
!
interface Port-Channel1.1003
   description PON Management
   vlan id 1003
   encapsulation vlan
      client dot1q 1003
```

### VLAN Interfaces

#### VLAN Interfaces Summary

| Interface | Description | VRF | MTU | Shutdown |
| --------- | ----------- | --- | --- | -------- |
| vlan1003 | - | PON_MGMT | - | False |

##### IPv4

| Interface | VRF | IP Address | IP Address Virtual | IP Router Virtual Address | ACL In | ACL Out |
| --------- | --- | ---------- | ------------------ | ------------------------- | ------ | ------- |
| vlan1003 | PON_MGMT | 172.31.255.1/24 | - | - | - | - |

#### VLAN Interfaces Device Configuration

```eos
!
interface vlan1003
   no shutdown
   vrf PON_MGMT
   ip address 172.31.255.1/24
```

## Routing

### IP Routing

#### IP Routing Summary

| VRF | Routing Enabled |
| --- | --------------- |
| default | True |
| DATA | True |
| OOB | False |
| PON_MGMT | True |
| VOICE | True |

#### IP Routing Device Configuration

```eos
!
ip routing
ip routing vrf DATA
no ip routing vrf OOB
ip routing vrf PON_MGMT
ip routing vrf VOICE
```

### IPv6 Routing

#### IPv6 Routing Summary

| VRF | Routing Enabled |
| --- | --------------- |
| default | False |
| DATA | True |
| OOB | False |
| PON_MGMT | True |
| VOICE | True |

#### IPv6 Routing Device Configuration

```eos
!
ipv6 unicast-routing vrf DATA
ipv6 unicast-routing vrf PON_MGMT
ipv6 unicast-routing vrf VOICE
```

### Static Routes

#### Static Routes Summary

| VRF | Destination Prefix | Next Hop IP | Exit interface | Administrative Distance | Tag | Route Name | Metric |
| --- | ------------------ | ----------- | -------------- | ----------------------- | --- | ---------- | ------ |
| OOB | 0.0.0.0/0 | - | 192.168.128.254 | 1 | - | - | - |
| PON_MGMT | 0.0.0.0/0 | - | 172.31.255.254 | 1 | - | - | - |

#### Static Routes Device Configuration

```eos
!
ip route vrf OOB 0.0.0.0/0 192.168.128.254
ip route vrf PON_MGMT 0.0.0.0/0 172.31.255.254
```

## VRF Instances

### VRF Instances Summary

| VRF Name | IP Routing |
| -------- | ---------- |
| DATA | enabled |
| OOB | disabled |
| PON_MGMT | enabled |
| VOICE | enabled |

### VRF Instances Device Configuration

```eos
!
vrf instance DATA
   description Customer CPE Data
!
vrf instance OOB
   description Out of Band
!
vrf instance PON_MGMT
   description PON Shelf Management
!
vrf instance VOICE
   description Customer CPE Voice
```
