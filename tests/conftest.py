"""Mock revenueholdings_license for tests so CLI commands don't hit the paywall.

This must be in conftest.py (top-level) so it runs before any test module
imports apighost.cli, which conditionally imports revenueholdings_license.

The real require_license(tool_name, daily_limit=50) checks rate limits and
calls sys.exit(1) when the free-tier daily cap is reached. We replace it
with a stub that always returns a LicenseStatus indicating the tool is allowed.
"""
import sys
from unittest.mock import MagicMock

# --- Build a mock module that matches the real package API ---

# Stub LicenseStatus that always reports "allowed"
class _MockLicenseStatus:
    """Mimics revenueholdings_license.LicenseStatus for test env."""
    def __init__(self, tool_name="apighost"):
        self.allowed = True
        self.limited = False
        self.remaining = 999
        self.daily_limit = -1  # unlimited
        self.error = None
        self.tier = "pro"

_mock_module = MagicMock()

# Key functions that the CLI calls — must return correct types
_mock_module.require_license = lambda tool_name, daily_limit=None: _MockLicenseStatus(tool_name)
_mock_module.check_rate_limit = MagicMock(return_value=True)
_mock_module.check_license = lambda tool_name, daily_limit=None: _MockLicenseStatus(tool_name)
_mock_module.get_license_info = MagicMock(return_value=MagicMock(tier=MagicMock(gte=lambda t: True)))

# Enums / classes that might be referenced
_mock_module.LicenseStatus = _MockLicenseStatus
_mock_module.LicenseError = Exception
_mock_module.UpgradeRequiredError = Exception
_mock_module.TIERS = {"free": {}, "pro": {}, "team": {}, "enterprise": {}}

# Insert *before* any import resolves it.
# setdefault avoids overwriting if the real package is already loaded
# (shouldn't happen in a fresh test worker).
sys.modules.setdefault("revenueholdings_license", _mock_module)
sys.modules.setdefault("revenueholdings_license.decorators", _mock_module)
sys.modules.setdefault("revenueholdings_license.rate_limit", _mock_module)
sys.modules.setdefault("revenueholdings_license.rate_limiter", _mock_module)
sys.modules.setdefault("revenueholdings_license.core", _mock_module)
sys.modules.setdefault("revenueholdings_license.gate", _mock_module)
sys.modules.setdefault("revenueholdings_license.license", _mock_module)
