"""
Deltek Ajera MCP Server — Read-Only (v2)

Exposes the Deltek Ajera project accounting API as MCP tools.
This server is intentionally read-only: no create, update, or delete
operations are included. Safe to use with a restricted API service account.

Compatible with any MCP-capable AI client (Claude, GitHub Copilot, etc.).

Required environment variables:
    AJERA_API_URL  — Full API endpoint URL including the ?id= parameter
                     Example: https://ajera.com/VXXXXXX/AjeraAPI.ashx?id=XXXXX
    AJERA_USERNAME — Ajera API username (service account, not an employee login)
    AJERA_PASSWORD — Ajera API password

See README.md for setup instructions.
"""

import json
import functools
from mcp.server.fastmcp import FastMCP
from ajera_client import AjeraClient, AjeraError

mcp = FastMCP(
    "Deltek Ajera",
    instructions=(
        "This server provides read-only access to Deltek Ajera, a project-based "
        "accounting and project management system. You can query projects, clients, "
        "contacts, employees, timesheets, GL accounts, vendors, expense reports, "
        "and all reference/lookup tables. "
        "Most list tools return summary data (keys + names) — use the corresponding "
        "get tool to retrieve full field detail. "
        "Keys are integer identifiers used to reference records across the API. "
        "This server is read-only: no data can be created, modified, or deleted."
    ),
)

_client: AjeraClient | None = None


def _get_client() -> AjeraClient:
    global _client
    if _client is None:
        _client = AjeraClient()
    return _client


def _fmt(data: object) -> str:
    return json.dumps(data, indent=2, default=str)


def _handle(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AjeraError as e:
            return f"Ajera API error: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
    return wrapper


# ===========================================================================
# Projects
# ===========================================================================


@mcp.tool()
@_handle
def list_projects(
    status: str = "Active",
    name_like: str = "",
    earliest_modified: str = "",
    latest_modified: str = "",
) -> str:
    """
    Search for projects and return summary information (ProjectKey, ID,
    Description, Status). Use get_project to retrieve full details including
    BillingType, TotalContractAmount, DepartmentDescription, ProjectManager,
    phases, and contacts.

    Production scale: ~1,146 active projects as of May 2026.

    Args:
        status: Filter by status — 'Active', 'Inactive', or '' for all.
        name_like: Partial name/description match (case-insensitive).
        earliest_modified: ISO date (YYYY-MM-DD) — modified on or after.
        latest_modified: ISO date (YYYY-MM-DD) — modified on or before.
    """
    c = _get_client()
    results = c.list_projects(
        status=[status] if status else None,
        name_like=name_like or None,
        earliest_modified=earliest_modified or None,
        latest_modified=latest_modified or None,
    )
    return _fmt(results) if results else "No projects found matching the given filters."


@mcp.tool()
@_handle
def get_project(project_keys: list[int]) -> str:
    """
    Retrieve full details for one or more projects by their ProjectKey values.

    Confirmed top-level fields (verified against production instance, ~1,146 active projects):
        ProjectKey          — integer primary key
        ID                  — human-readable job number (e.g. "4210.000")
        Description         — project name/title
        Status              — e.g. "Active", "Inactive"
        BillingType         — e.g. "TimeAndMaterials", "FixedFee", "CostPlus"
        TotalContractAmount — total contract value (float)
        DepartmentDescription — department name string
        ProjectManager      — nested dict: {EmployeeKey, FirstName, MiddleName, LastName}
                              NOT a plain string — extract name as FirstName + LastName
        InvoiceGroups       — list of invoice group objects
        Contacts            — list of associated contact objects

    Also returns phases, budgets, dates, billing configuration, and custom fields.

    Batching: tested safely at 25 keys per call across all 1,146 active projects
    with zero errors. Larger batches may work but are untested.

    Args:
        project_keys: List of integer ProjectKey values (e.g. [1001, 1002]).
    """
    c = _get_client()
    results = c.get_projects(project_keys)
    return _fmt(results) if results else "No projects found for the provided keys."


@mcp.tool()
@_handle
def list_project_types(status: str = "Active") -> str:
    """
    Return all available project type classifications (e.g. 'Federal',
    'Commercial', 'Internal').

    Args:
        status: 'Active', 'Inactive', or '' for all.
    """
    c = _get_client()
    results = c.list_project_types(status=[status] if status else None)
    return _fmt(results) if results else "No project types found."


@mcp.tool()
@_handle
def list_project_templates(status: str = "") -> str:
    """
    Return a summary list of all project templates available in Ajera.
    Use get_project_template to retrieve the full template including phases.

    Args:
        status: Filter by status — 'Active', 'Inactive', or '' for all.
            Note: the API may not support a status filter on this method;
            pass '' to retrieve all templates.
    """
    c = _get_client()
    results = c.list_project_templates()
    return _fmt(results) if results else "No project templates found."


@mcp.tool()
@_handle
def get_project_template(template_keys: list[int]) -> str:
    """
    Retrieve full details for one or more project templates by their key values.
    Returns the template structure including all phases and settings.

    Args:
        template_keys: List of integer project template key values.
    """
    c = _get_client()
    results = c.get_project_templates(template_keys)
    return _fmt(results) if results else "No project templates found for the provided keys."


@mcp.tool()
@_handle
def get_project_totals(project_key: int) -> str:
    """
    Retrieve financial totals for a single project — fees, WIP (unbilled
    work-in-progress), billed amounts, costs, and expenses. Phase-level totals
    are included and roll up to the project level after invoicing.

    Returns the same shape as get_project but with totals fields populated.
    Call once per project; the API accepts only one key per request.

    Args:
        project_key: The ProjectKey of the project to retrieve totals for.
    """
    c = _get_client()
    results = c.get_project_totals(project_key=project_key)
    return _fmt(results) if results else f"No totals found for ProjectKey {project_key}."


@mcp.tool()
@_handle
def get_projects_with_resources(
    project_keys: list[int] | None = None,
    earliest_date: str = "",
    latest_date: str = "",
) -> str:
    """
    Retrieve projects with their resource/staffing plan data. Returns project
    records enriched with resource assignment information.

    Note: exact argument keys and response shape for this method are unverified
    against instance your Ajera instance. Inspect raw output and update
    API_CAPABILITY_INVENTORY.md with confirmed field names.

    Args:
        project_keys: Specific ProjectKey values to retrieve. Omit for all.
        earliest_date: ISO date (YYYY-MM-DD) — start of resource period.
        latest_date: ISO date (YYYY-MM-DD) — end of resource period.
    """
    c = _get_client()
    results = c.get_projects_with_resources(
        project_keys=project_keys,
        earliest_date=earliest_date or None,
        latest_date=latest_date or None,
    )
    return _fmt(results) if results else "No projects with resources found for the provided filters."


@mcp.tool()
@_handle
def list_chargeable_phases(project_key: int) -> str:
    """
    Return the chargeable project/phase hierarchy for a project — the entries
    that appear in the timesheet 'Project' dropdown for that project.

    Returns a flat list with Level field: Level 0 = top-level project entry,
    Level 1+ = phases. Each entry has Key, Description, Level, Enabled, WBS,
    and RequireNotes fields.

    Note: ProjectKey is required — the API rejects calls without it. To get
    chargeable phases across multiple projects, call this tool once per project.

    Args:
        project_key: The ProjectKey of the project to query.
    """
    c = _get_client()
    results = c.list_chargeable_phases(project_key=project_key)
    return _fmt(results) if results else f"No chargeable phases found for ProjectKey {project_key}."


# ===========================================================================
# Clients
# ===========================================================================


@mcp.tool()
@_handle
def list_clients(
    status: str = "Active",
    name_like: str = "",
    earliest_modified: str = "",
    latest_modified: str = "",
) -> str:
    """
    Search for clients and return summary information (ClientKey, Description).
    Use get_client to retrieve full details including address and contacts.

    Args:
        status: Filter by status — 'Active', 'Inactive', or '' for all.
        name_like: Partial name match.
        earliest_modified: ISO date (YYYY-MM-DD).
        latest_modified: ISO date (YYYY-MM-DD).
    """
    c = _get_client()
    results = c.list_clients(
        status=[status] if status else None,
        name_like=name_like or None,
        earliest_modified=earliest_modified or None,
        latest_modified=latest_modified or None,
    )
    return _fmt(results) if results else "No clients found matching the given filters."


@mcp.tool()
@_handle
def get_client(client_keys: list[int]) -> str:
    """
    Retrieve full details for one or more clients by their ClientKey values.
    Returns contact information, addresses, financial settings, and custom fields.

    Args:
        client_keys: List of integer ClientKey values.
    """
    c = _get_client()
    results = c.get_clients(client_keys)
    return _fmt(results) if results else "No clients found for the provided keys."


@mcp.tool()
@_handle
def list_client_types(status: str = "Active") -> str:
    """
    Return all available client type classifications.

    Args:
        status: 'Active', 'Inactive', or '' for all.
    """
    c = _get_client()
    results = c.list_client_types(status=[status] if status else None)
    return _fmt(results) if results else "No client types found."


# ===========================================================================
# Contacts
# ===========================================================================


@mcp.tool()
@_handle
def list_contacts(
    status: str = "Active",
    name_like: str = "",
    client_keys: list[int] | None = None,
) -> str:
    """
    Search for contacts (people associated with clients) in Ajera.

    Args:
        status: Filter by status — 'Active', 'Inactive', or '' for all.
        name_like: Partial name match.
        client_keys: Only return contacts linked to these ClientKey values.
    """
    c = _get_client()
    results = c.list_contacts(
        status=[status] if status else None,
        name_like=name_like or None,
        client_keys=client_keys,
    )
    return _fmt(results) if results else "No contacts found matching the given filters."


@mcp.tool()
@_handle
def get_contact(contact_keys: list[int]) -> str:
    """
    Retrieve full details for one or more contacts by their ContactKey values.

    Args:
        contact_keys: List of integer ContactKey values.
    """
    c = _get_client()
    results = c.get_contacts(contact_keys)
    return _fmt(results) if results else "No contacts found for the provided keys."


@mcp.tool()
@_handle
def list_contact_types() -> str:
    """
    Return all configured contact type classifications and their key values.
    Useful for understanding what types exist before filtering contacts.
    """
    c = _get_client()
    results = c.list_contact_types()
    return _fmt(results) if results else "No contact types found."


# ===========================================================================
# Employees
# ===========================================================================


@mcp.tool()
@_handle
def list_employees(
    status: str = "Active",
    name_like: str = "",
    department_keys: list[int] | None = None,
    supervisor_keys: list[int] | None = None,
) -> str:
    """
    Search for employees and return summary information. Use get_employee to
    retrieve full details (including email address).

    Note: list_employees does NOT return the Email field — call get_employee
    for email and full contact details.

    Args:
        status: Filter by status — 'Active', 'Inactive', or '' for all.
        name_like: Partial name match.
        department_keys: Only return employees in these departments.
        supervisor_keys: Only return employees supervised by these EmployeeKeys.
    """
    c = _get_client()
    results = c.list_employees(
        status=[status] if status else None,
        name_like=name_like or None,
        department_keys=department_keys,
        supervisor_keys=supervisor_keys,
    )
    return _fmt(results) if results else "No employees found matching the given filters."


@mcp.tool()
@_handle
def get_employee(employee_keys: list[int]) -> str:
    """
    Retrieve full details for one or more employees by their EmployeeKey values.
    Returns pay rates, email address, contact info, addresses, and custom fields.

    Automatically batches requests in groups of 50 to stay within the API's
    hard limit (larger batches return an error with no data).

    Args:
        employee_keys: List of integer EmployeeKey values.
    """
    c = _get_client()
    all_results: list[dict] = []
    for i in range(0, len(employee_keys), 50):
        batch = employee_keys[i:i + 50]
        all_results.extend(c.get_employees(batch))
    return _fmt(all_results) if all_results else "No employees found for the provided keys."


@mcp.tool()
@_handle
def list_employee_types(status: str = "Active") -> str:
    """
    Return all available employee type classifications.

    Args:
        status: 'Active', 'Inactive', or '' for all.
    """
    c = _get_client()
    results = c.list_employee_types(status=[status] if status else None)
    return _fmt(results) if results else "No employee types found."


# ===========================================================================
# Timesheets  (require API v2 session)
# ===========================================================================


@mcp.tool()
@_handle
def list_timesheets(
    employee_keys: list[int] | None = None,
    submitted: str = "",
    rejected: str = "",
    earliest_date: str = "",
    latest_date: str = "",
) -> str:
    """
    Search for timesheets and return summary information. Use get_timesheet to
    retrieve the full timesheet with daily hour entries.

    Hard limit: 500 records per call — confirmed intentional (the API shares
    code with the Manage Timesheets UI, which has the same cap). Deltek has
    a request in to add a truncation warning to the API response. For
    organizations with many employees, use date windows of 7 days or fewer.

    Args:
        employee_keys: Only return timesheets for these EmployeeKey values.
        submitted: Filter by submission status — 'true', 'false', or '' for all.
        rejected: Filter by rejection status — 'true', 'false', or '' for all.
        earliest_date: ISO date (YYYY-MM-DD) — start of timesheet period.
        latest_date: ISO date (YYYY-MM-DD) — end of timesheet period.
    """
    c = _get_client()
    results = c.list_timesheets(
        employee_keys=employee_keys,
        submitted=(submitted.lower() == "true") if submitted else None,
        rejected=(rejected.lower() == "true") if rejected else None,
        earliest_date=earliest_date or None,
        latest_date=latest_date or None,
    )
    return _fmt(results) if results else "No timesheets found matching the given filters."


@mcp.tool()
@_handle
def get_timesheet(timesheet_keys: list[int]) -> str:
    """
    Retrieve full timesheet details including all project and overhead line
    items with daily hours (D1–D7) and notes (N1–N7).

    Args:
        timesheet_keys: List of integer TimesheetKey values.
    """
    c = _get_client()
    results = c.get_timesheets(timesheet_keys)
    return _fmt(results) if results else "No timesheets found for the provided keys."


@mcp.tool()
@_handle
def list_timesheet_non_work_days(
    earliest_date: str = "",
    latest_date: str = "",
) -> str:
    """
    Return holidays and non-work days configured in Ajera for a given date
    range. Useful for determining which days should have zero timesheet hours.

    Note: this method requires a v2 session. Argument keys are unverified —
    if date filtering does not work, try omitting the filters to return all
    non-work days and update API_CAPABILITY_INVENTORY.md.

    Args:
        earliest_date: ISO date (YYYY-MM-DD) — start of the date range.
        latest_date: ISO date (YYYY-MM-DD) — end of the date range.
    """
    c = _get_client()
    results = c.list_timesheet_non_work_days(
        earliest_date=earliest_date or None,
        latest_date=latest_date or None,
    )
    return _fmt(results) if results else "No non-work days found for the given date range."


# ===========================================================================
# GL Accounts
# ===========================================================================


@mcp.tool()
@_handle
def list_gl_accounts(
    status: str = "Active",
    account_type: str = "",
) -> str:
    """
    Return a summary list of GL accounts (GLAccountKey, ID, Description,
    AccountType, AccountGroup, Status). Use get_gl_account_balances to
    retrieve amounts and balances.

    Args:
        status: Filter by status — 'Active', 'Inactive', or '' for all.
        account_type: Filter by type — e.g. 'Income', 'Expense',
            'BillableCost', or '' for all types.
    """
    c = _get_client()
    results = c.list_gl_accounts(
        status=[status] if status else None,
        account_type=[account_type] if account_type else None,
    )
    return _fmt(results) if results else "No GL accounts found matching the given filters."


@mcp.tool()
@_handle
def get_gl_account_balances(
    gl_account_keys: list[int] | None = None,
    status: str = "Active",
    account_type: str = "",
    as_of_date: str = "",
    exclude_close_year_entries: bool = False,
) -> str:
    """
    Retrieve GL account details including current balances and budget amounts.
    Returns Amount, GLBalance, GLCashBasisBalance, and budget fields.

    Note: GL transaction-level detail (individual journal entries) is not
    exposed by the Ajera API — only balance snapshots are available.

    Args:
        gl_account_keys: Specific GLAccountKey values. Omit to return all.
        status: Filter by status — 'Active', 'Inactive', or '' for all.
        account_type: Filter by type — 'Income', 'Expense', 'BillableCost', etc.
        as_of_date: Balance snapshot date in MM/DD/YYYY format (e.g. '03/31/2025').
            Omit for current balances.
        exclude_close_year_entries: If True, year-end closing entries are excluded.
    """
    c = _get_client()
    results = c.get_gl_accounts(
        gl_account_keys=gl_account_keys,
        status=[status] if status else None,
        account_type=[account_type] if account_type else None,
        as_of_date=as_of_date or None,
        exclude_close_year_entries=exclude_close_year_entries,
    )
    return _fmt(results) if results else "No GL accounts found for the provided filters."


# ===========================================================================
# Expense Reports  (API user sees own reports only)
# ===========================================================================


@mcp.tool()
@_handle
def list_expense_reports(
    is_processed: str = "",
    name_like: str = "",
    earliest_beginning_date: str = "",
    latest_beginning_date: str = "",
    earliest_ending_date: str = "",
    latest_ending_date: str = "",
    earliest_modified: str = "",
    latest_modified: str = "",
) -> str:
    """
    Search for expense reports and return summary information.
    Use get_expense_report to retrieve line items and attachment metadata.

    Important: the API user can only access its own expense reports, not
    all users'. Use Ajera's ODBC connection for cross-user expense data.

    Args:
        is_processed: Filter by processing status — 'true', 'false', or '' for all.
        name_like: Partial description match.
        earliest_beginning_date: ISO date (YYYY-MM-DD) — report period start on or after.
        latest_beginning_date: ISO date (YYYY-MM-DD) — report period start on or before.
        earliest_ending_date: ISO date (YYYY-MM-DD) — report period end on or after.
        latest_ending_date: ISO date (YYYY-MM-DD) — report period end on or before.
        earliest_modified: ISO date (YYYY-MM-DD) — modified on or after.
        latest_modified: ISO date (YYYY-MM-DD) — modified on or before.
    """
    c = _get_client()
    results = c.list_expense_reports(
        is_processed=(is_processed.lower() == "true") if is_processed else None,
        name_like=name_like or None,
        earliest_beginning_date=earliest_beginning_date or None,
        latest_beginning_date=latest_beginning_date or None,
        earliest_ending_date=earliest_ending_date or None,
        latest_ending_date=latest_ending_date or None,
        earliest_modified=earliest_modified or None,
        latest_modified=latest_modified or None,
    )
    return _fmt(results) if results else "No expense reports found matching the given filters."


@mcp.tool()
@_handle
def get_expense_report(expense_report_keys: list[int]) -> str:
    """
    Retrieve full expense report details including all expense line items,
    approval statuses, amounts, and attachment metadata.

    Args:
        expense_report_keys: List of integer ExpenseReportKey values.
    """
    c = _get_client()
    results = c.get_expense_reports(expense_report_keys)
    return _fmt(results) if results else "No expense reports found for the provided keys."


@mcp.tool()
@_handle
def download_expense_attachment(file_key: int) -> str:
    """
    Download an expense attachment by its FileKey. Returns the file data as a
    base64-encoded string along with the filename and MIME type.

    The raw base64 blob is summarized (character count shown) to keep output
    readable — extract the full FileData from a direct API call if needed.

    Args:
        file_key: The FileKey of the attachment (found in get_expense_report output).
    """
    c = _get_client()
    result = c.download_expense_attachment(file_key)
    if not result:
        return "No attachment found for the provided FileKey."
    summary = {k: v for k, v in result.items() if k != "FileData"}
    summary["FileData"] = f"<base64 data, {len(result.get('FileData', ''))} chars>"
    return _fmt(summary)


# ===========================================================================
# Vendors
# ===========================================================================


@mcp.tool()
@_handle
def list_vendors(
    status: str = "Active",
    name_like: str = "",
    vendor_type_keys: list[int] | None = None,
    earliest_modified: str = "",
    latest_modified: str = "",
) -> str:
    """
    Search for vendors and return summary information (VendorKey, Name).
    Use get_vendor to retrieve full details.

    Args:
        status: Filter by status — 'Active', 'Inactive', or '' for all.
        name_like: Partial name match.
        vendor_type_keys: Filter by VendorTypeKey (see list_vendor_types).
        earliest_modified: ISO date (YYYY-MM-DD).
        latest_modified: ISO date (YYYY-MM-DD).
    """
    c = _get_client()
    results = c.list_vendors(
        status=[status] if status else None,
        name_like=name_like or None,
        vendor_type_keys=vendor_type_keys,
        earliest_modified=earliest_modified or None,
        latest_modified=latest_modified or None,
    )
    return _fmt(results) if results else "No vendors found matching the given filters."


@mcp.tool()
@_handle
def get_vendor(vendor_keys: list[int]) -> str:
    """
    Retrieve full details for one or more vendors by their VendorKey values.
    Returns address, phone, tax/1099 info, payment configuration, and contacts.

    Note: the API spells one field as 'BuisnessTypeW9' (typo preserved from
    Ajera source) — match it exactly when referencing the field.

    Args:
        vendor_keys: List of integer VendorKey values.
    """
    c = _get_client()
    results = c.get_vendors(vendor_keys)
    return _fmt(results) if results else "No vendors found for the provided keys."


@mcp.tool()
@_handle
def list_vendor_types(
    status: str = "Active",
    is_credit_card: str = "",
    is_consultant: str = "",
) -> str:
    """
    List vendor type classifications. Useful for understanding vendor categories
    before filtering list_vendors.

    Args:
        status: 'Active', 'Inactive', or '' for all.
        is_credit_card: 'true' to return only credit card types, 'false' to exclude.
        is_consultant: 'true' to return only consultant types, 'false' to exclude.
    """
    c = _get_client()
    results = c.list_vendor_types(
        status=[status] if status else None,
        is_credit_card=(is_credit_card.lower() == "true") if is_credit_card else None,
        is_consultant=(is_consultant.lower() == "true") if is_consultant else None,
    )
    return _fmt(results) if results else "No vendor types found."


@mcp.tool()
@_handle
def list_vendor_invoices(
    vendor_keys: list[int] | None = None,
    status: str = "",
    earliest_date: str = "",
    latest_date: str = "",
    earliest_modified: str = "",
    latest_modified: str = "",
) -> str:
    """
    Search for vendor invoices and return summary information.
    Use get_vendor_invoice to retrieve full line-item detail.

    Note: filter argument keys for this method are unverified against instance
    your Ajera instance. If results are unexpected, inspect raw output and update
    API_CAPABILITY_INVENTORY.md with confirmed field names.

    Args:
        vendor_keys: Only return invoices for these VendorKey values.
        status: Filter by status (e.g. 'Open', 'Paid') — '' for all.
        earliest_date: ISO date (YYYY-MM-DD) — invoice date on or after.
        latest_date: ISO date (YYYY-MM-DD) — invoice date on or before.
        earliest_modified: ISO date (YYYY-MM-DD).
        latest_modified: ISO date (YYYY-MM-DD).
    """
    c = _get_client()
    results = c.list_vendor_invoices(
        vendor_keys=vendor_keys,
        status=[status] if status else None,
        earliest_date=earliest_date or None,
        latest_date=latest_date or None,
        earliest_modified=earliest_modified or None,
        latest_modified=latest_modified or None,
    )
    return _fmt(results) if results else "No vendor invoices found matching the given filters."


@mcp.tool()
@_handle
def get_vendor_invoice(vendor_invoice_keys: list[int]) -> str:
    """
    Retrieve full details for one or more vendor invoices by their key values.
    Returns line items, amounts, approval status, and payment information.

    Note: the argument key ('RequestedVendorInvoices') is unverified against
    instance your Ajera instance. Update API_CAPABILITY_INVENTORY.md if a different key
    is required.

    Args:
        vendor_invoice_keys: List of integer VendorInvoiceKey values.
    """
    c = _get_client()
    results = c.get_vendor_invoices(vendor_invoice_keys)
    return _fmt(results) if results else "No vendor invoices found for the provided keys."


# ===========================================================================
# Reference / lookup data
# ===========================================================================


@mcp.tool()
@_handle
def list_account_groups() -> str:
    """
    Return all GL account groups configured in Ajera. Account groups are used
    to categorize GL accounts for reporting and filtering.
    """
    c = _get_client()
    results = c.list_account_groups()
    return _fmt(results) if results else "No account groups found."


@mcp.tool()
@_handle
def list_activities(status: str = "Active") -> str:
    """
    Return all activity codes configured in Ajera. Activities are used on
    timesheet lines and expense report entries to classify work type.

    Args:
        status: 'Active', 'Inactive', or '' for all.
    """
    c = _get_client()
    results = c.list_activities(status=[status] if status else None)
    return _fmt(results) if results else "No activities found."


@mcp.tool()
@_handle
def list_bank_accounts(status: str = "Active") -> str:
    """
    Return all bank accounts configured in Ajera. Used for expense
    reimbursements and accounts payable.

    Args:
        status: 'Active', 'Inactive', or '' for all.
    """
    c = _get_client()
    results = c.list_bank_accounts(status=[status] if status else None)
    return _fmt(results) if results else "No bank accounts found."


@mcp.tool()
@_handle
def list_companies() -> str:
    """
    Return all companies in this Ajera instance. Relevant for multi-company
    configurations where projects, employees, and financials are segregated
    by entity.
    """
    c = _get_client()
    results = c.list_companies()
    return _fmt(results) if results else "No companies found."


@mcp.tool()
@_handle
def list_deductions() -> str:
    """
    Return all payroll deduction types configured in Ajera (e.g. health
    insurance, 401k, garnishments).
    """
    c = _get_client()
    results = c.list_deductions()
    return _fmt(results) if results else "No deductions found."


@mcp.tool()
@_handle
def list_departments(status: str = "Active") -> str:
    """
    Return all departments configured in Ajera. Department keys are used
    to filter employees and allocate overhead costs.

    Args:
        status: 'Active', 'Inactive', or '' for all.
    """
    c = _get_client()
    results = c.list_departments(status=[status] if status else None)
    return _fmt(results) if results else "No departments found."


@mcp.tool()
@_handle
def list_fringes() -> str:
    """
    Return all fringe benefit configurations in Ajera. Fringes are applied
    to labor costs for burden calculations (e.g. FICA, vacation accrual).
    """
    c = _get_client()
    results = c.list_fringes()
    return _fmt(results) if results else "No fringes found."


@mcp.tool()
@_handle
def list_invoice_formats() -> str:
    """
    Return all invoice format templates configured in Ajera. Invoice formats
    control the layout and content of client-facing invoices.
    """
    c = _get_client()
    results = c.list_invoice_formats()
    return _fmt(results) if results else "No invoice formats found."


@mcp.tool()
@_handle
def list_marketing_final_dispositions() -> str:
    """
    Return all marketing final disposition types in Ajera. Used to classify
    the final outcome of a pursuit or opportunity (e.g. Won, Lost, No Bid).
    """
    c = _get_client()
    results = c.list_marketing_final_dispositions()
    return _fmt(results) if results else "No marketing final dispositions found."


@mcp.tool()
@_handle
def list_marketing_stages() -> str:
    """
    Return all marketing pipeline stages configured in Ajera. Stages represent
    the progression of a pursuit or business development opportunity.
    """
    c = _get_client()
    results = c.list_marketing_stages()
    return _fmt(results) if results else "No marketing stages found."


@mcp.tool()
@_handle
def list_overhead_groups() -> str:
    """
    Return all overhead groups configured in Ajera. Overhead groups are used
    to pool and allocate indirect costs across projects.
    """
    c = _get_client()
    results = c.list_overhead_groups()
    return _fmt(results) if results else "No overhead groups found."


@mcp.tool()
@_handle
def list_payroll_taxes() -> str:
    """
    Return all payroll tax types configured in Ajera (e.g. federal income tax,
    FICA, state taxes). Useful for understanding payroll burden setup.
    """
    c = _get_client()
    results = c.list_payroll_taxes()
    return _fmt(results) if results else "No payroll taxes found."


@mcp.tool()
@_handle
def list_pays() -> str:
    """
    Return all pay type codes configured in Ajera (e.g. Regular, Overtime,
    G&A Pay, Technical Overhead Pay). These codes appear on processed
    payroll transactions and are accessible via ODBC only — this method
    returns the code definitions themselves.
    """
    c = _get_client()
    results = c.list_pays()
    return _fmt(results) if results else "No pay types found."


@mcp.tool()
@_handle
def list_rate_tables(status: str = "Active") -> str:
    """
    Return all billing rate tables configured in Ajera. Rate tables define
    the billing rates applied to projects by employee type, role, or
    individual employee.

    Args:
        status: 'Active', 'Inactive', or '' for all.
    """
    c = _get_client()
    results = c.list_rate_tables(status=[status] if status else None)
    return _fmt(results) if results else "No rate tables found."


@mcp.tool()
@_handle
def list_wage_tables(status: str = "Active") -> str:
    """
    Return all wage tables configured in Ajera. Wage tables define the
    internal cost rates (pay rates) used for labor cost calculations.

    Args:
        status: 'Active', 'Inactive', or '' for all.
    """
    c = _get_client()
    results = c.list_wage_tables(status=[status] if status else None)
    return _fmt(results) if results else "No wage tables found."


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    mcp.run()
