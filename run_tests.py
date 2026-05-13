"""
Reads credentials from ../ajera-mcp/.mcp.json and runs the endpoint tests.
No shell env var quoting issues.
"""
import json, os, sys

# Load credentials from the v1 .mcp.json
here = os.path.dirname(os.path.abspath(__file__))
mcp_json = os.path.join(here, "..", ".mcp.json")

with open(mcp_json) as f:
    cfg = json.load(f)

env = cfg["mcpServers"]["ajera"]["env"]
os.environ["AJERA_API_URL"]  = env["AJERA_API_URL"]
os.environ["AJERA_USERNAME"] = env["AJERA_USERNAME"]
os.environ["AJERA_PASSWORD"] = env["AJERA_PASSWORD"]

# Now run the tests
import test_new_endpoints
test_new_endpoints.run()
