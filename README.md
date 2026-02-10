# 3WiFi WPS PIN Generator

Standalone Python port of the [3WiFi WPS PIN generator](https://3wifi.stascorp.com/wpspin).

Generates WPS PINs for wireless routers based on their BSSID (MAC address) using known vendor-specific algorithms.

> **[🇹🇷 Türkçe](README.tr.md)**

## Features

- **40+ PIN generation algorithms** — D-Link, ASUS, Belkin, EasyBox, Livebox, Airocon, Broadcom, Realtek, and more
- **MAC prefix matching** — Automatically selects relevant algorithms based on the device's OUI
- **Multiple input formats** — Accepts `AA:BB:CC:DD:EE:FF`, `AA-BB-CC-DD-EE-FF`, `AABBCCDDEEFF`
- **Serial number support** — For algorithms that derive PINs from both MAC and S/N (Belkin, EasyBox, Livebox)
- **No dependencies** — Pure Python 3, no external packages required

## Usage

```bash
# Suggest PINs based on known MAC prefixes
python3 wpspin.py AA:BB:CC:DD:EE:FF

# Try all algorithms (not just prefix matches)
python3 wpspin.py AABBCCDDEEFF --all

# With serial number (for Belkin, EasyBox, Livebox)
python3 wpspin.py AA:BB:CC:DD:EE:FF --sn 1234
```

### Example Output

```
$ python3 wpspin.py 00:14:D1:11:22:33

WPS PIN suggestions for 00:14:D1:11:22:33

11228677  |  24-bit PIN
22891587  |  D-Link PIN
56098419  |  D-Link PIN +1
95661469  |  Static PIN - Realtek 1
48563710  |  Static PIN - Realtek 3
```

## Supported Algorithms

| Algorithm | Type | Description |
|-----------|------|-------------|
| 24/28/32/36/40/44/48-bit | MAC | PIN derived from last N bits of MAC |
| Reverse byte/nibble/bits | MAC | PIN from reversed MAC representations |
| D-Link | MAC | D-Link specific XOR algorithm |
| D-Link +1 | MAC | D-Link algorithm on MAC+1 |
| ASUS | MAC | ASUS specific byte-sum algorithm |
| Airocon Realtek | MAC | Airocon/Realtek byte-pair algorithm |
| Belkin | MAC+SN | DSL universal algorithm (Stas'M) |
| EasyBox | MAC+SN | Vodafone EasyBox variant |
| Livebox | MAC+SN | Orange Livebox Arcadyan variant |
| Inv NIC / NIC×2 / NIC×3 | MAC | NIC-based transformations |
| OUI±NIC / OUI⊕NIC | MAC | OUI and NIC arithmetic operations |
| Cisco, Broadcom 1-6, Realtek 1-3, etc. | Static | Known default PINs for specific vendors |

## Credits

- Original JavaScript implementation by **Stas'M** and contributors
- Source: [3wifi.stascorp.com/wpspin](https://3wifi.stascorp.com/wpspin)
- Python port by [**fr0stb1rd**](https://fr0stb1rd.gitlab.io/), verified against original JS with 525 cross-verification tests

## Disclaimer

This tool is provided for educational and research purposes only. The author does not condone the use of this tool for any malicious or unauthorized activities. Users are responsible for complying with all applicable laws and regulations.

## License

Licensed under the [MIT License](LICENSE).
