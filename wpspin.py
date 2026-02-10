#!/usr/bin/env python3
"""
WPS PIN Generator
Ported from 3WiFi WPS PIN generator (https://3wifi.stascorp.com/wpspin)
Original JavaScript implementation by Stas'M and contributors
"""

import sys
import argparse
from typing import List, Dict, Callable, Tuple


# Algorithm modes
ALGO_MAC = 0
ALGO_MACSN = 1
ALGO_EMPTY = 2
ALGO_STATIC = 3


def zero_fill(number: int, width: int) -> str:
    """Pad number with leading zeros to specified width"""
    s = str(number)
    if len(s) < width:
        return '0' * (width - len(s)) + s
    return s


def reverse(s: str) -> str:
    """Reverse a string"""
    return s[::-1]


def pin_checksum(pin: int) -> int:
    """Calculate WPS PIN checksum"""
    pin = pin % 10000000
    accum = 0
    t = pin
    
    while t:
        accum += 3 * (t % 10)
        t //= 10
        accum += t % 10
        t //= 10
    
    return (pin * 10) + ((10 - (accum % 10)) % 10)


def algo_dlink(mac: int) -> int:
    """D-Link PIN algorithm"""
    mac &= 0xFFFFFF
    mac ^= 0x55AA55
    mac ^= (((mac & 0xF) << 4) |
            ((mac & 0xF) << 8) |
            ((mac & 0xF) << 12) |
            ((mac & 0xF) << 16) |
            ((mac & 0xF) << 20))
    mac %= 10000000
    if mac < 1000000:
        mac += ((mac % 9) * 1000000) + 1000000
    return mac


def algo_dsl_mac_sn(mac: int, sn: str = '', init: Dict = None) -> int:
    """
    Universal DSL algorithm that derives PIN from MAC and S/N
    Used by Belkin, DSL-EasyBox, Arcadyan, and others
    Reverse-engineered by Stas'M
    """
    if init is None:
        init = {}
    
    if not sn:
        sn = ''
    
    # Pad or truncate S/N to 4 chars
    if len(sn) < 4:
        sn = sn.zfill(4)
    if len(sn) > 4:
        sn = sn[-4:]
    
    # Convert S/N to nibbles
    sn_nibbles = []
    for c in sn:
        try:
            x = int(c, 16)
        except ValueError:
            x = 0
        sn_nibbles.append(x)
    
    # Extract NIC nibbles from MAC
    nic = [
        (mac & 0xFFFF) >> 12,
        (mac & 0xFFF) >> 8,
        (mac & 0xFF) >> 4,
        mac & 0xF
    ]
    
    # Default init values
    bk1 = init.get('bk1', 60)
    bk2 = init.get('bk2', 195)
    k1_init = init.get('k1', 0)
    k2_init = init.get('k2', 0)
    pin_init = init.get('pin', 0)
    xor_init = init.get('xor', 0)
    sub_mode = init.get('sub', 0)
    sk = init.get('sk', 0)
    skv = init.get('skv', 0)
    bx = init.get('bx', [])
    
    # Calculate k1
    k1 = k1_init & 0xF
    i = 0
    while bk1:
        if bk1 & 1:
            k1 += nic[i] if i < 4 else sn_nibbles[i - 4]
            k1 &= 0xF
        bk1 >>= 1
        i += 1
    
    # Calculate k2
    k2 = k2_init & 0xF
    i = 0
    while bk2:
        if bk2 & 1:
            k2 += nic[i] if i < 4 else sn_nibbles[i - 4]
            k2 &= 0xF
        bk2 >>= 1
        i += 1
    
    # Calculate PIN
    pin = pin_init
    for bx_val in bx:
        xor = xor_init & 0xF
        i = 0
        bx_copy = bx_val
        while bx_copy:
            if bx_copy & 1:
                if i > 4:
                    xor ^= sn_nibbles[i - 4]
                elif i > 1:
                    xor ^= nic[i - 1]
                elif i > 0:
                    xor ^= k2
                else:
                    xor ^= k1
            bx_copy >>= 1
            i += 1
        pin <<= 4
        pin |= xor
    
    # Apply subtraction/addition mode
    if sub_mode == 0:
        return pin % 10000000
    elif sub_mode == 1:
        mult = k2 if sk > 1 else (k1 if sk > 0 else skv)
        return (pin % 10000000) - ((pin // 10000000) * mult)
    elif sub_mode == 2:
        mult = k2 if sk > 1 else (k1 if sk > 0 else skv)
        return (pin % 10000000) + ((pin // 10000000) * mult)
    
    return pin % 10000000


def algo_asus(mac: int) -> int:
    """ASUS PIN algorithm"""
    mac_str = zero_fill(hex(mac)[2:].upper(), 12)
    
    b = [int(mac_str[i:i+2], 16) for i in range(0, 12, 2)]
    
    pin = []
    for i in range(7):
        pin.append((b[i % 6] + b[5]) % (10 - ((i + b[1] + b[2] + b[3] + b[4] + b[5]) % 7)))
    
    return int(''.join(map(str, pin)))


def algo_airocon(mac: int) -> int:
    """Airocon Realtek PIN algorithm"""
    mac_str = zero_fill(hex(mac)[2:].upper(), 12)
    
    b = [int(mac_str[i:i+2], 16) for i in range(0, 12, 2)]
    
    return (((b[0] + b[1]) % 10) +
            (((b[5] + b[0]) % 10) * 10) +
            (((b[4] + b[5]) % 10) * 100) +
            (((b[3] + b[4]) % 10) * 1000) +
            (((b[2] + b[3]) % 10) * 10000) +
            (((b[1] + b[2]) % 10) * 100000) +
            (((b[0] + b[1]) % 10) * 1000000))


# Algorithm definitions
class Algorithm:
    def __init__(self, id: str, name: str, mode: int, func: Callable, prefixes: List[str] = None):
        self.id = id
        self.name = name
        self.mode = mode
        self.func = func
        self.prefixes = prefixes or []


# MAC prefix database (OUI) for each algorithm
# Extracted from the HTML textareas
# Note: Some prefixes are longer than 6 chars (partial MAC match beyond OUI)
MAC_PREFIXES = {
    'pin24': ['000CF6', '0014D1', '001CDF', '001F1F', '002275', '0022F7', '00265B', '0026CE',
              '00664B', '00A026', '00B00C', '00E020', '04BF6D', '081075', '087A4C', '08863B',
              '0E5D4E', '107BEF', '14A9E3', '14B968', '14D64D', '1C7EE5', '2008ED', '202BC1',
              '20CF30', '28285D', '2A285D', '308730', '32B2DC', '346BD3', '34BA9A', '381766',
              '404A03', '4C9EFF', '4CEDDE', '4E5D4E', '5067F0', '5C4CA9', '5CA39D', '5CF4AB',
              '62233D', '623CE4', '623DFF', '6253D4', '62559C', '626BD3', '627D5E', '6296BF',
              '62A8E4', '62B686', '62C06F', '62C61F', '62C714', '62CBA8', '62CDBE', '62E87B',
              '6416F0', '647002', '68B6CF', '6A1D67', '6A233D', '6A285D', '6A3DFF', '6A53D4',
              '6A559C', '6A6BD3', '6A7D5E', '6A96BF', '6AA8E4', '6AC06F', '6AC61F', '6AC714',
              '6ACBA8', '6ACDBE', '6AD15E', '6AD167', '721D67', '72233D', '723CE4', '723DFF',
              '7253D4', '72559C', '726BD3', '727D5E', '7296BF', '72A8E4', '72C06F', '72C61F',
              '72C714', '72CBA8', '72CDBE', '72D15E', '72E87B', '786A89', '788DF7', '801F02',
              '84C9B2', '88E3AB', '8E5D4E', '9094E4', '90E6BA', '9897D1', 'A0F3C1', 'AA285D',
              'B0487A', 'B0B2DC', 'B246FC', 'B4944E', 'BC1401', 'BCF685', 'C4A81D', 'C83A35',
              'C86C87', 'CC5D4E', 'CE5D4E', 'D46E5C', 'D4BF7F4', 'D86CE9', 'D8EB97', 'DC7144',
              'E04136', 'E0CB4E', 'E24136', 'E243F6', 'E47CF9', 'E8CD2D', 'EA285D', 'EC233D',
              'EC43F6', 'ECCB30', 'EE43F6', 'F2B2DC', 'F49FF3', 'F81A67', 'F8C091', 'F8D111',
              'FC7516', 'FCF528', 'FEF528'],

    'pin28': ['200BC7', '4846FB', 'D46AA8', 'F84ABF'],

    'pin32': ['000726', '1062EB', '10BF48', '14DAE9', '1C5F2B', '2CAB25', '3085A9', '48EE0C',
              '50465D', '5404A6', '801F02', '802689', '908D78', 'C86000', 'D8FEE3', 'E8CC18',
              'F46D04', 'FC8B97'],

    'pin36': [],
    'pin40': [],
    'pin44': [],
    'pin48': [],

    'pinDLink': ['0014D1', '14D64D', '1C7EE5', '28107B', '84C9B2', 'A0AB1B', 'B8A386',
                 'C0A0BB', 'CCB255', 'D8EB97', 'FC7516'],

    'pinDLink1': ['0014D1', '0018E7', '00195B', '001CF0', '001E58', '002191', '0022B0',
                  '002401', '00265A', '14D64D', '1C7EE5', '340804', '5CD998', '84C9B2',
                  'B8A386', 'C8BE19', 'C8D3A3', 'CCB255'],

    'pinBelkin': ['08863B', '94103E', 'B4750E', 'C05627', 'EC1A59'],

    'pinEasyBox': ['00264D', '38229D', '7C4FB5'],

    'pinLivebox': ['1883BF', '488D36', '4C09D4', '507E5D', '5CDC96', '743170', '849CA6',
                   '880355', '9C80DF', 'A8D3F7', 'D0052A', 'D463FE'],

    'pinASUS': ['00072624', '0008A1D3', '00177C', '001EA6', '00304FB', '00E04C0', '048D38',
                '049226', '04D9F5', '081077', '081078', '081079', '083E5D', '08606E', '0862669',
                '107B44', '10BF48', '10C37B', '10FEED3C', '14DDA9', '181E78', '1C4419', '1C872C',
                '1CB72C', '2420C7', '247F20', '2C56DC', '2CAB25', '2CFDA1', '305A3A', '3085A98C',
                '382C4A', '38D547', '3C1E04', '40167E', '40F201', '44E9DD', '48EE0C', '50465D',
                '5464D9', '54A050', '54B80A', '587BE906', '6045CB', '60A44C', '60D1AA21',
                '64517E', '64D954', '6C198F', '6C7220', '6CFDB9', '704D7B', '7062B8', '74D02B',
                '7824AF', '78542E', '78D99FD', '7C2664', '803F5DF6', '84A423', '88A6C6',
                '88D7F6', '8C10D4', '8C882B00', '904D4A', '907282', '90F65290', '94FBB2',
                '9C5C8E', 'A01B29', 'A0F3C1E', 'A8F7E00', 'AC220B', 'AC9E17', 'ACA213',
                'B06EBF', 'B85510', 'B8EE0E', 'BC3400', 'BC9680', 'BCEE7B', 'C0A0BB8C',
                'C412F5', 'C4A81D', 'C860007', 'C891F9', 'D00ED90', 'D017C2', 'D084B0',
                'D850E6', 'D8FEE3', 'E03F49', 'E4BEED', 'E894F6F6', 'E8CC18', 'EC1A5971',
                'EC2280', 'EC4C4D', 'F0795978', 'F42853', 'F43E61', 'F46BEF', 'F832E4',
                'F8AB05', 'F8E903F4', 'FC8B97'],

    'pinAirocon': ['0007262F', '000B2B4A', '000EF4E7', '001333B', '00177C', '001AEF',
                   '00E04BB3', '02101801', '0810734', '08107710', '1013EE0', '2CAB25C7',
                   '788C54', '803F5DF6', '94FBB2', 'BC9680', 'F43E61', 'FC8B97'],

    'pinEmpty': ['000E8F', '004A77', '0C96BF', '1062EB', '10BEF5', '1C5F2B', '20F3A3',
                 '2C957F', '344DEA', '38D82F', '3C9872', '54BE53', '58D56E', '64136C',
                 '68A0F6', '702E22', '709F2D', '74A78E', '74B57E', '74DADA', '788102',
                 '7894B4', '789682', '78F5FD', '7C3953', '802689', '88D274', '8C68C8',
                 '94A7B7', '981333', '9CD643', 'A0AB1B', 'ACE215', 'C8D15E', 'CAA366',
                 'D0608C', 'D42122', 'D460E3', 'D476EA', 'E06066', 'E46F13', 'EC2280'],

    'pinCisco': ['001A2B', '00248C', '002618', '344DEB', '7054F5', '7071BC', 'E06995',
                 'E0CB4E'],

    'pinBrcm1': ['001AA9', '14144B', '988B5D', 'ACF1DF', 'BCF685', 'C8D3A3', 'EC6264'],

    'pinBrcm2': ['14D64D', '1C7EE5', '28107B', '84C9B2', 'B8A386', 'BCF685', 'C8BE19'],

    'pinBrcm3': ['14D64D', '1C7EE5', '28107B', '7C034C', 'B8A386', 'BCF685', 'C8BE19'],

    'pinBrcm4': ['14D64D', '18622C', '1C7EE5', '204E7F', '28107B', '4C17EB', '7C03D8',
                 '84C9B2', 'B8A386', 'BCF685', 'C8BE19', 'C8D3A3', 'CCB255', 'D86CE9',
                 'FC7516'],

    'pinBrcm5': ['14D64D', '18622C', '1C7EE5', '204E7F', '28107B', '4C17EB', '7C03D8',
                 '84C9B2', 'B8A386', 'BCF685', 'C8BE19', 'C8D3A3', 'CCB255', 'D86CE9',
                 'FC7516'],

    'pinBrcm6': ['14D64D', '18622C', '1C7EE5', '204E7F', '28107B', '4C17EB', '7C03D8',
                 '84C9B2', 'B8A386', 'BCF685', 'C8BE19', 'C8D3A3', 'CCB255', 'D86CE9',
                 'FC7516'],

    'pinAirc1': ['181E78', '40F201', '44E9DD', 'D084B0'],

    'pinAirc2': ['84A423', '88A6C6', '8C10D4'],

    'pinDSL2740R': ['00265A', '1CBDB9', '340804', '5CD998', '84C9B2', 'FC7516'],

    'pinRealtek1': ['000C42', '000EE8', '0014D1'],

    'pinRealtek2': ['007263', 'E4BEED'],

    'pinRealtek3': ['08C6B3'],

    'pinUpvel': ['784476', 'D4BF7F0', 'F8C091'],

    'pinUR814AC': ['D4BF7F60'],

    'pinUR825AC': ['D4BF7F5'],

    'pinOnlime': ['0014D1', '144D67', '784476', 'D4BF7F', 'F8C091'],

    'pinEdimax': ['00E04C', '801F02'],

    'pinThomson': ['002624', '4432C8', '88F7C7', 'CC03FA'],

    'pinHG532x': ['00664B', '086361', '087A4C', '0C96BF', '14B968', '2008ED', '2469A5',
                  '346BD3', '786A89', '88E3AB', '9CC172', 'ACE215', 'CCA223', 'D07AB5',
                  'E8CD2D', 'F80113', 'F83DFF'],

    'pinH108L': ['4C09B4', '4CAC0A', '84742A4', '9CD24B', 'B075D5', 'C864C7', 'DC028E',
                 'FCC897'],

    'pinONO': ['5C353B', 'DC537C'],
}


def get_algorithms() -> List[Algorithm]:
    """Return list of all algorithms with their implementations"""
    algos = []
    
    # 24-bit PIN
    algos.append(Algorithm('pin24', '24-bit PIN', ALGO_MAC,
                          lambda mac: mac & 0xFFFFFF,
                          MAC_PREFIXES['pin24']))
    
    # 28-bit PIN  
    algos.append(Algorithm('pin28', '28-bit PIN', ALGO_MAC,
                          lambda mac: mac & 0xFFFFFFF,
                          MAC_PREFIXES['pin28']))
    
    # 32-bit PIN
    algos.append(Algorithm('pin32', '32-bit PIN', ALGO_MAC,
                          lambda mac: mac % 0x100000000,
                          MAC_PREFIXES['pin32']))
    
    # 36-bit PIN
    algos.append(Algorithm('pin36', '36-bit PIN', ALGO_MAC,
                          lambda mac: mac % 0x1000000000,
                          MAC_PREFIXES['pin36']))
    
    # 40-bit PIN
    algos.append(Algorithm('pin40', '40-bit PIN', ALGO_MAC,
                          lambda mac: mac % 0x10000000000,
                          MAC_PREFIXES['pin40']))
    
    # 44-bit PIN
    algos.append(Algorithm('pin44', '44-bit PIN', ALGO_MAC,
                          lambda mac: mac % 0x100000000000,
                          MAC_PREFIXES['pin44']))
    
    # 48-bit PIN
    algos.append(Algorithm('pin48', '48-bit PIN', ALGO_MAC,
                          lambda mac: mac,
                          MAC_PREFIXES['pin48']))
    
    # Reverse byte variants
    def pin24rh(mac):
        mac &= 0xFFFFFF
        mac_str = zero_fill(hex(mac)[2:], 6)
        return int(mac_str[4:6] + mac_str[2:4] + mac_str[0:2], 16)
    
    algos.append(Algorithm('pin24rh', 'Reverse byte 24-bit', ALGO_MAC, pin24rh, []))
    
    def pin32rh(mac):
        mac %= 0x100000000
        mac_str = zero_fill(hex(mac)[2:], 8)
        return int(mac_str[6:8] + mac_str[4:6] + mac_str[2:4] + mac_str[0:2], 16)
    
    algos.append(Algorithm('pin32rh', 'Reverse byte 32-bit', ALGO_MAC, pin32rh, []))
    
    def pin48rh(mac):
        mac_str = zero_fill(hex(mac)[2:], 12)
        return int(mac_str[10:12] + mac_str[8:10] + mac_str[6:8] + 
                  mac_str[4:6] + mac_str[2:4] + mac_str[0:2], 16)
    
    algos.append(Algorithm('pin48rh', 'Reverse byte 48-bit', ALGO_MAC, pin48rh, []))
    
    # Reverse nibble variants
    def pin24rn(mac):
        mac &= 0xFFFFFF
        mac_str = zero_fill(hex(mac)[2:], 6)
        return int(reverse(mac_str), 16)
    
    algos.append(Algorithm('pin24rn', 'Reverse nibble 24-bit', ALGO_MAC, pin24rn, []))
    
    def pin32rn(mac):
        mac %= 0x100000000
        mac_str = zero_fill(hex(mac)[2:], 8)
        return int(reverse(mac_str), 16)
    
    algos.append(Algorithm('pin32rn', 'Reverse nibble 32-bit', ALGO_MAC, pin32rn, []))
    
    def pin48rn(mac):
        mac_str = zero_fill(hex(mac)[2:], 12)
        return int(reverse(mac_str), 16)
    
    algos.append(Algorithm('pin48rn', 'Reverse nibble 48-bit', ALGO_MAC, pin48rn, []))
    
    # Reverse bits variants
    def pin24rb(mac):
        mac &= 0xFFFFFF
        mac_str = bin(mac)[2:].zfill(24)
        return int(reverse(mac_str), 2)
    
    algos.append(Algorithm('pin24rb', 'Reverse bits 24-bit', ALGO_MAC, pin24rb, []))
    
    def pin32rb(mac):
        mac %= 0x100000000
        mac_str = bin(mac)[2:].zfill(32)
        return int(reverse(mac_str), 2)
    
    algos.append(Algorithm('pin32rb', 'Reverse bits 32-bit', ALGO_MAC, pin32rb, []))
    
    def pin48rb(mac):
        mac_str = bin(mac)[2:].zfill(48)
        return int(reverse(mac_str), 2)
    
    algos.append(Algorithm('pin48rb', 'Reverse bits 48-bit', ALGO_MAC, pin48rb, []))
    
    # D-Link algorithms
    algos.append(Algorithm('pinDLink', 'D-Link PIN', ALGO_MAC,
                          algo_dlink,
                          MAC_PREFIXES['pinDLink']))
    
    algos.append(Algorithm('pinDLink1', 'D-Link PIN +1', ALGO_MAC,
                          lambda mac: algo_dlink(mac + 1),
                          MAC_PREFIXES['pinDLink1']))
    
    # Belkin algorithm
    algos.append(Algorithm('pinBelkin', 'Belkin PIN', ALGO_MACSN,
                          lambda mac, sn='': algo_dsl_mac_sn(mac, sn, {'bx': [66, 129, 209, 10, 24, 3, 39]}),
                          MAC_PREFIXES['pinBelkin']))
    
    # EasyBox algorithm
    def easybox_pin(mac, sn=''):
        if not sn:
            sn = str(mac & 0xFFFF)
        return algo_dsl_mac_sn(mac, sn, {'bx': [129, 65, 6, 10, 136, 80, 33]})
    
    algos.append(Algorithm('pinEasyBox', 'Vodafone EasyBox', ALGO_MACSN,
                          easybox_pin,
                          MAC_PREFIXES['pinEasyBox']))
    
    # Livebox algorithm
    algos.append(Algorithm('pinLivebox', 'Livebox Arcadyan', ALGO_MACSN,
                          lambda mac, sn='': algo_dsl_mac_sn(mac - 2, sn, {'bx': [129, 65, 6, 10, 136, 80, 33]}),
                          MAC_PREFIXES['pinLivebox']))
    
    # ASUS algorithm
    algos.append(Algorithm('pinASUS', 'ASUS PIN', ALGO_MAC,
                          algo_asus,
                          MAC_PREFIXES['pinASUS']))
    
    # Airocon algorithm
    algos.append(Algorithm('pinAirocon', 'Airocon Realtek', ALGO_MAC,
                          algo_airocon,
                          MAC_PREFIXES['pinAirocon']))
    
    # Inv NIC
    algos.append(Algorithm('pinInvNIC', 'Inv NIC to PIN', ALGO_MAC,
                          lambda mac: (~mac) & 0xFFFFFF,
                          []))
    
    # NIC multipliers
    algos.append(Algorithm('pinNIC2', 'NIC * 2', ALGO_MAC,
                          lambda mac: (mac & 0xFFFFFF) * 2,
                          []))
    
    algos.append(Algorithm('pinNIC3', 'NIC * 3', ALGO_MAC,
                          lambda mac: (mac & 0xFFFFFF) * 3,
                          []))
    
    # OUI operations
    def oui_add_nic(mac):
        mac_str = zero_fill(hex(mac)[2:], 12)
        oui = int(mac_str[0:6], 16)
        nic = int(mac_str[6:12], 16)
        return (oui + nic) % 0x1000000
    
    algos.append(Algorithm('pinOUIaddNIC', 'OUI + NIC', ALGO_MAC, oui_add_nic, []))
    
    def oui_sub_nic(mac):
        mac_str = zero_fill(hex(mac)[2:], 12)
        oui = int(mac_str[0:6], 16)
        nic = int(mac_str[6:12], 16)
        if nic < oui:
            return oui - nic
        else:
            return (oui + 0x1000000 - nic) & 0xFFFFFF
    
    algos.append(Algorithm('pinOUIsubNIC', 'OUI - NIC', ALGO_MAC, oui_sub_nic, []))
    
    def oui_xor_nic(mac):
        mac_str = zero_fill(hex(mac)[2:], 12)
        oui = int(mac_str[0:6], 16)
        nic = int(mac_str[6:12], 16)
        return oui ^ nic
    
    algos.append(Algorithm('pinOUIxorNIC', 'OUI ^ NIC', ALGO_MAC, oui_xor_nic, []))
    
    # Empty PIN
    algos.append(Algorithm('pinEmpty', 'Empty PIN', ALGO_EMPTY,
                          lambda mac: '',
                          MAC_PREFIXES['pinEmpty']))
    
    # Static PINs
    algos.append(Algorithm('pinCisco', 'Cisco', ALGO_STATIC,
                          lambda mac: 1234567,
                          MAC_PREFIXES['pinCisco']))
    
    algos.append(Algorithm('pinBrcm1', 'Broadcom 1', ALGO_STATIC,
                          lambda mac: 2017252,
                          MAC_PREFIXES['pinBrcm1']))
    
    algos.append(Algorithm('pinBrcm2', 'Broadcom 2', ALGO_STATIC,
                          lambda mac: 4626484,
                          MAC_PREFIXES['pinBrcm2']))
    
    algos.append(Algorithm('pinBrcm3', 'Broadcom 3', ALGO_STATIC,
                          lambda mac: 7622990,
                          MAC_PREFIXES['pinBrcm3']))
    
    algos.append(Algorithm('pinBrcm4', 'Broadcom 4', ALGO_STATIC,
                          lambda mac: 6232714,
                          MAC_PREFIXES['pinBrcm4']))
    
    algos.append(Algorithm('pinBrcm5', 'Broadcom 5', ALGO_STATIC,
                          lambda mac: 1086411,
                          MAC_PREFIXES['pinBrcm5']))
    
    algos.append(Algorithm('pinBrcm6', 'Broadcom 6', ALGO_STATIC,
                          lambda mac: 3195719,
                          MAC_PREFIXES['pinBrcm6']))
    
    algos.append(Algorithm('pinAirc1', 'Airocon 1', ALGO_STATIC,
                          lambda mac: 3043203,
                          MAC_PREFIXES['pinAirc1']))
    
    algos.append(Algorithm('pinAirc2', 'Airocon 2', ALGO_STATIC,
                          lambda mac: 7141225,
                          MAC_PREFIXES['pinAirc2']))
    
    algos.append(Algorithm('pinDSL2740R', 'DSL-2740R', ALGO_STATIC,
                          lambda mac: 6817554,
                          MAC_PREFIXES['pinDSL2740R']))
    
    algos.append(Algorithm('pinRealtek1', 'Realtek 1', ALGO_STATIC,
                          lambda mac: 9566146,
                          MAC_PREFIXES['pinRealtek1']))
    
    algos.append(Algorithm('pinRealtek2', 'Realtek 2', ALGO_STATIC,
                          lambda mac: 9571911,
                          MAC_PREFIXES['pinRealtek2']))
    
    algos.append(Algorithm('pinRealtek3', 'Realtek 3', ALGO_STATIC,
                          lambda mac: 4856371,
                          MAC_PREFIXES['pinRealtek3']))
    
    algos.append(Algorithm('pinUpvel', 'Upvel', ALGO_STATIC,
                          lambda mac: 2085483,
                          MAC_PREFIXES['pinUpvel']))
    
    algos.append(Algorithm('pinUR814AC', 'UR-814AC', ALGO_STATIC,
                          lambda mac: 4397768,
                          MAC_PREFIXES['pinUR814AC']))
    
    algos.append(Algorithm('pinUR825AC', 'UR-825AC', ALGO_STATIC,
                          lambda mac: 529417,
                          MAC_PREFIXES['pinUR825AC']))
    
    algos.append(Algorithm('pinOnlime', 'Onlime', ALGO_STATIC,
                          lambda mac: 9995604,
                          MAC_PREFIXES['pinOnlime']))
    
    algos.append(Algorithm('pinEdimax', 'Edimax', ALGO_STATIC,
                          lambda mac: 3561153,
                          MAC_PREFIXES['pinEdimax']))
    
    algos.append(Algorithm('pinThomson', 'Thomson', ALGO_STATIC,
                          lambda mac: 6795814,
                          MAC_PREFIXES['pinThomson']))
    
    algos.append(Algorithm('pinHG532x', 'HG532x', ALGO_STATIC,
                          lambda mac: 3425928,
                          MAC_PREFIXES['pinHG532x']))
    
    algos.append(Algorithm('pinH108L', 'H108L', ALGO_STATIC,
                          lambda mac: 9422988,
                          MAC_PREFIXES['pinH108L']))
    
    algos.append(Algorithm('pinONO', 'CBN ONO', ALGO_STATIC,
                          lambda mac: 9575521,
                          MAC_PREFIXES['pinONO']))
    
    return algos


def gen_pin(mac: int, sn: str, algo: Algorithm) -> str:
    """Generate PIN using specified algorithm"""
    if algo.mode == ALGO_MACSN:
        result = algo.func(mac, sn)
    else:
        result = algo.func(mac)
    
    if isinstance(result, str):
        return result
    
    # Apply checksum and format
    result = pin_checksum(result)
    return zero_fill(str(result), 8)


def pin_suggest(bssid: str, sn: str = '', get_all: bool = False) -> List[Tuple[str, str]]:
    """
    Suggest WPS PINs for a given BSSID
    
    Args:
        bssid: MAC address (various formats accepted)
        sn: Serial number (optional, for some algorithms)
        get_all: If True, try all algorithms; if False, only try matching prefixes
    
    Returns:
        List of (pin, algorithm_name) tuples
    """
    # Clean and parse MAC address
    mac_clean = bssid.replace(':', '').replace('-', '').replace('.', '').replace(' ', '').upper()
    
    try:
        mac = int(mac_clean, 16)
    except ValueError:
        return []
    
    if mac > 0xFFFFFFFFFFFF:
        return []
    
    results = []
    algos = get_algorithms()
    
    for algo in algos:
        match = get_all
        
        if not get_all and algo.prefixes:
            # Check if MAC matches any prefix for this algorithm
            for prefix in algo.prefixes:
                if mac_clean.startswith(prefix):
                    match = True
                    break
        
        if match:
            pin = gen_pin(mac, sn, algo)
            
            if algo.mode == ALGO_STATIC:
                results.append((pin, f'Static PIN - {algo.name}'))
            else:
                results.append((pin, algo.name))
    
    return results


def format_mac(mac: int) -> str:
    """Format MAC address as XX:XX:XX:XX:XX:XX"""
    mac_str = zero_fill(hex(mac)[2:].upper(), 12)
    return ':'.join(mac_str[i:i+2] for i in range(0, 12, 2))


def main():
    parser = argparse.ArgumentParser(
        description='WPS PIN Generator - Generate WPS PINs from BSSID/MAC address',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s 00:11:22:33:44:55              # Suggest PINs based on known prefixes
  %(prog)s 001122334455 --all             # Try all algorithms
  %(prog)s 00:11:22:33:44:55 --sn 1234   # With serial number
        '''
    )
    
    parser.add_argument('bssid', help='BSSID/MAC address (various formats accepted)')
    parser.add_argument('--sn', default='', help='Serial number (for some algorithms)')
    parser.add_argument('--all', action='store_true', help='Try all algorithms instead of only matching prefixes')
    
    args = parser.parse_args()
    
    results = pin_suggest(args.bssid, args.sn, args.all)
    
    if not results:
        print('No PINs found or invalid MAC address')
        return 1
    
    # Parse MAC for display
    mac_clean = args.bssid.replace(':', '').replace('-', '').replace('.', '').replace(' ', '').upper()
    mac_int = int(mac_clean, 16)
    mac_formatted = format_mac(mac_int)
    
    print(f'\nWPS PIN suggestions for {mac_formatted}\n')
    
    for pin, algo_name in results:
        if pin == '':
            pin = '<empty>'
        print(f'{pin:8s}  |  {algo_name}')
    
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
