# Ajera API Capability Inventory

Complete map of every method exposed by the Deltek Ajera API, based on the
API Settings permission screen. Columns:

- **Method** — exact name sent in the `Method` field of the JSON payload
- **Type** — Read or Write
- **Content Key** — top-level key in `Content` that holds the result array
- **v2 Required** — whether this method requires a v2 session token
- **MCP v2** — implemented in the read-only v2 MCP server
- **Notes** — quirks, filter names, known limitations

---

## Account Groups

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListAccountGroups` | Read | `AccountGroups` | No | ✓ | No filters needed |

---

## Activities

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListActivities` | Read | `Activities` | No | ✓ | Activity codes used on timesheets and expense lines |

---

## Attachment Categories

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListAttachmentCategories` | Read | `AttachmentCategories` | No | — | Read permission not tested — enable in API Settings to use |

---

## Bank Accounts

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListBankAccounts` | Read | `BankAccounts` | No | ✓ | Returns accounts used for expense reimbursements and AP |

---

## Chargeable Phases

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListChargeablePhases` | Read | `ChargeablePhases` | No | ✓ | **Requires `ProjectKey: int` (scalar, not array).** Returns flat hierarchy: Level 0 = project, Level 1+ = phases. Fields: `Key`, `Description`, `Level`, `Enabled`, `WBS`, `RequireNotes`. |

> ⚠️ `ListChargeablePhases` requires `ProjectKey` as a **scalar integer** — passing an array or omitting the argument returns "One or more properties contain invalid data". Call once per project.

---

## Clients

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListClients` | Read | `Clients` | No | ✓ | Filters: `FilterByStatus`, `FilterByNameLike`, `FilterByCompany`, `FilterByClientType`, date range |
| `GetClients` | Read | `Clients` | No | ✓ | `RequestedClients: [int...]`; returns full record including Contacts[] array |
| `UpdateClients` | Write | — | No | — | Requires `UpdatedClients` + `UnchangedClients` for concurrency; links contacts via Contacts[] not ContactClientKey |

---

## Client Types

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListClientTypes` | Read | `ClientTypes` | No | ✓ | Filter: `FilterByStatus` |

---

## Companies

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListCompanies` | Read | `Companies` | No | ✓ | Returns companies in multi-company Ajera instances |

---

## Contacts

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListContacts` | Read | `Contacts` | No | ✓ | Filters: `FilterByStatus`, `FilterByNameLike`, `FilterByClient` |
| `GetContacts` | Read | `Contacts` | No | ✓ | `RequestedContacts: [int...]` |
| `UpdateContacts` | Write | — | No | — | Create with `ContactKey: -1`; one new contact per call; global name uniqueness enforced |

---

## Contact Types

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListContactTypes` | Read | `ContactTypes` | No | ✓ | No filters; returns all active contact type keys and descriptions |

---

## Deductions

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListDeductions` | Read | `Deductions` | No | ✓ | Payroll deduction types configured in the system |

---

## Departments

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListDepartments` | Read | `Departments` | No | ✓ | Filter: `FilterByStatus` |

---

## Employee Types

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListEmployeeTypes` | Read | `EmployeeTypes` | No | ✓ | Filter: `FilterByStatus` |

---

## Employees

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListEmployees` | Read | `Employees` | No | ✓ | Returns summary only — does NOT include Email field |
| `GetEmployees` | Read | `Employees` | **v1 only** | ✓ | `RequestedEmployees: [int...]`; batch ≤50 keys per call — larger batches return RC=-100; includes Email |
| `UpdateEmployees` | Write | — | No | — | Write method — not covered by this server |

> ⚠️ `GetEmployees` requires a **v1** session even when the rest of the server uses v2.
> ⚠️ `ListEmployees` does not return the `Email` field — use `GetEmployees` for email.
> ℹ️ `GetEmployee` (singular, no "s") does not exist. Behavior when called varies by instance — some return `"Unauthorized method: GetEmployee"`; others return `ResponseCode: 200` with empty `Content` and no error. Either way, always use `GetEmployees` (plural).

---

## Expense Reports

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListExpenseReports` | Read | `ExpenseReports` | No | ✓ | API user sees **only its own** reports — not all users' |
| `GetExpenseReports` | Read | `ExpenseReports` | No | ✓ | `RequestedExpenseReports: [int...]` |
| `DownloadExpenseReports` | Read | *(file blob)* | No | ✓ | `FileKey: int`; returns base64 file data |
| `UpdateExpenseReports` | Write | — | No | — | Write method — not covered by this server |
| `UploadExpenseReports` | Write | — | No | — | Write method — not covered by this server |

> ⚠️ Expense report access is scoped to the API user — ODBC required for cross-user access.

---

## Fringes

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListFringes` | Read | `Fringes` | No | ✓ | Fringe benefit configurations |

---

## GL Accounts

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListGLAccounts` | Read | `GLAccounts` | No | ✓ | Filters: `FilterByStatus`, `FilterByAccountGroup`, `FilterByType` |
| `GetGLAccounts` | Read | `GLAccounts` | No | ✓ | Returns balances; `AsOfDate` uses MM/DD/YYYY format; no transaction-level detail |

> ⚠️ GL transaction detail (individual journal entries) is **not exposed** by the API.
> ⚠️ `AsOfDate` format is `MM/DD/YYYY`, not ISO.

---

## Invoice Formats

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListInvoiceFormats` | Read | `InvoiceFormats` | No | ✓ | Invoice template configurations |

---

## Marketing Final Dispositions

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListMarketingFinalDispositions` | Read | `MarketingFinalDispositions` | No | ✓ | Outcome types for marketing/pursuit tracking |

---

## Marketing Stages

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListMarketingStages` | Read | `MarketingStages` | No | ✓ | Pipeline stages for pursuit/opportunity tracking |

---

## Overhead Groups

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListOverheadGroups` | Read | `OverheadGroups` | No | ✓ | Overhead cost groupings used in indirect rate calculations |

---

## Payroll Taxes

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListPayrollTaxes` | Read | `PayrollTaxes` | No | ✓ | Payroll tax types configured in the system |

---

## Pays

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListPays` | Read | `Pays` | No | ✓ | Pay type codes (Regular, Overtime, G&A Pay, etc.) |

---

## Project Templates

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListProjectTemplates` | Read | `ProjectTemplates` | No | ✓ | Summary list of project templates |
| `GetProjectTemplates` | Read | `ProjectTemplates` | No | ✓ | **Argument key is `RequestedProjects: [int...]` (NOT `RequestedProjectTemplates`).** Returns full template with phases, budgets, billing type, and custom fields. |

---

## Project Totals

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `GetProjectTotals` | Read | `ProjectTotals` | No | ✓ | **`RequestedProjectTotals: int` (scalar integer, not array).** Financial summary per project: fees, WIP, billed amounts, costs. Returns 0 records for overhead/non-billable projects. |

> ⚠️ `RequestedProjectTotals` is a **scalar integer** — not an array, not `ProjectKey`. Passing an array or any other argument key returns "One or more properties contain invalid data". Call once per project.

---

## Project Types

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListProjectTypes` | Read | `ProjectTypes` | No | ✓ | Filter: `FilterByStatus` |

---

## Projects

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListProjects` | Read | `Projects` | No | ✓ | Filters: `FilterByStatus`, `FilterByNameLike`, `FilterByCompany`, `FilterByProjectType`, date range |
| `GetProjects` | Read | `Projects` | No | ✓ | `RequestedProjects: [int...]`; returns full project including phases |
| `CreateProjects` | Write | — | No | — | Write method — not covered by this server |
| `UpdateProjects` | Write | — | No | — | Write method — not covered by this server |

---

## Projects With Resources

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `GetProjectsWithResources` | Read | `Projects` | No | ✓ | Use `RequestedProjects: [int...]`. Returns full project record + Resources[] array per phase. Response shape identical to GetProjects with Resources array added. |
| `UpdateProjectsWithResources` | Write | — | No | — | Write method — not covered by this server |

---

## Rate Tables

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListRateTables` | Read | `RateTables` | No | ✓ | Billing rate table configurations |

---

## Timesheets

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListTimesheets` | Read | `Timesheets` | **Yes** | ✓ | 500-record cap per call — confirmed intentional; fetch week by week |
| `GetTimesheets` | Read | `Timesheets` | **Yes** | ✓ | `RequestedTimesheets: [int...]` |
| `ListTimesheetNonWorkDays` | Read | `NonWorkDays` | **Yes** | ✓ | Holidays and non-work days; filter by date range |
| `CreateTimesheet` | Write | — | Yes | — | Write method — not covered by this server. Payload must nest under `{"Timesheet": {"EmployeeKey": ..., "TimesheetDate": "..."}}` |
| `UpdateTimesheets` | Write | — | Yes | — | Write method — not covered by this server. **Row-level field names use spaces, not camelCase** (e.g. `"Project Key"`, `"Phase Key"`, `"Activity Key"`, `"D1 Regular"`, `"Timesheet Overhead Group Detail Key"`). `UnchangedData` (full record from GetTimesheets) goes inside the timesheet object alongside `UpdatedProjects`/`UpdatedOverheads`. |
| `SubmitTimesheets` | Write | — | Yes | — | Write method — not covered by this server |
| `EndTimesheetSessions` | Write | — | Yes | — | Write method — not covered by this server |

> ⚠️ All timesheet methods require a **v2** session token.
> ⚠️ `ListTimesheets` has a hard 500-record cap — **confirmed intentional** (shared code with the Manage Timesheets UI; not a silent bug). Deltek has entered a request to add a truncation warning to API responses. To decouple the API limit from the UI limit, submit an enhancement request to the [Ajera Ideas Portal](https://ideas.deltek.com/). Use 7-day date windows to stay within the cap.
> ⚠️ Filter names: `FilterByEarliestTimesheetDate` / `FilterByLatestTimesheetDate` (not `FilterByEarliestDate`).
> ⚠️ Approval fields (`Submitted`, `Supervisor Approved`, `Accounting Approved`) are absent on unactioned records — treat absence as false.

---

## Vendor Invoices

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListVendorInvoices` | Read | `VendorInvoices` | **Yes** | ✓ | Requires v2 session. Filters: vendor keys, date range, status |
| `GetVendorInvoices` | Read | `VendorInvoices` | **Yes** | ✓ | Requires v2 session. `RequestedVendorInvoices: [int...]` |
| `CreateVendorInvoices` | Write | — | No | — | Write method — not covered by this server |
| `DeleteVendorInvoices` | Write | — | No | — | Write method — not covered by this server |
| `DownloadVendorInvoices` | Read | *(file)* | No | — | Read permission not tested |
| `UploadVendorInvoices` | Write | — | No | — | Write method — not covered by this server |
| `UpdateVendorInvoices` | Write | — | No | — | Write method — not covered by this server |

> ⚠️ Both `ListVendorInvoices` and `GetVendorInvoices` require a **v2** session token. Calling on v1 returns "Unauthorized method ... for api version 1 but is supported with api version 2".

---

## Vendor Types

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListVendorTypes` | Read | `VendorTypes` | No | ✓ | Filters: `FilterByStatus`, `FilterByIsCreditCard`, `FilterByIsConsultant` |

---

## Vendors

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListVendors` | Read | `Vendors` | No | ✓ | Filters: `FilterByStatus`, `FilterByNameLike`, `FilterByCompany`, `FilterByVendorType`, date range |
| `GetVendors` | Read | `Vendors` | No | ✓ | `RequestedVendors: [int...]`; note API typo `BuisnessTypeW9` — match exactly when reading |
| `UpdateVendors` | Write | — | No | — | Write method — strip derived fields before sending |

---

## Wage Tables

| Method | Type | Content Key | v2 | MCP v2 | Notes |
|---|---|---|---|---|---|
| `ListWageTables` | Read | `WageTables` | No | ✓ | Wage table configurations used for payroll calculations |

---

## Summary Counts

| Category | Read Methods | Write Methods | Read in MCP v2 |
|---|---|---|---|
| Account Groups | 1 | 0 | 1 |
| Activities | 1 | 0 | 1 |
| Attachment Categories | 1 | 0 | 0 (not tested) |
| Bank Accounts | 1 | 0 | 1 |
| Chargeable Phases | 1 | 0 | 1 |
| Clients | 2 | 1 | 2 |
| Client Types | 1 | 0 | 1 |
| Companies | 1 | 0 | 1 |
| Contacts | 2 | 1 | 2 |
| Contact Types | 1 | 0 | 1 |
| Deductions | 1 | 0 | 1 |
| Departments | 1 | 0 | 1 |
| Employee Types | 1 | 0 | 1 |
| Employees | 2 | 1 | 2 |
| Expense Reports | 3 | 2 | 3 |
| Fringes | 1 | 0 | 1 |
| GL Accounts | 2 | 0 | 2 |
| Invoice Formats | 1 | 0 | 1 |
| Marketing Final Dispositions | 1 | 0 | 1 |
| Marketing Stages | 1 | 0 | 1 |
| Overhead Groups | 1 | 0 | 1 |
| Payroll Taxes | 1 | 0 | 1 |
| Pays | 1 | 0 | 1 |
| Project Templates | 2 | 0 | 2 |
| Project Totals | 1 | 0 | 1 |
| Project Types | 1 | 0 | 1 |
| Projects | 2 | 2 | 2 |
| Projects With Resources | 1 | 1 | 1 |
| Rate Tables | 1 | 0 | 1 |
| Timesheets | 3 | 4 | 3 |
| Vendor Invoices | 2 | 5 | 2 |
| Vendor Types | 1 | 0 | 1 |
| Vendors | 2 | 1 | 2 |
| Wage Tables | 1 | 0 | 1 |
| **Total** | **46** | **18** | **46** |

---

## Verification Status

All methods marked ✓ in MCP v2 have been tested against a live Ajera instance.
Methods flagged ℹ️ in their Notes need additional empirical verification.

| Method | Verified | Notes |
|---|---|---|
| `ListAccountGroups` | ✅ Confirmed | 51 records; fields: AccountGroupKey, Description, Status, Notes |
| `ListActivities` | ✅ Confirmed | 137 records; fields: ActivityKey, Description, Status, Notes, UnitBased, UnitDescription, UnitCostRate, ICRExpense |
| `ListBankAccounts` | ✅ Confirmed | 4 records; fields: BankAccountKey, Description, Status, Notes |
| `ListChargeablePhases` | ✅ Confirmed | **Requires `ProjectKey: int` (scalar).** Fields: Key, Description, Level, Enabled, WBS, RequireNotes |
| `ListCompanies` | ✅ Confirmed | 1 record |
| `ListContactTypes` | ✅ Confirmed | 2 records; fields: ContactTypeKey, Description, Status, Notes |
| `ListDeductions` | ✅ Confirmed | 3 records |
| `ListDepartments` | ✅ Confirmed | 6 records; fields: DepartmentKey, Department, Notes, Status, DPEPercent, OverheadPercent |
| `ListFringes` | ✅ Confirmed | 2 records |
| `ListInvoiceFormats` | ✅ Confirmed | 170 records |
| `ListMarketingFinalDispositions` | ✅ Confirmed | 7 records |
| `ListMarketingStages` | ✅ Confirmed | 7 records |
| `ListOverheadGroups` | ✅ Confirmed | 17 records |
| `ListPayrollTaxes` | ✅ Confirmed | 7 records |
| `ListPays` | ✅ Confirmed | 32 records; fields: PayKey, Description, Status, Notes |
| `ListProjectTemplates` | ✅ Confirmed | 4 records; fields: ProjectTemplateKey, ID, Description |
| `GetProjectTemplates` | ✅ Confirmed | **`RequestedProjects: [int...]` (int array) — NOT RequestedProjectTemplates.** Returns full template with phases, budgets, billing type, and custom fields. |
| `GetProjectTotals` | ✅ Confirmed | **`RequestedProjectTotals: int` (scalar, not array).** Returns same shape as GetProjects with totals fields. Phase totals roll up to project level after invoicing. Returns 0 records for overhead/non-billable projects. |
| `GetProjectsWithResources` | ✅ Confirmed | Use `RequestedProjects: [int...]`. Returns full project record + Resources[] array per phase. Response shape identical to GetProjects with Resources array added. |
| `ListRateTables` | ✅ Confirmed | 857 records; fields: RateTableKey, Description, Status, Notes |
| `ListTimesheetNonWorkDays` | ✅ Confirmed | **v2 session required.** 53 records; fields: Date, Description. Filter keys: FilterByEarliestDate / FilterByLatestDate |
| `ListVendorInvoices` | ✅ Confirmed | **v2 session required.** Returns invoice list; exact filter keys may vary by instance. |
| `GetVendorInvoices` | ✅ Confirmed | **v2 session required.** Arg key `RequestedVendorInvoices: [int...]` |
| `ListWageTables` | ✅ Confirmed | 1 record; fields: WageTableKey, Description, Status, Notes |
