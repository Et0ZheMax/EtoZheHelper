# SNMP printers

## Проверка snmpwalk

```bash
snmpwalk -v2c -c public 10.0.0.50 1.3.6.1.2.1.1
```

## Типовые OID

```text
1.3.6.1.2.1.1.1.0    sysDescr
1.3.6.1.2.1.1.5.0    sysName
1.3.6.1.2.1.43       printer MIB
```

## Что собирать

- online/offline;
- модель;
- hostname;
- расходники;
- счётчики страниц;
- ошибки;
- состояние очереди.

## Типовые проблемы

- SNMP выключен на принтере;
- community не public;
- firewall;
- SNMP v3 вместо v2c;
- устройство отвечает частично.
