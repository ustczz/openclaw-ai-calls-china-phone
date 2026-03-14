#!/bin/bash
# stream_chat.sh - Stream real-time AI conversation during a phone call (SSE)
# Usage: ./stream_chat.sh <call_id> [options]
#
# Examples:
#   ./stream_chat.sh "8bbbbbbb-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
#   ./stream_chat.sh "8bbbbbbb-xxxx-xxxx-xxxx-xxxxxxxxxxxx" --json

set -e

SKILL_VERSION="1.0.0"
API_BASE="https://open-skill-api.steponeai.com"

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
        echo "Stream real-time AI conversation content during a phone call."
        echo "Connect as soon as the call is initiated; the stream will show"
        echo "AI and user dialogue in real time until the call ends."
        echo ""
        echo "Options:"
        echo "  --json    Output raw SSE data (no formatting)"
        echo "  --help    Show this help"
        echo ""
        echo "Signals:"
        echo "  [DONE]    Call ended normally"
        echo "  [TIMEOUT] Call not answered within 30 seconds"
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
    echo "Set it in your environment or in ~/.clawd/secrets.json"
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

if ! validate_call_id "$CALL_ID"; then
    exit 1
fi

SAFE_CALL_ID=$(json_escape "$CALL_ID")

if [[ "$JSON_OUTPUT" != "true" ]]; then
    echo "🎙️  Streaming real-time conversation"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Call ID: $CALL_ID"
    echo "Waiting for connection..."
    echo ""
fi

# SSE streaming via curl
curl -sN -X POST "${API_BASE}/api/v1/callinfo/stream_chat_history" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $STEPONEAI_API_KEY" \
    -H "X-Skill-Version: $SKILL_VERSION" \
    -d "{\"call_id\": \"$SAFE_CALL_ID\"}" 2>/dev/null | while IFS= read -r line; do

    # skip empty lines and keep-alive comments
    [[ -z "$line" ]] && continue
    [[ "$line" == ": keep-alive" ]] && continue

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo "$line"
        continue
    fi

    # parse data: {...} lines
    if [[ "$line" == data:* ]]; then
        PAYLOAD="${line#data: }"
        PAYLOAD="${PAYLOAD## }"

        ROLE=$(echo "$PAYLOAD" | grep -o '"role"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
        CONTENT=$(echo "$PAYLOAD" | grep -o '"content"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')

        if [[ "$ROLE" == "system" && "$CONTENT" == "[DONE]" ]]; then
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "📞 Call ended"
            break
        fi

        if [[ "$ROLE" == "system" && "$CONTENT" == "[TIMEOUT]" ]]; then
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "⏰ Timeout - call not answered"
            break
        fi

        if [[ "$ROLE" == "assistant" ]]; then
            echo "🤖 AI: $CONTENT"
        elif [[ "$ROLE" == "user" ]]; then
            echo "👤 User: $CONTENT"
        elif [[ -n "$ROLE" ]]; then
            echo "[$ROLE] $CONTENT"
        fi
    fi
done

EXIT_CODE=${PIPESTATUS[0]}
if [[ $EXIT_CODE -ne 0 && "$JSON_OUTPUT" != "true" ]]; then
    echo "❌ Connection error (exit code: $EXIT_CODE)"
    exit 1
fi
