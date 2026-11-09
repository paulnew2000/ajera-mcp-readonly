# Ajera MCP Server — Read-Only

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes the **Deltek Ajera** project accounting API as AI tools. Ask your AI assistant questions about your projects, employees, timesheets, financials, and more — all in plain English.

> **Read-only by design.** No data can be created, modified, or deleted. Safe to run with a restricted API service account.

---

## What You Can Ask

Once connected, you can ask your AI assistant things like:

- *"Which active projects haven't been modified in the last 30 days?"*
- *"Show me all timesheets for the week of May 5th that haven't been submitted yet."*
- *"What are the chargeable phases for project 1042?"*
- *"List all active vendors with unpaid invoices."*
- *"What GL accounts are in the Expense account group?"*
- *"Show journal entries for October and the debit/credit lines for a selected entry."*
- *"Give me full details on employees in the Austin department."*
- *"List all active projects and their billing type and total contract amount."*
- *"Who is the project manager on job 4210.000?"*
- *"Which active projects are billed as Fixed Fee and have a total contract over $500,000?"*

---

## Coverage

Read tools cover the following domains, including API v2 journal-entry reads
added in version 2.1.0:

| Domain | Tools |
|---|---|
| **Projects** | List, get full detail, get totals, get with resources, list chargeable phases |
| **Project Templates** | List, get full detail |
| **Clients** | List, get full detail, list client types |
| **Contacts** | List, get full detail, list contact types |
| **Employees** | List, get full detail (incl. email), list employee types |
| **Timesheets** | List, get full detail, list non-work days |
| **GL Accounts** | List, get with balances |
| **Journal Entries** | List headers with date/company/basis/void filters; get posting lines |
| **Expense Reports** | List, get full detail, download attachments |
| **Vendors** | List, get full detail, list vendor types |
| **Vendor Invoices** | List, get full detail |
| **Reference / Lookup** | Account groups, activities, bank accounts, companies, deductions, departments, fringes, invoice formats, marketing stages & dispositions, overhead groups, payroll taxes, pay types, rate tables, wage tables |

See [`API_CAPABILITY_INVENTORY.md`](API_CAPABILITY_INVENTORY.md) for the complete verified field reference, including response shapes, argument keys, and known API quirks.

---

## Requirements

- Python 3.11 or later
- A Deltek Ajera instance (cloud/SaaS or on-premises)
- An Ajera API service account (see [API User Setup](#api-user-setup) below)
- An MCP-capable AI client (Claude Desktop, VS Code with Copilot, etc.)

---

## Installation

```bash
git clone https://github.com/paulnew2000/ajera-mcp-readonly.git
cd ajera-mcp-readonly
pip install -e .
```

---

## Configuration

### 1. Set environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
AJERA_API_URL=https://ajera.com/VXXXXXX/AjeraAPI.ashx?id=XXXXXXXX
AJERA_USERNAME=your_api_username
AJERA_PASSWORD=your_api_password
```

Your API URL is found in Ajera under **Utility → Setup → Integrations → API Settings**.

> ⚠️ Never commit your `.env` file. It is listed in `.gitignore`.

### 2. Configure your MCP client

Copy `.mcp.json.example` to `.mcp.json` and update the path and credentials:

```json
{
  "mcpServers": {
    "ajera": {
      "command": "python",
      "args": ["/path/to/ajera-mcp-readonly/server.py"],
      "env": {
        "AJERA_API_URL": "https://ajera.com/VXXXXXX/AjeraAPI.ashx?id=XXXXXXXX",
        "AJERA_USERNAME": "your_api_username",
        "AJERA_PASSWORD": "your_api_password"
      }
    }
  }
}
```

For **Claude Desktop**, add this block to:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

---

## API User Setup

1. In Ajera, go to **Utility → Setup → Integrations → API Settings**
2. Create a dedicated API user (do not use an employee login)
3. Enable **only the read permissions** your use case requires
4. Save — you will be prompted for your password to confirm

> **SaaS note:** Permission changes in hosted Ajera may take several minutes to propagate. If a newly-enabled method still fails, wait 5–10 minutes before troubleshooting.

Recommended read-only permissions to enable (matches this server's tool set):

- Projects: Get, List
- Project Templates: Get, List
- Project Totals: Get
- Projects With Resources: Get
- Clients: Get, List
- Client Types: List
- Contacts: Get, List
- Contact Types: List
- Employees: Get, List
- Employee Types: List
- Timesheets: Get, List, List Non Work Days
- GL Accounts: Get, List
- Journal Entries: Get, List (requires an Ajera version supporting these v2 methods)
- Expense Reports: Get, List, Download
- Vendors: Get, List
- Vendor Types: List
- Vendor Invoices: Get, List
- Account Groups / Activities / Bank Accounts / Companies / Deductions / Departments / Fringes / Invoice Formats / Marketing Stages & Dispositions / Overhead Groups / Payroll Taxes / Pays / Rate Tables / Wage Tables: List

---

## Verification

Run the offline contract tests with synthetic HTTP responses (no credentials or
live connection required):

```bash
pip install -e ".[test]"
python -m pytest
```

The older reference-endpoint script makes **live read requests** using your
configured API credentials:

```bash
python test_new_endpoints.py
```

It covers the original additional reference endpoints, not the new journal-entry
tools. It reports record counts and may print sample data; run it only where
that output is appropriate.

## Journal Entries

Enable **List Journal Entries** and **Get Journal Entries** for your API user.
The client routes both methods to API v2 automatically. Two tools are available:

- `list_journal_entries`: optional inclusive `earliest_date`/`latest_date`
  (`YYYY-MM-DD`), `company_keys`, `basis` (`Accrual`, `Cash`, `Both`, or empty
  for all), and `voided` (true, false, or null for both statuses).
- `get_journal_entry`: a nonempty list of positive `journal_entry_keys` from
  the list tool. Returns headers and visible debit/credit lines. Requests are
  deduplicated and batched in groups of five to limit large API responses;
  five is a client batch size, not a claimed API maximum.

The list tool returns `JournalEntries`, `ReturnedCount`, `Limit` and
`PossiblyTruncated`, with a warning when 500 entries are returned. **The API
applies its 500-entry cap before pagination.** Split accounting-date windows
and deduplicate by key; paging alone cannot establish complete history. If a
single day still reaches 500, partition further by company, basis or void
status, or report that completeness is unresolved.

List uses space-separated fields such as `Journal Entry Key`; Get uses
camelCase such as `JournalEntryKey`. Preserve reversal metadata from List,
since Get may omit it. Missing debit/credit sides can be treated as zero for
arithmetic. Some entries omit account/department fields; voided entries may
have no visible lines. These reads do not establish complete coverage of all
GL transaction sources.

Large opaque update snapshots are removed from Get output. API errors and
missing requested keys are surfaced as failures; partial batches are not
silently presented as complete. This server exposes only journal-entry reads.

---

## Known Limitations

- **Expense reports are user-scoped** — the API user can only access its own expense reports. Use Ajera's ODBC connection for cross-user expense data.
- **`ListTimesheets` has a 500-record cap per call** — silently truncates. Use date windows of 7 days or fewer for organizations with many employees.
- **`GetEmployees` batch limit of 50 keys** — the tool handles batching automatically.
- **`GetProjectTotals` is one project at a time** — the API accepts a single scalar key per call.
- **`ListChargeablePhases` requires a project key** — call once per project.
- **GL detail coverage is partial** — GL account tools return balance snapshots;
  journal-entry tools return selected entries and posting lines, with the
  omissions described above. Other GL transaction sources are not covered.
- **No write operations** — this server is intentionally read-only.
- **`ProjectManager` on project records is a nested dict**, not a plain string — shape is `{"EmployeeKey": int, "FirstName": str, "MiddleName": str, "LastName": str}`. Extract name as `FirstName + " " + LastName`.
- **`GetProjects` batch size** — tested safely at 25 keys per call across a full production set (~1,146 active projects) with zero errors. Larger batches are untested; stay at ≤25 for bulk operations.

---

## API Documentation

For field-level documentation including response shapes, argument keys, version requirements, and quirks discovered during development:

- [`API_CAPABILITY_INVENTORY.md`](API_CAPABILITY_INVENTORY.md) — complete verified endpoint reference
- [Deltek Ajera API Reference](https://help.deltek.com/Product/Ajera/api/)

---

## Contributing

Issues and pull requests are welcome. If you discover new API quirks, undocumented fields, or argument keys not covered here, please open an issue or submit a PR updating `API_CAPABILITY_INVENTORY.md`.

---

## License

MIT — see [LICENSE](LICENSE).
