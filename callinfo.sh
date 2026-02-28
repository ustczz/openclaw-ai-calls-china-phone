#!/bin/bash
# callinfo.sh - Check the status of a Stepone AI phone call
# Usage: ./callinfo.sh <call_id> [options]

set -e

# JSON转义函数
json_escape() {
    local str="$1"
    str="${str//\\/\\\\}"
    str="${str//\"/\\\"}"
    str="${str//$'\n'/\\n}"
    str="${str//$'\r'/}"
    str="${str//$'\t'/\\t}"
    echo "$str"
}

# 验证call_id
validate_call_id() {
    local call_id="$1"
    if [[ ! "$call_id" =~ ^[a-zA-Z0-9^_-]+$ ]]; then
        echo "Error: Invalid call_id format"
        return 1
    fi
    return 0
}

# 检查帮助
for arg in "$@"; do
    if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
        echo "Usage: $0 <call_id> [options]"
        echo ""
        echo "Options:"
        echo "  --json    Output raw JSON"
        echo "  --help    Show this help"
        exit 0
    fi
done

# 加载API key
if [[ -z "$STEPONEAI_API_KEY" ]]; then
    if [[ -f ~/.clawd/secrets.json ]]; then
        STEPONEAI_API_KEY=$(grep -o '"steponeai_api_key"[[:space:]]*:[[:space:]]*"[^"]*"' ~/.clawd/secrets.json | sed 's/.*"\([^"]*\)"$/\1/')
    fi
fi

if [[ -z "$STEPONEAI_API_KEY" ]]; then
    echo "Error: STEPONEAI_API_KEY not set"
    exit 1
fi

# 解析参数
CALL_ID=""
JSON_OUTPUT="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            JSON_OUTPUT="true"
            shift
            ;;
        --help|-h)
            exit 0
            ;;
        *)
            CALL_ID="$1"
            shift
            ;;
    esac
done

if [[ -z "$CALL_ID" ]]; then
    echo "Error: Call ID required"
    echo "Usage: $0 <call_id>"
    exit 1
fi

# 验证call_id
if ! validate_call_id "$CALL_ID"; then
    exit 1
fi

# 转义
SAFE_CALL_ID=$(json_escape "$CALL_ID")

# 获取通话详情
RESPONSE=$(curl -s -X POST "https://open-skill-api.steponeai.com/api/v1/callinfo/search_callinfo" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $STEPONEAI_API_KEY" \
    -d "{\"call_id\": \"$SAFE_CALL_ID\"}")

if [[ "$JSON_OUTPUT" == "true" ]]; then
    echo "$RESPONSE"
    exit 0
fi

# 解析和显示结果
DURATION=$(echo "$RESPONSE" | grep -o '"duration_seconds":[0-9]*' | head -1 | cut -d':' -f2)
if [[ -z "$DURATION" || "$DURATION" == "null" ]]; then
    echo "⏳ Call not completed yet, please try again later"
    exit 0
fi

PHONE=$(echo "$RESPONSE" | grep -o '"phones":"[^"]*"' | cut -d'"' -f4)
TASK=$(echo "$RESPONSE" | grep -o '"user_requirement":"[^"]*"' | cut -d'"' -f4)
COST=$(echo "$RESPONSE" | grep -o '"cost":[0-9.]*' | head -1 | cut -d':' -f2)
BILLED=$(echo "$RESPONSE" | grep -o '"billed":[^,}]*' | head -1 | cut -d':' -f2)

echo "📱 Call Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Call ID:     $CALL_ID"
echo "Phone:       $PHONE"
echo "Task:        $TASK"
echo "Duration:    ${DURATION}s"
echo "Cost:        ¥$COST"
echo "Billed:      $BILLED"
echo ""

# 显示通话内容（如果有）
CALL_CONTENT=$(echo "$RESPONSE" | grep -o '"call_content":\[[^]]*\]' | sed 's/"call_content"://')
if [[ -n "$CALL_CONTENT" && "$CALL_CONTENT" != "null" ]]; then
    echo "📝 Transcript"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$RESPONSE" | grep -o '"content":"[^"]*"' | sed 's/"content":"//;s/"$//' | while read -r line; do
        ROLE=$(echo "$line" | grep -o '"role":"[^"]*"' | cut -d'"' -f4)
        CONTENT=$(echo "$line" | sed 's/.*"role":"[^"]*", *"content":"//;s/"}$//')
        echo "$ROLE: $CONTENT"
    done
    echo ""
fi

# 显示provider_response中的信息
PROVIDER_RESPONSE=$(echo "$RESPONSE" | grep -o '"provider_response":"[^"]*"' | sed 's/"provider_response":"//;s/"$//' | sed 's/\\"/"/g')
if [[ -n "$PROVIDER_RESPONSE" && "$PROVIDER_RESPONSE" != "null" ]]; then
    echo "📋 Provider Response"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$PROVIDER_RESPONSE" | sed 's/\\"/"/g'
    echo ""
fi
