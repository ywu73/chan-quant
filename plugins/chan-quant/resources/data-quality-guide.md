# Data quality guide

Data modes are not interchangeable:

| Mode | Meaning | Main warning |
| --- | --- | --- |
| `synthetic` | Deterministic demonstration input | It is mock data, not market evidence |
| `csv` | User-supplied offline daily bars | User owns authorization and adjustment declaration |
| `snapshot` | Immutable local package with manifest and bars hash | Integrity does not prove licensing or economics |
| `sina` / observed | Backend remote adapter | Undocumented fields, no SLA, no redistribution grant |

For a snapshot, `integrity=MATCH` means the manifest hash matches the current `bars.csv`; it does not establish provider authorization or strategy validity. For market breadth, `COMPLETE/PARTIAL/FAILED` describes observation coverage, not a trading signal.

