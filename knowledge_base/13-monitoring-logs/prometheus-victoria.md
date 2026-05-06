# Prometheus / VictoriaMetrics

## Prometheus scrape idea

```yaml
scrape_configs:
  - job_name: "node"
    static_configs:
      - targets:
          - "host1:9100"
          - "host2:9100"
```

## Метрики, которые нужны почти всегда

```text
up
node_cpu_seconds_total
node_memory_MemAvailable_bytes
node_filesystem_avail_bytes
node_filesystem_files_free
node_load1
process_resident_memory_bytes
http_requests_total
http_request_duration_seconds
```

## Примеры PromQL

CPU:

```promql
100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

Disk free:

```promql
node_filesystem_avail_bytes / node_filesystem_size_bytes * 100
```

Service up:

```promql
up == 0
```
