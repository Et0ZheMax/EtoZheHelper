# Loki / Vector logs

## Vector file source idea

```toml
[sources.app_logs]
type = "file"
include = ["/var/log/app/*.log"]
read_from = "end"

[transforms.parse]
type = "remap"
inputs = ["app_logs"]
source = '''
. = parse_json!(.message)
'''

[sinks.loki]
type = "loki"
inputs = ["parse"]
endpoint = "http://loki:3100"
encoding.codec = "json"

[sinks.loki.labels]
job = "app"
host = "{{ host }}"
```

## Что важно

- не превращать high-cardinality поля в labels;
- labels: service, environment, host;
- request_id лучше хранить в message/json, не label;
- настроить retention;
- маскировать секреты.
