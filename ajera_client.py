"""
Deltek Ajera API HTTP client — read-only.

Version routing:
    v2 only : All timesheet methods (ListTimesheets, GetTimesheets,
              ListTimesheetNonWorkDays)
    v1 only : Everything else, including GetEmployees (see note below)
    both    : ListProjects, GetProjects, ListGLAccounts

⚠️  GetEmployees quirk: despite the server defaulting to v2, GetEmployees
    and ListEmployees require a v1 session. The routing table below handles
    this automatically — callers just call _call("GetEmployees", ...).

Sessions for each version are created lazily on first use and reused for the
lifetime of the AjeraClient instance.
"""

import os
import httpx
from typing import Any


class AjeraError(Exception):
    """Raised when the Ajera API returns a negative ResponseCode or negative ErrorID."""

    def __init__(self, message: str, errors: list[str] | None = None):
        self.errors = errors or []
        detail = f" Errors: {'; '.join(self.errors)}" if self.errors else ""
        super().__init__(f"{message}{detail}")


class AjeraClient:
    """
    Read-only client for the Deltek Ajera REST API.

    Configuration via environment variables:
        AJERA_API_URL  — Full API URL including the ?id= parameter
                         (from Ajera: Setup → Integrations → API Settings)
        AJERA_USERNAME — API service account username (not an employee login)
        AJERA_PASSWORD — API service account password
    """

    # Methods that require an API v2 session token.
    # Everything not in this set is routed to v1.
    _V2_ONLY_METHODS: frozenset[str] = frozenset({
        "ListTimesheets",
        "GetTimesheets",
        "ListTimesheetNonWorkDays",
        "ListVendorInvoices",
        "GetVendorInvoices",
    })

    # Methods that must use v1 even if a v2 session exists.
    # GetEmployees/ListEmployees are v1-only despite the v2 default.
    _V1_ONLY_METHODS: frozenset[str] = frozenset({
        "ListEmployees",
        "GetEmployees",
    })

    def __init__(
        self,
        api_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.api_url = api_url or os.environ.get("AJERA_API_URL", "")
        self.username = username or os.environ.get("AJERA_USERNAME", "")
        self.password = password or os.environ.get("AJERA_PASSWORD", "")
        self._sessions: dict[int, str] = {}  # version → session token

        if not self.api_url:
            raise ValueError(
                "AJERA_API_URL must be set "
                "(e.g. https://ajera.com/VXXXXXX/AjeraAPI.ashx?id=XXXXX)"
            )

    # ------------------------------------------------------------------
    # Core HTTP / session machinery
    # ------------------------------------------------------------------

    def _raw_call(
        self,
        method: str,
        arguments: dict[str, Any] | None = None,
        top_level: dict[str, Any] | None = None,
        session_token: str | None = None,
    ) -> Any:
        """Low-level HTTP POST with no session management."""
        payload: dict[str, Any] = {"Method": method}
        if session_token:
            payload["SessionToken"] = session_token
        if top_level:
            payload.update(top_level)
        else:
            payload["MethodArguments"] = arguments or {}

        with httpx.Client(timeout=60.0) as http:
            response = http.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()

        rc = data.get("ResponseCode", 0)
        all_errors = data.get("Errors", [])
        neg_errors = [e for e in all_errors if e.get("ErrorID", 0) < 0]
        if rc < 0:
            msgs = [e.get("ErrorMessage", str(e)) for e in all_errors] if all_errors else []
            raise AjeraError(data.get("Message", "API error"), msgs)
        if neg_errors:
            raise AjeraError(
                neg_errors[0].get("ErrorMessage", data.get("Message", "API error")),
                [e.get("ErrorMessage", str(e)) for e in neg_errors],
            )
        return data.get("Content")

    def _ensure_session(self, version: int) -> str:
        if version not in self._sessions:
            content = self._raw_call(
                "CreateAPISession",
                top_level={
                    "APIVersion": version,
                    "Username": self.username,
                    "Password": self.password,
                },
            )
            self._sessions[version] = content.get("SessionToken", "")
        return self._sessions[version]

    def _call(self, method: str, arguments: dict[str, Any] | None = None) -> Any:
        """Make an API call with automatic v1/v2 routing."""
        if method in self._V1_ONLY_METHODS:
            version = 1
        elif method in self._V2_ONLY_METHODS:
            version = 2
        else:
            version = 1
        token = self._ensure_session(version)
        return self._raw_call(method, arguments, session_token=token)

    def close_sessions(self) -> None:
        for token in list(self._sessions.values()):
            try:
                self._raw_call("CloseAPISession", session_token=token)
            except AjeraError:
                pass
        self._sessions.clear()

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def list_projects(
        self,
        status: list[str] | None = None,
        name_like: str | None = None,
        company_keys: list[int] | None = None,
        project_type_keys: list[int] | None = None,
        earliest_modified: str | None = None,
        latest_modified: str | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if status:
            args["FilterByStatus"] = status
        if name_like:
            args["FilterByNameLike"] = name_like
        if company_keys:
            args["FilterByCompany"] = company_keys
        if project_type_keys:
            args["FilterByProjectType"] = project_type_keys
        if earliest_modified:
            args["FilterByEarliestModifiedDate"] = earliest_modified
        if latest_modified:
            args["FilterByLatestModifiedDate"] = latest_modified
        content = self._call("ListProjects", args or None)
        return content.get("Projects", []) if content else []

    def get_projects(self, project_keys: list[int]) -> list[dict]:
        content = self._call("GetProjects", {"RequestedProjects": project_keys})
        return content.get("Projects", []) if content else []

    def list_project_types(self, status: list[str] | None = None) -> list[dict]:
        args = {"FilterByStatus": status} if status else None
        content = self._call("ListProjectTypes", args)
        return content.get("ProjectTypes", []) if content else []

    def list_project_templates(self) -> list[dict]:
        content = self._call("ListProjectTemplates")
        return content.get("ProjectTemplates", []) if content else []

    def get_project_templates(self, template_keys: list[int]) -> list[dict]:
        """
        Argument key is RequestedProjects (int array) — not RequestedProjectTemplates.
        Returns full template detail including phases, budgets, and custom fields.
        """
        content = self._call("GetProjectTemplates", {"RequestedProjects": template_keys})
        return content.get("ProjectTemplates", []) if content else []

    def get_project_totals(self, project_key: int) -> list[dict]:
        """
        RequestedProjectTotals takes a single scalar integer (not an array).
        Returns phase-level totals that roll up to the project level.
        Content key is 'Projects' (same shape as GetProjects + totals fields).
        """
        content = self._call("GetProjectTotals", {"RequestedProjectTotals": project_key})
        return content.get("Projects", []) if content else []

    def get_projects_with_resources(
        self,
        project_keys: list[int] | None = None,
        earliest_date: str | None = None,
        latest_date: str | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if project_keys:
            args["RequestedProjects"] = project_keys
        if earliest_date:
            args["FilterByEarliestDate"] = earliest_date
        if latest_date:
            args["FilterByLatestDate"] = latest_date
        content = self._call("GetProjectsWithResources", args or None)
        return content.get("Projects", []) if content else []

    def list_chargeable_phases(self, project_key: int) -> list[dict]:
        """
        Returns the chargeable project/phase hierarchy for a single project.
        ProjectKey (scalar int) is required — the API rejects calls without it.
        Level 0 = top-level project, Level 1+ = phases.
        """
        content = self._call("ListChargeablePhases", {"ProjectKey": project_key})
        return content.get("ChargeablePhases", []) if content else []

    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------

    def list_clients(
        self,
        status: list[str] | None = None,
        name_like: str | None = None,
        company_keys: list[int] | None = None,
        client_type_keys: list[int] | None = None,
        earliest_modified: str | None = None,
        latest_modified: str | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if status:
            args["FilterByStatus"] = status
        if name_like:
            args["FilterByNameLike"] = name_like
        if company_keys:
            args["FilterByCompany"] = company_keys
        if client_type_keys:
            args["FilterByClientType"] = client_type_keys
        if earliest_modified:
            args["FilterByEarliestModifiedDate"] = earliest_modified
        if latest_modified:
            args["FilterByLatestModifiedDate"] = latest_modified
        content = self._call("ListClients", args or None)
        return content.get("Clients", []) if content else []

    def get_clients(self, client_keys: list[int] | None = None) -> list[dict]:
        args = {"RequestedClients": client_keys} if client_keys else None
        content = self._call("GetClients", args)
        return content.get("Clients", []) if content else []

    def list_client_types(self, status: list[str] | None = None) -> list[dict]:
        args = {"FilterByStatus": status} if status else None
        content = self._call("ListClientTypes", args)
        return content.get("ClientTypes", []) if content else []

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    def list_contacts(
        self,
        status: list[str] | None = None,
        name_like: str | None = None,
        client_keys: list[int] | None = None,
        earliest_modified: str | None = None,
        latest_modified: str | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if status:
            args["FilterByStatus"] = status
        if name_like:
            args["FilterByNameLike"] = name_like
        if client_keys:
            args["FilterByClient"] = client_keys
        if earliest_modified:
            args["FilterByEarliestModifiedDate"] = earliest_modified
        if latest_modified:
            args["FilterByLatestModifiedDate"] = latest_modified
        content = self._call("ListContacts", args or None)
        return content.get("Contacts", []) if content else []

    def get_contacts(self, contact_keys: list[int] | None = None) -> list[dict]:
        args = {"RequestedContacts": contact_keys} if contact_keys else None
        content = self._call("GetContacts", args)
        return content.get("Contacts", []) if content else []

    def list_contact_types(self) -> list[dict]:
        content = self._call("ListContactTypes")
        return content.get("ContactTypes", []) if content else []

    # ------------------------------------------------------------------
    # Employees  (v1 only — ListEmployees and GetEmployees both require v1)
    # ------------------------------------------------------------------

    def list_employees(
        self,
        status: list[str] | None = None,
        name_like: str | None = None,
        department_keys: list[int] | None = None,
        company_keys: list[int] | None = None,
        supervisor_keys: list[int] | None = None,
        employee_type_keys: list[int] | None = None,
        earliest_modified: str | None = None,
        latest_modified: str | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if status:
            args["FilterByStatus"] = status
        if name_like:
            args["FilterByNameLike"] = name_like
        if department_keys:
            args["FilterByDepartment"] = department_keys
        if company_keys:
            args["FilterByCompany"] = company_keys
        if supervisor_keys:
            args["FilterBySupervisor"] = supervisor_keys
        if employee_type_keys:
            args["FilterByEmployeeType"] = employee_type_keys
        if earliest_modified:
            args["FilterByEarliestModifiedDate"] = earliest_modified
        if latest_modified:
            args["FilterByLatestModifiedDate"] = latest_modified
        content = self._call("ListEmployees", args or None)
        return content.get("Employees", []) if content else []

    def get_employees(self, employee_keys: list[int]) -> list[dict]:
        """Batch ≤ 50 keys per call — larger batches return RC=-100."""
        content = self._call("GetEmployees", {"RequestedEmployees": employee_keys})
        return content.get("Employees", []) if content else []

    def list_employee_types(self, status: list[str] | None = None) -> list[dict]:
        args = {"FilterByStatus": status} if status else None
        content = self._call("ListEmployeeTypes", args)
        return content.get("EmployeeTypes", []) if content else []

    # ------------------------------------------------------------------
    # Timesheets  (all require v2 session)
    # ------------------------------------------------------------------

    def list_timesheets(
        self,
        employee_keys: list[int] | None = None,
        company_keys: list[int] | None = None,
        submitted: bool | None = None,
        rejected: bool | None = None,
        earliest_date: str | None = None,
        latest_date: str | None = None,
    ) -> list[dict]:
        # Hard cap of 500 records per call — confirmed intentional by Deltek
        # (shared server-side code with the Manage Timesheets UI).
        # Use narrow date windows (≤7 days) to stay within the limit.
        args: dict[str, Any] = {}
        if employee_keys:
            args["FilterByEmployee"] = employee_keys
        if company_keys:
            args["FilterByCompany"] = company_keys
        if submitted is not None:
            args["FilterBySubmitted"] = submitted
        if rejected is not None:
            args["FilterByRejected"] = rejected
        if earliest_date:
            args["FilterByEarliestTimesheetDate"] = earliest_date
        if latest_date:
            args["FilterByLatestTimesheetDate"] = latest_date
        content = self._call("ListTimesheets", args or None)
        return content.get("Timesheets", []) if content else []

    def get_timesheets(self, timesheet_keys: list[int]) -> list[dict]:
        content = self._call("GetTimesheets", {"RequestedTimesheets": timesheet_keys})
        return content.get("Timesheets", []) if content else []

    def list_timesheet_non_work_days(
        self,
        earliest_date: str | None = None,
        latest_date: str | None = None,
        company_keys: list[int] | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if earliest_date:
            args["FilterByEarliestDate"] = earliest_date
        if latest_date:
            args["FilterByLatestDate"] = latest_date
        if company_keys:
            args["FilterByCompany"] = company_keys
        content = self._call("ListTimesheetNonWorkDays", args or None)
        return content.get("NonWorkDays", []) if content else []

    # ------------------------------------------------------------------
    # GL Accounts
    # ------------------------------------------------------------------

    def list_gl_accounts(
        self,
        status: list[str] | None = None,
        account_group: list[int] | None = None,
        account_type: list[str] | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if status:
            args["FilterByStatus"] = status
        if account_group:
            args["FilterByAccountGroup"] = account_group
        if account_type:
            args["FilterByType"] = account_type
        content = self._call("ListGLAccounts", args or None)
        return content.get("GLAccounts", []) if content else []

    def get_gl_accounts(
        self,
        gl_account_keys: list[int] | None = None,
        status: list[str] | None = None,
        account_group: list[int] | None = None,
        account_type: list[str] | None = None,
        as_of_date: str | None = None,
        exclude_close_year_entries: bool = False,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if gl_account_keys:
            args["RequestedGLAccounts"] = gl_account_keys
        if status:
            args["FilterByStatus"] = status
        if account_group:
            args["FilterByAccountGroup"] = account_group
        if account_type:
            args["FilterByType"] = account_type
        if as_of_date:
            args["AsOfDate"] = as_of_date
        if exclude_close_year_entries:
            args["ExcludeCloseYearEntries"] = True
        content = self._call("GetGLAccounts", args or None)
        return content.get("GLAccounts", []) if content else []

    # ------------------------------------------------------------------
    # Expense Reports  (API user sees own reports only)
    # ------------------------------------------------------------------

    def list_expense_reports(
        self,
        company_keys: list[int] | None = None,
        supervisor_keys: list[int] | None = None,
        is_processed: bool | None = None,
        name_like: str | None = None,
        earliest_beginning_date: str | None = None,
        latest_beginning_date: str | None = None,
        earliest_ending_date: str | None = None,
        latest_ending_date: str | None = None,
        earliest_modified: str | None = None,
        latest_modified: str | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if company_keys:
            args["FilterByCompany"] = company_keys
        if supervisor_keys:
            args["FilterBySupervisor"] = supervisor_keys
        if is_processed is not None:
            args["FilterByIsProcessed"] = is_processed
        if name_like:
            args["FilterByNameLike"] = name_like
        if earliest_beginning_date:
            args["FilterByEarliestBeginningDate"] = earliest_beginning_date
        if latest_beginning_date:
            args["FilterByLatestBeginningDate"] = latest_beginning_date
        if earliest_ending_date:
            args["FilterByEarliestEndingDate"] = earliest_ending_date
        if latest_ending_date:
            args["FilterByLatestEndingDate"] = latest_ending_date
        if earliest_modified:
            args["FilterByEarliestModifiedDate"] = earliest_modified
        if latest_modified:
            args["FilterByLatestModifiedDate"] = latest_modified
        content = self._call("ListExpenseReports", args or None)
        return content.get("ExpenseReports", []) if content else []

    def get_expense_reports(self, expense_report_keys: list[int]) -> list[dict]:
        content = self._call(
            "GetExpenseReports", {"RequestedExpenseReports": expense_report_keys}
        )
        return content.get("ExpenseReports", []) if content else []

    def download_expense_attachment(self, file_key: int) -> dict:
        content = self._call("DownloadExpenseReports", {"FileKey": file_key})
        return content or {}

    # ------------------------------------------------------------------
    # Vendors
    # ------------------------------------------------------------------

    def list_vendors(
        self,
        status: list[str] | None = None,
        name_like: str | None = None,
        company_keys: list[int] | None = None,
        vendor_type_keys: list[int] | None = None,
        earliest_modified: str | None = None,
        latest_modified: str | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if status:
            args["FilterByStatus"] = status
        if name_like:
            args["FilterByNameLike"] = name_like
        if company_keys:
            args["FilterByCompany"] = company_keys
        if vendor_type_keys:
            args["FilterByVendorType"] = vendor_type_keys
        if earliest_modified:
            args["FilterByEarliestModifiedDate"] = earliest_modified
        if latest_modified:
            args["FilterByLatestModifiedDate"] = latest_modified
        content = self._call("ListVendors", args or None)
        return content.get("Vendors", []) if content else []

    def get_vendors(self, vendor_keys: list[int]) -> list[dict]:
        content = self._call("GetVendors", {"RequestedVendors": vendor_keys})
        return content.get("Vendors", []) if content else []

    def list_vendor_types(
        self,
        status: list[str] | None = None,
        is_credit_card: bool | None = None,
        is_consultant: bool | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if status:
            args["FilterByStatus"] = status
        if is_credit_card is not None:
            args["FilterByIsCreditCard"] = is_credit_card
        if is_consultant is not None:
            args["FilterByIsConsultant"] = is_consultant
        content = self._call("ListVendorTypes", args or None)
        return content.get("VendorTypes", []) if content else []

    def list_vendor_invoices(
        self,
        vendor_keys: list[int] | None = None,
        status: list[str] | None = None,
        earliest_date: str | None = None,
        latest_date: str | None = None,
        earliest_modified: str | None = None,
        latest_modified: str | None = None,
    ) -> list[dict]:
        args: dict[str, Any] = {}
        if vendor_keys:
            args["FilterByVendor"] = vendor_keys
        if status:
            args["FilterByStatus"] = status
        if earliest_date:
            args["FilterByEarliestDate"] = earliest_date
        if latest_date:
            args["FilterByLatestDate"] = latest_date
        if earliest_modified:
            args["FilterByEarliestModifiedDate"] = earliest_modified
        if latest_modified:
            args["FilterByLatestModifiedDate"] = latest_modified
        content = self._call("ListVendorInvoices", args or None)
        return content.get("VendorInvoices", []) if content else []

    def get_vendor_invoices(self, vendor_invoice_keys: list[int]) -> list[dict]:
        content = self._call(
            "GetVendorInvoices", {"RequestedVendorInvoices": vendor_invoice_keys}
        )
        return content.get("VendorInvoices", []) if content else []

    # ------------------------------------------------------------------
    # Reference / lookup data (simple list methods, no complex filters)
    # ------------------------------------------------------------------

    def list_account_groups(self) -> list[dict]:
        content = self._call("ListAccountGroups")
        return content.get("AccountGroups", []) if content else []

    def list_activities(self, status: list[str] | None = None) -> list[dict]:
        args = {"FilterByStatus": status} if status else None
        content = self._call("ListActivities", args)
        return content.get("Activities", []) if content else []

    def list_bank_accounts(self, status: list[str] | None = None) -> list[dict]:
        args = {"FilterByStatus": status} if status else None
        content = self._call("ListBankAccounts", args)
        return content.get("BankAccounts", []) if content else []

    def list_companies(self) -> list[dict]:
        content = self._call("ListCompanies")
        return content.get("Companies", []) if content else []

    def list_deductions(self) -> list[dict]:
        content = self._call("ListDeductions")
        return content.get("Deductions", []) if content else []

    def list_departments(self, status: list[str] | None = None) -> list[dict]:
        args = {"FilterByStatus": status} if status else None
        content = self._call("ListDepartments", args)
        return content.get("Departments", []) if content else []

    def list_fringes(self) -> list[dict]:
        content = self._call("ListFringes")
        return content.get("Fringes", []) if content else []

    def list_invoice_formats(self) -> list[dict]:
        content = self._call("ListInvoiceFormats")
        return content.get("InvoiceFormats", []) if content else []

    def list_marketing_final_dispositions(self) -> list[dict]:
        content = self._call("ListMarketingFinalDispositions")
        return content.get("MarketingFinalDispositions", []) if content else []

    def list_marketing_stages(self) -> list[dict]:
        content = self._call("ListMarketingStages")
        return content.get("MarketingStages", []) if content else []

    def list_overhead_groups(self) -> list[dict]:
        content = self._call("ListOverheadGroups")
        return content.get("OverheadGroups", []) if content else []

    def list_payroll_taxes(self) -> list[dict]:
        content = self._call("ListPayrollTaxes")
        return content.get("PayrollTaxes", []) if content else []

    def list_pays(self) -> list[dict]:
        content = self._call("ListPays")
        return content.get("Pays", []) if content else []

    def list_rate_tables(self, status: list[str] | None = None) -> list[dict]:
        args = {"FilterByStatus": status} if status else None
        content = self._call("ListRateTables", args)
        return content.get("RateTables", []) if content else []

    def list_wage_tables(self, status: list[str] | None = None) -> list[dict]:
        args = {"FilterByStatus": status} if status else None
        content = self._call("ListWageTables", args)
        return content.get("WageTables", []) if content else []
