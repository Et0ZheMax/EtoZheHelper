# tcpdump quick start

## DNS

```bash
sudo tcpdump -ni any port 53
```

## HTTP/HTTPS to host

```bash
sudo tcpdump -ni any host 10.0.0.10 and port 443
```

## SSH

```bash
sudo tcpdump -ni any port 22
```

## ICMP

```bash
sudo tcpdump -ni any icmp
```

## Запись в pcap

```bash
sudo tcpdump -ni any host 10.0.0.10 -w /tmp/capture.pcap
```

## Читать pcap

```bash
tcpdump -nn -r /tmp/capture.pcap
```

## Что искать

- SYN без SYN-ACK: порт закрыт/firewall/routing.
- DNS query без ответа: DNS/firewall.
- RST: сервис отказал или порт закрыт.
- TLS handshake fail: сертификаты/версии/proxy.
