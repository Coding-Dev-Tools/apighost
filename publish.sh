#!/usr/bin/env bash
set -euo pipefail

# Pre-publish checks
echo " Running pre-publish checks..."
pytest -v --tb=short

echo ""
echo " Building package..."
rm -rf dist/ build/ *.egg-info
python -m build

echo ""
echo " Package built. Files:"
ls -lh dist/

echo ""
echo " To publish to PyPI:"
echo "   twine upload dist/*"
echo ""
echo " Requires PYPI_API_TOKEN set in GitHub secrets."
echo " Trigger via: gh release create v0.1.0 --generate-notes"
