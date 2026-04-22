#!/bin/bash
# Bump version (patch, minor, or major)
# Usage: ./scripts/bump_version.sh [patch|minor|major]
# Requires: pip install semver

set -e

RELEASE_TYPE="${1:-patch}"

if [[ ! "$RELEASE_TYPE" =~ ^(patch|minor|major)$ ]]; then
    echo "Usage: $0 [patch|minor|major]"
    exit 1
fi

# Find version.txt (could be at repo root or in token/)
if [ -f "version.txt" ]; then
    VERSION_FILE="version.txt"
elif [ -f "../version.txt" ]; then
    VERSION_FILE="../version.txt"
else
    VERSION_FILE="version.txt"
fi

# Create version file if it doesn't exist
if [ ! -f "$VERSION_FILE" ]; then
    echo "0.1.0" > "$VERSION_FILE"
    echo "Created $VERSION_FILE with initial version 0.1.0"
fi

CURRENT_VERSION=$(cat "$VERSION_FILE")

# Calculate new version
NEW_VERSION=$(python3 -c "import semver; v=semver.VersionInfo.parse('${CURRENT_VERSION}'); print(v.bump_${RELEASE_TYPE}())")

echo "Bumping version: ${CURRENT_VERSION} -> ${NEW_VERSION}"
echo "${NEW_VERSION}" > "$VERSION_FILE"

echo "✅ Version bumped to ${NEW_VERSION}"
echo ""
echo "To commit: git add version.txt && git commit -m 'Bump version to v${NEW_VERSION}'"
