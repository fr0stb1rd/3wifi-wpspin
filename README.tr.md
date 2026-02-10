# 3WiFi WPS PIN Üretici

[3WiFi WPS PIN üreticisinin](https://3wifi.stascorp.com/wpspin) bağımsız Python portu.

Kablosuz yönlendiriciler için BSSID (MAC adresi) kullanarak bilinen üreticiye özel algoritmalarla WPS PIN'leri üretir.

> **[🇬🇧 English](README.md)**

## Özellikler

- **40+ PIN üretim algoritması** — D-Link, ASUS, Belkin, EasyBox, Livebox, Airocon, Broadcom, Realtek ve daha fazlası
- **MAC ön eki eşleştirme** — Cihazın OUI'sine göre ilgili algoritmaları otomatik seçer
- **Birden fazla giriş formatı** — `AA:BB:CC:DD:EE:FF`, `AA-BB-CC-DD-EE-FF`, `AABBCCDDEEFF` kabul eder
- **Seri numarası desteği** — PIN'i hem MAC hem de S/N'den türeten algoritmalar için (Belkin, EasyBox, Livebox)
- **Bağımlılık yok** — Saf Python 3, harici paket gerektirmez

## Kullanım

```bash
# Bilinen MAC ön eklerine göre PIN öner
python3 wpspin.py AA:BB:CC:DD:EE:FF

# Tüm algoritmaları dene (sadece ön ek eşleşmeleri değil)
python3 wpspin.py AABBCCDDEEFF --all

# Seri numarası ile (Belkin, EasyBox, Livebox için)
python3 wpspin.py AA:BB:CC:DD:EE:FF --sn 1234
```

### Örnek Çıktı

```
$ python3 wpspin.py 00:14:D1:11:22:33

00:14:D1:11:22:33 için WPS PIN önerileri

11228677  |  24-bit PIN
22891587  |  D-Link PIN
56098419  |  D-Link PIN +1
95661469  |  Statik PIN - Realtek 1
48563710  |  Statik PIN - Realtek 3
```

## Desteklenen Algoritmalar

| Algoritma | Tür | Açıklama |
|-----------|-----|----------|
| 24/28/32/36/40/44/48-bit | MAC | PIN, MAC'in son N bitinden türetilir |
| Ters bayt/nibble/bit | MAC | Ters çevrilmiş MAC gösterimlerinden PIN |
| D-Link | MAC | D-Link'e özel XOR algoritması |
| D-Link +1 | MAC | MAC+1 üzerinde D-Link algoritması |
| ASUS | MAC | ASUS'a özel bayt toplama algoritması |
| Airocon Realtek | MAC | Airocon/Realtek bayt çifti algoritması |
| Belkin | MAC+SN | DSL evrensel algoritması (Stas'M) |
| EasyBox | MAC+SN | Vodafone EasyBox varyantı |
| Livebox | MAC+SN | Orange Livebox Arcadyan varyantı |
| Inv NIC / NIC×2 / NIC×3 | MAC | NIC tabanlı dönüşümler |
| OUI±NIC / OUI⊕NIC | MAC | OUI ve NIC aritmetik işlemleri |
| Cisco, Broadcom 1-6, Realtek 1-3, vb. | Statik | Belirli üreticiler için bilinen varsayılan PIN'ler |

## Katkıda Bulunanlar

- Orijinal JavaScript uygulaması **Stas'M** ve katkıda bulunanlar tarafından
- Kaynak: [3wifi.stascorp.com/wpspin](https://3wifi.stascorp.com/wpspin)
- Python portu [**fr0stb1rd**](https://fr0stb1rd.gitlab.io/) tarafından yapılmıştır, 525 çapraz doğrulama testi ile orijinal JS'ye karşı doğrulanmıştır

## Yasal Uyarı

Bu araç yalnızca eğitim ve araştırma amaçlıdır. Yazar, bu aracın kötü amaçlı veya yetkisiz faaliyetler için kullanılmasını tasvip etmemektedir. Kullanıcılar, yürürlükteki tüm yasalara ve düzenlemelere uymaktan sorumludur.

## Lisans

[MIT Lisansı](LICENSE) altında lisanslanmıştır.
