"""Synthetic HTTP contract tests. No credentials or live Ajera calls."""

import asyncio
import json

import httpx
import pytest

import ajera_client
from ajera_client import AjeraClient, AjeraError
import server


def mock_api(monkeypatch, responder):
    requests = []
    original_client = httpx.Client

    def handle(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if payload["Method"] == "CreateAPISession":
            body = {"ResponseCode": 200, "Content": {"SessionToken": "synthetic-token"}}
        elif payload["Method"] == "EndAPISession":
            body = {"ResponseCode": 200, "Content": {}}
        else:
            body = responder(payload)
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handle)
    monkeypatch.setattr(
        ajera_client.httpx, "Client",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )
    return AjeraClient(api_url="https://example.invalid/api"), requests


def success(rows):
    return {"ResponseCode": 200, "Errors": [], "Content": {"JournalEntries": rows}}


def test_list_routes_v2_and_preserves_false_filter(monkeypatch):
    client, requests = mock_api(monkeypatch, lambda _: success([]))
    assert client.list_journal_entries(
        company_keys=[101], earliest_date="2026-01-01", latest_date="2026-01-31",
        basis="Both", voided=False,
    ) == []
    assert requests[0]["APIVersion"] == 2
    assert requests[1]["Method"] == "ListJournalEntries"
    assert requests[1]["MethodArguments"] == {
        "FilterByCompany": [101],
        "FilterByEarliestAccountingDate": "2026-01-01",
        "FilterByLatestAccountingDate": "2026-01-31",
        "FilterByBasis": "Both", "FilterByVoided": False,
    }
    client.list_journal_entries()
    assert requests[-1]["MethodArguments"] == {}
    assert len([r for r in requests if r["Method"] == "CreateAPISession"]) == 1
    client.close_sessions()
    assert requests[-1]["Method"] == "EndAPISession"


@pytest.mark.parametrize("arguments", [
    {"earliest_date": "20260101"}, {"latest_date": "2026-02-30"},
    {"earliest_date": "2026-03-01", "latest_date": "2026-02-01"},
    {"basis": "all"}, {"voided": "false"}, {"company_keys": []},
    {"company_keys": [False]}, {"company_keys": [-1]},
])
def test_invalid_filters_fail_before_network(monkeypatch, arguments):
    client, requests = mock_api(monkeypatch, lambda _: pytest.fail("Unexpected HTTP request"))
    with pytest.raises(ValueError):
        client.list_journal_entries(**arguments)
    assert requests == []


def test_get_batches_deduplicates_and_strips_snapshots(monkeypatch):
    def respond(payload):
        assert payload["Method"] == "GetJournalEntries"
        return success([
            {"JournalEntryKey": key, "IsVoided": key == 106,
             "Details": [] if key == 106 else [{"Debit": 1.25}],
             "UnchangedJournalEntries": {"Details": "opaque-example", "Header": "opaque"}}
            for key in payload["MethodArguments"]["RequestedJournalEntries"]
        ])

    client, requests = mock_api(monkeypatch, respond)
    rows = client.get_journal_entries([101, 102, 103, 104, 105, 106, 101])
    assert requests[0]["APIVersion"] == 2
    assert [r["MethodArguments"]["RequestedJournalEntries"] for r in requests[1:]] == [
        [101, 102, 103, 104, 105], [106],
    ]
    assert [row["JournalEntryKey"] for row in rows] == list(range(101, 107))
    assert all("UnchangedJournalEntries" not in row for row in rows)
    assert rows[0]["Details"] == [{"Debit": 1.25}]
    assert rows[-1]["IsVoided"] is True and rows[-1]["Details"] == []


@pytest.mark.parametrize("keys", [[], [0], [-1], [True], ["101"], 101])
def test_invalid_get_keys_fail_before_network(monkeypatch, keys):
    client, requests = mock_api(monkeypatch, lambda _: pytest.fail("Unexpected HTTP request"))
    with pytest.raises(ValueError):
        client.get_journal_entries(keys)
    assert requests == []


@pytest.mark.parametrize("response", [
    {"ResponseCode": -100, "Errors": [{"ErrorID": -1, "ErrorMessage": "Key missing"}],
     "Content": {"JournalEntries": [{"JournalEntryKey": 101}]}},
    {"ResponseCode": -100, "Errors": [{"ErrorID": 1, "ErrorMessage": "Required"}]},
    {"ResponseCode": 200, "Errors": [{"ErrorID": -1, "ErrorMessage": "Failure"}]},
    {"ResponseCode": -90, "Errors": [], "Message": "Wrong API version"},
    success([{"JournalEntryKey": 101}]),
    success([{"JournalEntryKey": 101}, {"JournalEntryKey": 999}]),
    success([{"JournalEntryKey": 101}, {"JournalEntryKey": 102}, {"JournalEntryKey": 102}]),
])
def test_get_never_accepts_partial_or_error_response(monkeypatch, response):
    client, _ = mock_api(monkeypatch, lambda _: response)
    with pytest.raises(AjeraError):
        client.get_journal_entries([101, 102])


@pytest.mark.parametrize("count", [0, 2, 500])
def test_tool_reports_cap_and_empty_results(monkeypatch, count):
    client, _ = mock_api(
        monkeypatch, lambda _: success([{"Journal Entry Key": key} for key in range(count)]),
    )
    monkeypatch.setattr(server, "_client", client)
    result = json.loads(server.list_journal_entries())
    assert result["ReturnedCount"] == count
    assert result["Limit"] == 500
    assert result["PossiblyTruncated"] is (count >= 500)
    assert ("Warning" in result) is (count >= 500)


def test_get_tool_keeps_visible_lines_and_no_snapshots(monkeypatch):
    client, _ = mock_api(monkeypatch, lambda _: success([
        {"JournalEntryKey": 101, "Details": [{"Credit": 1.25}],
         "UnchangedJournalEntries": {"Header": "opaque", "Details": "opaque"}},
    ]))
    monkeypatch.setattr(server, "_client", client)
    result = json.loads(server.get_journal_entry([101]))
    assert result == [{"JournalEntryKey": 101, "Details": [{"Credit": 1.25}]}]
    assert server.get_journal_entry([]).startswith("Invalid request:")


def test_registered_tools_are_reads_and_new_schema_supports_tristate():
    tools = asyncio.run(server.mcp.list_tools())
    by_name = {tool.name: tool for tool in tools}
    assert {"list_journal_entries", "get_journal_entry"} <= by_name.keys()
    assert all(not name.startswith(("create_", "update_", "delete_", "void_", "submit_"))
               for name in by_name)
    schema = by_name["list_journal_entries"].inputSchema
    voided_schema = schema["properties"]["voided"]
    assert {option["type"] for option in voided_schema["anyOf"]} == {"boolean", "null"}
    assert "journal_entry_keys" in by_name["get_journal_entry"].inputSchema["required"]
