# Security

## Threat model

This application controls physical hardware (SolarEdge inverters) via Modbus TCP. There is no authentication on the Modbus protocol — anyone with network access to the inverter can read and write registers.

### Attack surface

- **Modbus TCP**: Unencrypted, unauthenticated. An attacker on the LAN can impersonate the controller or directly write to inverter registers.
- **evcc API**: Unauthenticated HTTP. A compromised evcc instance or man-in-the-middle could feed false price data, causing the controller to throttle or kill PV output unnecessarily.
- **Environment variables**: `INVERTERS` and `EVCC_URL` contain network addresses. The `.env` file should not be committed to version control.

### Mitigations

- Deploy on an isolated VLAN or subnet with the inverter(s) and evcc instance.
- Do not expose the Modbus port or evcc API to the internet.
- The controller only writes `ActivePowerLimit` (0-100%) — it cannot damage the inverter or override hardware safety limits.
- On shutdown or crash, the inverter reverts to 100% output (safe default).

## Reporting a vulnerability

If you discover a security issue, please report it privately via [GitHub Security Advisories](https://github.com/nickels/solardege-modulator/security/advisories/new) rather than opening a public issue.
