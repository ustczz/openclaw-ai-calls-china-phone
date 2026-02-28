#!/bin/bash
# callout.sh - Make an AI phone call via Stepone AI
# Usage: ./callout.sh <phone_number> <task> [options]
#
# Examples:
#   ./callout.sh "13800138000" "通知您明天上午9点开会"
#   ./callout.sh "13800138000" "提醒他明天上班" --wait

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

# 验证手机号
validate_phone() {
    local phone="$1"
    if [[ ! "$phone" =~ ^1[3-9][0-9]{9}$ ]]; then
        echo "Error: Invalid phone number (must be 11 digits starting with 1)"
        return 1
    fi
    return 0
}

# 检查帮助
for arg in "$@"; do
    if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
        echo "Usage: $0 <phone_number> <task> [options]"
        echo ""
        echo "Arguments:"
        echo "  phone_number    Phone number (11 digits, e.g., 13800138000)"
        echo "  task            Instructions for the AI agent"
        echo ""
        echo "Options:"
        echo "  --wait                Wait for call to complete and show result"
        echo "  --help                Show this help"
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
PHONE_NUMBER=""
TASK=""
WAIT_FOR_COMPLETION="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --wait)
            WAIT_FOR_COMPLETION="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <phone_number> <task> [options]"
            echo ""
            echo "Arguments:"
            echo "  phone_number    Phone number (11 digits, e.g., 13800138000)"
            echo "  task            Instructions for the AI agent"
            echo ""
            echo "Options:"
            echo "  --wait                Wait for call to complete and show result"
            echo "  --help                Show this help"
            exit 0
            ;;
        *)
            if [[ -z "$PHONE_NUMBER" ]]; then
                PHONE_NUMBER="$1"
            elif [[ -z "$TASK" ]]; then
                TASK="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$PHONE_NUMBER" ]] || [[ -z "$TASK" ]]; then
    echo "Error: Phone number and task are required"
    echo "Usage: $0 <phone_number> <task> [options]"
    exit 1
fi

# 验证手机号
if ! validate_phone "$PHONE_NUMBER"; then
    exit 1
fi

# 转义用户输入
SAFE_PHONE=$(json_escape "$PHONE_NUMBER")
SAFE_TASK=$(json_escape "$TASK")

# 构建请求
REQUEST_BODY="{\"phones\": \"$SAFE_PHONE\", \"user_requirement\": \"$SAFE_TASK\"}"

# 发起呼叫
echo "📞 Initiating call to $PHONE_NUMBER..."
echo "📝 Task: $TASK"
echo ""

RESPONSE=$(curl -s -X POST "https://open-skill-api.steponeai.com/api/v1/callinfo/initiate_call" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $STEPONEAI_API_KEY" \
    -d "$REQUEST_BODY")

# 检查错误
SUCCESS=$(echo "$RESPONSE" | grep -o '"success":[^,}]*' | cut -d':' -f2)
if [[ "$SUCCESS" != "true" ]]; then
    ERROR_MSG=$(echo "$RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
    echo "❌ Error: $ERROR_MSG"
    exit 1
fi

# 提取call_id
CALL_ID=$(echo "$RESPONSE" | grep -o '"call_ids":\["[^"]*"\]' | grep -o '\[".*"\]' | sed 's/\["//;s/"\]//')
if [[ -z "$CALL_ID" ]]; then
    CALL_ID=$(echo "$RESPONSE" | grep -o '"provider_call_id":"[^"]*"' | cut -d'"' -f4)
fi

if [[ -z "$CALL_ID" ]]; then
    echo "❌ Error: No call ID returned"
    echo "$RESPONSE"
    exit 1
fi

echo "✅ Call initiated!"
echo "📱 Call ID: $CALL_ID"
echo ""

# 如果有--wait标志，等待完成
if [[ "$WAIT_FOR_COMPLETION" == "true" ]]; then
    echo "⏳ Waiting for call to complete..."
    
    while true; do
        sleep 10
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        
        CALL_STATUS=$("$SCRIPT_DIR/callinfo.sh" "$CALL_ID" --json 2>/dev/null || echo '{}')
        DURATION=$(echo "$CALL_STATUS" | grep -o '"duration_seconds":[0-9]*' | cut -d':' -f2)
        
        if [[ -n "$DURATION" && "$DURATION" != "null" ]]; then
            echo ""
            echo "📋 Call completed!"
            "$SCRIPT_DIR/callinfo.sh" "$CALL_ID"
            break
        fi
        
        echo -n "."
    done
else
    echo "💡 Check status with: ./callinfo.sh $CALL_ID"
fi
