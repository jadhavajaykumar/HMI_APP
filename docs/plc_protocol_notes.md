# PLC Protocol Interoperability Notes (Siemens + Keyence)

## Quick answer

Yes, you can use a **single Modbus TCP protocol** for both Siemens and Keyence **if** both PLCs are configured to expose/consume Modbus registers/coils.

- Keyence KV series commonly supports Modbus TCP directly.
- Siemens S7 can use Modbus TCP via CPU features (model-dependent) or MB_SERVER/MB_CLIENT logic (or communication module).

If Siemens is not configured for Modbus, you need protocol translation on either PLC or HMI side (e.g., keep Siemens on S7/OPC UA and Keyence on Modbus).

## Current app behavior (from repository)

This HMI app already supports multiple drivers selected by connection profile:

- `modbus`
- `siemens_s7` (Snap7)
- `opcua`
- `simulator`

The active profile is selected in `config/tags.json` under `active_connection`, and each profile has independent tag bindings.

## Addressing model in this app

### 1) Modbus profile (`driver = modbus`)

Tag `area` values used by the app:

- `holding_register` (16-bit words)
- `coil` (single-bit bool)

Tag `address` is a **zero-based offset** used directly in read/write requests.

### 2) Siemens S7 profile (`driver = siemens_s7`)

Tag `area` values:

- `dbw` for word access (DB word offset in bytes)
- `dbx` for bit access using encoded integer: `byte * 100 + bit`
  - Example: `1010` means DBX10.2? No — in this app it means byte 10, bit 10 (invalid). Valid bit must be 0..7.
  - Correct example: `1002` means byte 10, bit 2.

> Note: The driver validates DBX bit index must be 0..7.

### 3) OPC UA profile (`driver = opcua`)

Tag `area` is `opcua_node`, and `address` is the node id string (`ns=...;s=...`).

## Can Siemens + Keyence share one Modbus map?

Yes, with constraints:

1. Pick one canonical HMI map (for example):
   - Status words: holding registers 0..99
   - Recipe words: holding registers 100..199
   - Commands: coils 0..63
2. In each PLC program, map internal variables to those Modbus addresses.
3. Keep datatype agreement strict (bit vs 16-bit word, signed vs unsigned).
4. Use one offset convention consistently across engineering and app docs.

## Important offset convention warning

Vendors/tools often display Modbus addresses as:

- Coil `00001`
- Holding `40001`

But protocol calls use a numeric **offset**. This app passes `address` directly as offset. So if PLC docs say `40001`, app address is typically `0` (depending on PLC editor convention). Validate this once with a test tag before commissioning.

## If you want one unified Modbus setup (recommended steps)

### PLC side

1. **Keyence**
   - Enable Modbus TCP server.
   - Bind required words/bits to register/coil offsets.

2. **Siemens**
   - Enable/provision Modbus TCP support (CPU function blocks or module).
   - Create explicit DB variables for HMI exchange.
   - Map DB variables to Modbus register/coil offsets to match Keyence logical map.

3. Freeze and document a single address contract table (`tag`, `type`, `modbus area`, `offset`, scaling, R/W).

### App side

1. Use `driver = modbus` profiles for both PLCs (separate profile per PLC IP).
2. Keep same `tag_catalog` names across profiles.
3. In `tag_bindings`, set `holding_register`/`coil` addresses per profile.
4. Verify every writable tag uses supported Modbus areas (`coil`, `holding_register`).

## If unified Modbus is not feasible

Use mixed protocol profiles (already supported by app):

- Keyence via `modbus`
- Siemens via `siemens_s7` or `opcua`

Then maintain per-profile tag bindings so the same logical tag names map to different protocol addresses/node ids.

## Repository-specific implementation limits to keep in mind

1. Modbus driver currently reads/writes one point at a time (no batching).
2. Modbus areas implemented: only `coil` and `holding_register`.
3. Modbus writes cast register values with `int(value)` (16-bit semantics expected).
4. Siemens S7 driver supports only `dbw` (word) and `dbx` (bit) in one configured DB number.
5. `TagDefinition.address` is typed as `int`, while OPC UA binding addresses are strings (works at runtime in current flow, but type model is inconsistent).

## Suggested next engineering update

- Add an explicit `address_type`/`address` union in model validation so OPC UA string addresses are first-class and Modbus/S7 numeric offsets remain validated.
- Add protocol-specific lint in settings import/export:
  - Modbus: only `coil`/`holding_register` + integer offsets.
  - Siemens: `dbx` encoded bit index 0..7 and `dbw` even-byte word offsets.
- Add a commissioning checklist screen/report with live read/write test per tag.