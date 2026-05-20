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
- *"Give me full details on employees in the Austin department."*
- *"List all active projects and their billing type and total contract amount."*
- *"Who is the project manager on job 4210.000?"*
- *"Which active projects are billed as Fixed Fee and have a total contract over $500,000?"*

---

## Coverage

All 46 readable Ajera API endpoints are implemented across every domain:

| Domain | Tools |
|---|---|
| **Projects** | List, get full detail, get totals, get with resources, list chargeable phases |
| **Project Templates** | List, get full detail |
| **Clients** | List, get full detail, list client types |
| **Contacts** | List, get full detail, list contact types |
| **Employees** | List, get full detail (incl. email), list employee types |
| **Timesheets** | List, get full detail, list non-work days |
| **GL Accounts** | List, get with balances |
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
- Expense Reports: Get, List, Download
- Vendors: Get, List
- Vendor Types: List
- Vendor Invoices: Get, List
- Account Groups / Activities / Bank Accounts / Companies / Deductions / Departments / Fringes / Invoice Formats / Marketing Stages & Dispositions / Overhead Groups / Payroll Taxes / Pays / Rate Tables / Wage Tables: List

---

## Verification

Run the included test script to verify your API connection and confirm all endpoints are working:

```bash
python test_new_endpoints.py
```

Expected output: 24 new endpoints passing with record counts and sample data.

---

## Known Limitations

- **Expense reports are user-scoped** — the API user can only access its own expense reports. Use Ajera's ODBC connection for cross-user expense data.
- **`ListTimesheets` has a 500-record cap per call** — silently truncates. Use date windows of 7 days or fewer for organizations with many employees.
- **`GetEmployees` batch limit of 50 keys** — the tool handles batching automatically.
- **`GetProjectTotals` is one project at a time** — the API accepts a single scalar key per call.
- **`ListChargeablePhases` requires a project key** — call once per project.
- **GL transaction detail is not available** — only balance snapshots via `GetGLAccounts`.
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
