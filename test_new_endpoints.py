"""
Quick verification script for all new endpoints in the v2 read-only MCP.
Run from the ajera-mcp-v2/ directory after setting environment variables.

Usage:
    set AJERA_API_URL=...
    set AJERA_USERNAME=...
    set AJERA_PASSWORD=...
    python test_new_endpoints.py
"""

import os
import sys

# Allow running from parent dir
sys.path.insert(0, os.path.dirname(__file__))

from ajera_client import AjeraClient, AjeraError

API_URL = os.environ.get("AJERA_API_URL", "")
USERNAME = os.environ.get("AJERA_USERNAME", "")
PASSWORD = os.environ.get("AJERA_PASSWORD", "")

PASS = "OK"
FAIL = "XX"
WARN = "??"

results = []


def test(label: str, fn):
    try:
        data = fn()
        count = len(data) if isinstance(data, list) else "non-list"
        status = PASS
        note = f"{count} records"
        results.append((status, label, note, None))
        return data
    except AjeraError as e:
        results.append((FAIL, label, str(e)[:100], "AjeraError"))
        return []
    except Exception as e:
        results.append((FAIL, label, str(e)[:100], type(e).__name__))
        return []


def run():
    if not API_URL:
        print("ERROR: AJERA_API_URL not set")
        sys.exit(1)

    c = AjeraClient(api_url=API_URL, username=USERNAME, password=PASSWORD)

    print("\n=== Ajera MCP v2 — New Endpoint Verification ===\n")

    # --- Reference lookup tables ---
    test("ListAccountGroups",               lambda: c.list_account_groups())
    test("ListActivities",                  lambda: c.list_activities())
    test("ListBankAccounts",                lambda: c.list_bank_accounts())
    test("ListCompanies",                   lambda: c.list_companies())
    test("ListContactTypes",                lambda: c.list_contact_types())
    test("ListDeductions",                  lambda: c.list_deductions())
    test("ListDepartments",                 lambda: c.list_departments())
    test("ListFringes",                     lambda: c.list_fringes())
    test("ListInvoiceFormats",              lambda: c.list_invoice_formats())
    test("ListMarketingFinalDispositions",  lambda: c.list_marketing_final_dispositions())
    test("ListMarketingStages",             lambda: c.list_marketing_stages())
    test("ListOverheadGroups",              lambda: c.list_overhead_groups())
    test("ListPayrollTaxes",               lambda: c.list_payroll_taxes())
    test("ListPays",                        lambda: c.list_pays())
    test("ListRateTables",                  lambda: c.list_rate_tables())
    test("ListWageTables",                  lambda: c.list_wage_tables())

    # --- Project extensions ---
    test("ListProjectTemplates",            lambda: c.list_project_templates())
    test("ListChargeablePhases (ProjectKey=28)", lambda: c.list_chargeable_phases(28))
    test("GetProjectTotals (key=28)",       lambda: c.get_project_totals(28))
    test("GetProjectsWithResources (key=28)",  lambda: c.get_projects_with_resources(project_keys=[28]))

    # --- Timesheet extension (v2 session) ---
    test("ListTimesheetNonWorkDays",        lambda: c.list_timesheet_non_work_days(
        earliest_date="2026-01-01", latest_date="2026-12-31"
    ))

    # --- Vendor invoices ---
    test("ListVendorInvoices (no filter)",  lambda: c.list_vendor_invoices())

    # --- Project templates detail (use first key if available) ---
    templates = []
    try:
        templates = c.list_project_templates()
    except Exception:
        pass
    if templates:
        first_key = templates[0].get("ProjectTemplateKey") or templates[0].get("Key")
        if first_key:
            test(f"GetProjectTemplates (key={first_key})",
                 lambda: c.get_project_templates([first_key]))
        else:
            results.append((WARN, "GetProjectTemplates", "Could not determine key field name from ListProjectTemplates response", None))
    else:
        results.append((WARN, "GetProjectTemplates", "Skipped — no templates returned by ListProjectTemplates", None))

    # --- Vendor invoice detail (use first key if available) ---
    invoices = []
    try:
        invoices = c.list_vendor_invoices()
    except Exception:
        pass
    if invoices:
        first_key = invoices[0].get("VendorInvoiceKey") or invoices[0].get("Key")
        if first_key:
            test(f"GetVendorInvoices (key={first_key})",
                 lambda: c.get_vendor_invoices([first_key]))
        else:
            results.append((WARN, "GetVendorInvoices", "Could not determine key field name from ListVendorInvoices response", None))
    else:
        results.append((WARN, "GetVendorInvoices", "Skipped — no invoices returned by ListVendorInvoices", None))

    # --- Print summary ---
    print(f"{'Status':<4} {'Method':<45} {'Result'}")
    print("-" * 90)
    for status, label, note, _ in results:
        print(f"  {status}  {label:<45} {note}")

    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)
    warned = sum(1 for r in results if r[0] == WARN)
    print(f"\n  {passed} passed  |  {failed} failed  |  {warned} warnings\n")

    # --- Print first record for each new successful method ---
    print("\n=== Sample Data (first record per successful new method) ===\n")
    import json

    sample_calls = [
        ("ListAccountGroups",   lambda: c.list_account_groups()),
        ("ListActivities",      lambda: c.list_activities()),
        ("ListBankAccounts",    lambda: c.list_bank_accounts()),
        ("ListDepartments",     lambda: c.list_departments()),
        ("ListContactTypes",    lambda: c.list_contact_types()),
        ("ListPays",            lambda: c.list_pays()),
        ("ListRateTables",      lambda: c.list_rate_tables()),
        ("ListWageTables",      lambda: c.list_wage_tables()),
        ("ListProjectTemplates",lambda: c.list_project_templates()),
        ("ListChargeablePhases",lambda: c.list_chargeable_phases()),
        ("GetProjectTotals",    lambda: c.get_project_totals(28)),
        ("GetProjectsWithResources", lambda: c.get_projects_with_resources()),
        ("ListTimesheetNonWorkDays", lambda: c.list_timesheet_non_work_days(
            earliest_date="2026-01-01", latest_date="2026-12-31"
        )),
        ("ListVendorInvoices",  lambda: c.list_vendor_invoices()),
    ]

    for label, fn in sample_calls:
        try:
            data = fn()
            if data:
                print(f"--- {label} ---")
                print(json.dumps(data[0], indent=2, default=str))
                print()
        except Exception:
            pass


if __name__ == "__main__":
    run()
