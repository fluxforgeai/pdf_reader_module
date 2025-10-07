#!/bin/bash
# Simple API test script

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

API_URL="http://localhost:8000"

echo -e "${BLUE}=== Bank Statement Parser API Test ===${NC}\n"

# Test 1: Health Check
echo -e "${BLUE}1. Testing health endpoint...${NC}"
response=$(curl -s "${API_URL}/api/statements/health")
echo "Response: $response"
if [[ $response == *"ok"* ]]; then
    echo -e "${GREEN}✓ Health check passed${NC}\n"
else
    echo -e "${RED}✗ Health check failed${NC}\n"
    exit 1
fi

# Test 2: Parse PDF (requires sample PDF)
if [ -f "$1" ]; then
    echo -e "${BLUE}2. Testing parse endpoint with: $1${NC}"

    response=$(curl -s -X POST "${API_URL}/api/statements/parse" \
        -F "file=@$1" \
        -F "bank_name=Sample Bank")

    echo "Response (first 500 chars):"
    echo "$response" | head -c 500
    echo "..."

    if [[ $response == *"transaction_count"* ]]; then
        echo -e "\n${GREEN}✓ Parse endpoint passed${NC}\n"

        # Extract transaction count
        count=$(echo "$response" | grep -o '"transaction_count":[0-9]*' | grep -o '[0-9]*')
        echo -e "Found ${GREEN}${count}${NC} transactions\n"
    else
        echo -e "\n${RED}✗ Parse endpoint failed${NC}\n"
    fi
else
    echo -e "${BLUE}2. Skipping parse test (no PDF provided)${NC}"
    echo "   Usage: ./test_api.sh <path_to_pdf>"
    echo ""
fi

# Test 3: Root endpoint
echo -e "${BLUE}3. Testing root endpoint...${NC}"
response=$(curl -s "${API_URL}/")
echo "Response: $response"
if [[ $response == *"Bank Statement Parser"* ]]; then
    echo -e "${GREEN}✓ Root endpoint passed${NC}\n"
else
    echo -e "${RED}✗ Root endpoint failed${NC}\n"
fi

echo -e "${BLUE}=== Test Complete ===${NC}"
echo -e "View API docs at: ${BLUE}${API_URL}/docs${NC}"
