# Changelog

## 2.1.0 — 2026-11-08

- Add read-only `list_journal_entries` and `get_journal_entry` MCP tools with
  automatic API v2 routing and validated accounting-date, company, basis and
  void-status filters.
- Flag potentially truncated lists at the API's 500-entry cap; document why
  pagination cannot retrieve entries beyond that cap.
- Retrieve selected entries in small batches, remove opaque update snapshots,
  and reject incomplete or erroneous responses instead of presenting partial
  data as complete.
- Replace the old statement that journal-entry detail is unavailable with
  the verified read capabilities and their remaining field/coverage limits.
- Add synthetic HTTP contract tests, MCP tool/schema checks and explicit wheel
  module selection. Constrain the MCP dependency to the compatible 1.x SDK;
  SDK 2.x removed the FastMCP import used by this server.
- Use the documented `EndAPISession` method for session cleanup.
- Suppress HTTP INFO logs that otherwise include the API connection URL.

GL account and balance reads predate this release. No business-write tools are
included in this server.
