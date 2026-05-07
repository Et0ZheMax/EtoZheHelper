from app.actions.models import ActionDefinition, ActionParamDefinition

SERVICE = ActionParamDefinition(type="string", kind="service", description="systemd unit name")
NAME = ActionParamDefinition(type="string", kind="safe_name", description="safe hostname, IP address, or DNS name", maximum=253)
URL = ActionParamDefinition(type="string", kind="url", description="http:// or https:// URL")
PORT = ActionParamDefinition(type="integer", kind="port", description="TCP port number", minimum=1, maximum=65535)
LINES = ActionParamDefinition(type="integer", kind="lines", description="number of tail lines", required=False, default=100, minimum=20, maximum=500)
CONTAINER = ActionParamDefinition(type="string", kind="container", description="Docker container name or id", maximum=128)
PRINTER = ActionParamDefinition(type="string", kind="printer", description="printer queue name", maximum=128)

_DEFINITIONS = [
    ActionDefinition("host_identity", "Show host identity", "Collect OS and host identity metadata.", "linux", "hostnamectl"),
    ActionDefinition("uptime_load", "Show uptime and load", "Collect uptime and load averages.", "linux", "uptime"),
    ActionDefinition("memory_snapshot", "Show memory snapshot", "Collect human-readable memory usage.", "linux", "free -h"),
    ActionDefinition("disk_usage", "Show disk usage", "Collect filesystem capacity usage.", "linux", "df -h"),
    ActionDefinition("inode_usage", "Show inode usage", "Collect filesystem inode usage.", "linux", "df -i"),
    ActionDefinition("failed_units", "List failed systemd units", "List failed systemd units without changing state.", "systemd", "systemctl --failed"),
    ActionDefinition("ip_addresses", "Show IP addresses", "Collect concise interface address information.", "network", "ip -br a"),
    ActionDefinition("routes", "Show routes", "Collect routing table information.", "network", "ip r"),
    ActionDefinition("tcp_probe", "Probe TCP connectivity", "Probe whether a TCP host and port accepts connections.", "network", "nc -vz {host} {port}", {"host": NAME, "port": PORT}),
    ActionDefinition("resolved_status", "Show systemd-resolved status", "Collect resolver status and DNS server information.", "dns", "resolvectl status"),
    ActionDefinition("dns_query", "Query DNS name", "Resolve a DNS name through systemd-resolved.", "dns", "resolvectl query {name}", {"name": NAME}),
    ActionDefinition("getent_hosts", "Query hosts database", "Resolve a name through NSS hosts lookup.", "dns", "getent hosts {name}", {"name": NAME}),
    ActionDefinition("curl_head", "Fetch HTTP headers", "Request HTTP response headers only.", "http_tls", "curl -I {url}", {"url": URL}),
    ActionDefinition("curl_timing", "Measure HTTP timing", "Collect curl timing phases without response body.", "http_tls", "curl -sS -o /dev/null -w 'code=%{http_code} dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} total=%{time_total}\\n' {url}", {"url": URL}),
    ActionDefinition("systemd_status", "Check systemd service status", "Inspect systemd service status without changing service state.", "systemd", "systemctl status {service} --no-pager", {"service": SERVICE}),
    ActionDefinition("systemd_cat", "Show systemd unit file", "Inspect the resolved systemd unit configuration.", "systemd", "systemctl cat {service}", {"service": SERVICE}),
    ActionDefinition("journal_tail", "Tail systemd journal", "Read recent service journal entries.", "systemd", "journalctl -u {service} -n {lines} --no-pager", {"service": SERVICE, "lines": LINES}, needs_sudo=True),
    ActionDefinition("list_listening_ports", "List listening TCP ports", "List listening TCP sockets and owning processes.", "network", "ss -lntp"),
    ActionDefinition("docker_ps", "List running Docker containers", "List running Docker containers.", "docker", "docker ps", needs_sudo=True),
    ActionDefinition("docker_ps_all", "List all Docker containers", "List all Docker containers including stopped ones.", "docker", "docker ps -a", needs_sudo=True),
    ActionDefinition("docker_logs_tail", "Tail Docker container logs", "Read recent Docker logs for one container.", "docker", "docker logs --tail={lines} {container}", {"container": CONTAINER, "lines": LINES}, needs_sudo=True),
    ActionDefinition("docker_system_df", "Show Docker disk usage", "Show Docker disk usage summary.", "docker", "docker system df", needs_sudo=True),
    ActionDefinition("cups_status", "Check CUPS service status", "Inspect CUPS systemd status.", "cups", "systemctl status cups --no-pager"),
    ActionDefinition("lpstat_all", "Show printer status", "List CUPS printers and queues.", "cups", "lpstat -t"),
    ActionDefinition("printer_queue", "Show printer queue", "Inspect one CUPS printer queue.", "cups", "lpq -P {printer}", {"printer": PRINTER}),
]

ACTION_CATALOG: dict[str, ActionDefinition] = {definition.key: definition for definition in _DEFINITIONS}


def list_action_definitions() -> list[ActionDefinition]:
    return list(_DEFINITIONS)


def get_action_definition(key: str) -> ActionDefinition | None:
    return ACTION_CATALOG.get(key)
