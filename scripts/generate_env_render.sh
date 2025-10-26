#!/bin/bash

# Generate .env_render from .env for Render.com deployment
# - Removes comments and blank lines
# - Replaces URLs with Render.com deployment URL

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Source and target files
SOURCE_FILE=".env"
TARGET_FILE=".env_render"

# Usage
usage() {
    echo "Usage: $0 <render-url>"
    echo ""
    echo "Example:"
    echo "  $0 myapp.onrender.com"
    echo "  $0 https://myapp.onrender.com"
    echo ""
    echo "This will:"
    echo "  1. Remove comments and blank lines from .env"
    echo "  2. Replace all URLs with https://<render-url>"
    echo "  3. Save to .env_render"
    exit 1
}

# Check arguments
if [ $# -ne 1 ]; then
    echo -e "${RED}Error: Missing render URL argument${NC}"
    echo ""
    usage
fi

RENDER_URL="$1"

# Remove https:// prefix if present
RENDER_URL="${RENDER_URL#https://}"
RENDER_URL="${RENDER_URL#http://}"

# Remove trailing slash
RENDER_URL="${RENDER_URL%/}"

echo -e "${GREEN}Generating ${TARGET_FILE} for Render.com deployment${NC}"
echo "=================================================="
echo -e "${BLUE}Render URL: https://${RENDER_URL}${NC}"
echo ""

# Check if source file exists
if [ ! -f "$SOURCE_FILE" ]; then
    echo -e "${RED}Error: ${SOURCE_FILE} not found!${NC}"
    exit 1
fi

# Process .env file
# 1. Remove comments (lines starting with #)
# 2. Remove blank lines
# 3. Remove inline comments
# 4. Trim trailing whitespace
# 5. Replace URLs with Render URL
grep -v '^#' "$SOURCE_FILE" | \
    grep -v '^[[:space:]]*$' | \
    sed 's/#.*//' | \
    sed 's/[[:space:]]*$//' | \
    sed -E "s|https://[^/]+/|https://${RENDER_URL}.onrender.com/|g" > "$TARGET_FILE"

# Count lines
SOURCE_LINES=$(wc -l < "$SOURCE_FILE")
TARGET_LINES=$(wc -l < "$TARGET_FILE")
REMOVED_LINES=$((SOURCE_LINES - TARGET_LINES))

# Count URL replacements
URL_COUNT=$(grep -c "https://${RENDER_URL}/" "$TARGET_FILE" || true)

echo -e "${GREEN}✓ Generated ${TARGET_FILE}${NC}"
echo ""
echo "Statistics:"
echo "  Source lines:     $SOURCE_LINES"
echo "  Target lines:     $TARGET_LINES"
echo "  Removed lines:    $REMOVED_LINES (comments and blank lines)"
echo "  URL replacements: $URL_COUNT"
echo ""

# Show affected URLs
echo -e "${YELLOW}Replaced URLs:${NC}"
grep "https://${RENDER_URL}/" "$TARGET_FILE" | sed 's/^/  /' || echo "  (none)"
echo ""

# Show preview
echo -e "${YELLOW}Preview (first 15 lines):${NC}"
head -15 "$TARGET_FILE" | sed 's/^/  /'
if [ $(wc -l < "$TARGET_FILE") -gt 15 ]; then
    echo "  ..."
fi
echo ""

# Warning
echo -e "${YELLOW}⚠️  Important:${NC}"
echo "  - ${TARGET_FILE} contains sensitive data"
echo "  - DO NOT commit to git (.gitignore already excludes it)"
echo "  - Use this file for Render.com deployment only"
echo "  - Copy contents to Render.com environment variables"
echo ""

echo -e "${GREEN}✓ Done!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review ${TARGET_FILE}"
echo "  2. Copy environment variables to Render.com:"
echo "     Dashboard → Your Service → Environment"
echo "  3. Deploy"
echo ""

exit 0
