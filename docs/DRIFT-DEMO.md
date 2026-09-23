# Timestamp-unit drift: reproducible example

Fortinet's [log field documentation](https://docs.fortinet.com/document/fortigate/7.4.4/fortios-log-message-reference/357866/log-message-fields) includes an epoch-seconds example. Its [event-time technical note](https://community.fortinet.com/fortigate-3/technical-tip-event-time-display-in-the-logs-94022) includes epoch-nanosecond values. These establish that both representations exist; they do not establish a particular firmware upgrade transition on our hardware.

The two `samples/fortigate-epoch-*.log` fixtures are **constructed, documented-format examples** with lab identity and documentation IP addresses. They are not captured production logs or proof that a specific firmware version renamed a field. The timestamp precision changes while the key set stays the same.

1. Register a fresh replay source. Ingest `samples/fortigate-epoch-seconds.log` through file upload or HTTP. The built-in parser establishes a baseline.
2. Ingest `samples/fortigate-epoch-nanoseconds.log` under the **same** source ID. Its event-time unit fingerprint differs, so the event is quarantined as `drifted` despite a compatible broad adapter.
3. In Parser Lab, inspect the raw `eventtime` and derived `eventtime_utc`, and map the latter to `time`. Validate the source IP and timestamp against sample expectations.
4. Approve with a reviewer name. Replay the retained event.
5. Inspect revision 1 (`drifted`) and revision 2 (`normalized`). Download the original bytes and verify the Merkle proof. The original integer retains nanosecond precision; the derived ISO timestamp is truncated to Python's microsecond precision.

Automated end-to-end proof: `python -m pytest tests/test_vendor_drift.py -v`.

Upgrade note: FortiGate records containing `eventtime` now include timestamp-unit information in their fingerprint. Existing parsers for those records require review under the new fingerprint. Historical raw bytes, signed bundles and revisions are retained.
