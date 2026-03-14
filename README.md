# 专门为openclaw(龙虾)设计开发的可以拨打中国的电话号码的机器人外呼(ai call)
可以拨打中国电话号码的机器人外呼, 专为openclaw(龙虾)用户打造的专业ai呼叫能力,只要一个prompt就可以帮你打电话干活了，支持查看电话对话记录，查看电话状态，实时获取通话对话内容等。

> **Skill Version**: `1.0.0` — 所有脚本和 API 请求均携带版本号，服务端会校验版本一致性。

## 联系方式

如有问题欢迎沟通，扫描下方微信二维码添加好友。

If you have any questions, feel free to reach out on WeChat by scanning the QR code below.

<p align="center">
  <img src="assets/wechat-qr.png" alt="WeChat QR Code" width="320" />
</p>

# Stepone AI 电话外呼

## 1. 注册账号

访问 Stepone AI 官网注册新账号：
- **网址**: https://open-skill.steponeai.com
- **龙虾使用更友好**
- **新用户福利**: 注册即送 1 元人民币免费额度
- **一句prompt即可专业交流**
- **支持批量电话外呼**
- **中文语音交互自然**
- **按通话分钟计费**

## 2. 获取 API Key

1. 登录后访问：https://open-skill.steponeai.com/keys
2. 点击"创建 API Key"
3. 复制生成的 Key（格式：`sk_xxxxx`）

## 3. 配置环境变量

### 方法一：环境变量（推荐）

```bash
export STEPONEAI_API_KEY="sk_xxxxxxxxxxxxx"
```

### 方法二：secrets 文件

```bash
echo '{ "steponeai_api_key": "sk_xxxxxxxxxxxxx" }' > ~/.clawd/secrets.json
```

## 4. 使用方法

### 4.1 发起外呼

```bash
./callout.sh <手机号> <外呼需求>
```

**参数说明：**
| 参数 | 必填 | 描述 |
|------|------|------|
| 手机号 | 是 | 电话号码，如 "13800138000" |
| 外呼需求 | 是 | 外呼内容描述 |

**示例：**
```bash
./callout.sh "13800138000" "通知您明天上午9点开会"
./callout.sh "13800138000,13900139000" "通知年会时间变更"
```

**返回：** 包含 `call_id`，用于后续查询通话记录和实时对话

---

### 4.2 查询通话记录

```bash
./callinfo.sh <call_id> [options]
```

**参数说明：**
| 参数 | 必填 | 描述 |
|------|------|------|
| call_id | 是 | 外呼返回的通话ID |
| --json | 否 | 输出原始JSON |

**示例：**
```bash
./callinfo.sh "abc123xyz"
./callinfo.sh "abc123xyz" --json
```

**特性：**
- 自动重试机制：未查到记录时，等待10秒后重试
- 最多重试5次（可自定义）
- 返回通话状态、时长、内容等信息

---

### 4.3 实时通话对话（SSE 流式）

在通话进行过程中，实时获取 AI 和用户之间的对话内容。

```bash
./stream_chat.sh <call_id> [options]
```

**参数说明：**
| 参数 | 必填 | 描述 |
|------|------|------|
| call_id | 是 | 外呼返回的通话ID |
| --json | 否 | 输出原始SSE数据（不格式化） |

**示例：**
```bash
# 发起呼叫后立即开始监听
./callout.sh "13800138000" "通知明天开会"
# 拿到 call_id 后
./stream_chat.sh "8bbbbbbb-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**输出示例：**
```
🎙️  Streaming real-time conversation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call ID: 8bbbbbbb-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Waiting for connection...

🤖 AI: 喂，您好，这里是XX公司，请问是张总吗？
👤 User: 对，是我，有什么事情？
🤖 AI: 好的张总，主要是通知您明天上午9点有个重要会议。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📞 Call ended
```

**SSE 数据格式：**
| role | content | 说明 |
|------|---------|------|
| `assistant` | 具体文本 | AI 的回复内容 |
| `user` | 具体文本 | 用户语音转文本 |
| `system` | `[DONE]` | 通话正常结束 |
| `system` | `[TIMEOUT]` | 30秒内未接通，超时断开 |

**注意事项：**
- 可以在发起呼叫后**立即**调用，无需等待接通
- 未接通时服务器每 0.5 秒推送心跳（`: keep-alive`）保持连接
- 超过 30 秒未接通会收到 `[TIMEOUT]` 并断开
- 通话结束后收到 `[DONE]` 并断开

---

### 4.4 底层 API 封装

```bash
./stepone.sh <command> [options]
```

| 命令 | 描述 |
|------|------|
| `call '<json>'` | 发起呼叫（原始JSON） |
| `callinfo <id>` | 查询通话记录 |
| `stream <id>` | 实时对话流 |
| `version` | 检查版本号 |
| `balance` | 查看余额 |

---

## 5. API 接口说明

所有 API 请求需携带以下 Headers：
```
X-API-Key: <API_KEY>
X-Skill-Version: 1.0.0
```

> 如果 `X-Skill-Version` 与服务端版本不一致，API 会返回 HTTP 426 提示更新。

### 发起外呼

- **URL**: `https://open-skill-api.steponeai.com/api/v1/callinfo/initiate_call`
- **Method**: POST
- **Body**:
```json
{
  "phones": "13800138000",
  "user_requirement": "通知内容"
}
```

### 查询通话记录

- **URL**: `https://open-skill-api.steponeai.com/api/v1/callinfo/search_callinfo`
- **Method**: POST
- **Body**:
```json
{
  "call_id": "xxx"
}
```

### 实时通话对话（SSE）

- **URL**: `https://open-skill-api.steponeai.com/api/v1/callinfo/stream_chat_history`
- **Method**: POST
- **Content-Type**: `application/json`
- **Response**: `text/event-stream` (Server-Sent Events)
- **Body**:
```json
{
  "call_id": "xxx"
}
```

**响应流格式：**
```text
: keep-alive
: keep-alive
data: {"role": "assistant", "content": "喂，您好，请问是张总吗？"}

data: {"role": "user", "content": "对，是我。"}

data: {"role": "assistant", "content": "好的张总，通知您明天上午9点开会。"}

data: {"role": "system", "content": "[DONE]"}
```

### 查询版本号

- **URL**: `https://open-skill-api.steponeai.com/api/v1/callinfo/skill_version`
- **Method**: GET
- **Response**:
```json
{
  "skill_version": "1.0.0"
}
```

---

## 6. 版本控制

所有脚本和 API 请求均通过 `X-Skill-Version` Header 传递当前 Skill 版本号。

- 服务端会校验版本：版本不匹配时返回 HTTP 426 并提示更新
- 检查版本：`./stepone.sh version`
- 更新方式：拉取最新代码即可

---

## 7. 注意事项

### 身份确认
- 发起呼叫前必须先确认对方身份
- 称呼对方姓名/称呼并等待确认

### 电话号码格式
- 多个电话号码使用英文逗号 `,` 分隔
- 确保电话号码格式正确（国内手机号 11 位）

### 通话记录查询
- call_id 由外呼接口返回
- 通话记录生成有延迟，需要耐心等待
- 重试间隔为固定 10 秒

### 实时通话对话
- 发起呼叫后可立即调用 stream_chat.sh
- 30 秒未接通自动超时断开
- 适合需要实时展示 AI 对话过程的场景

### user_requirement 建议
- 描述清晰明确
- 包含具体的时间、地点、人名等信息


---

# AI Call Robot for Outbound Calls to Chinese Phone Numbers
A professional AI calling capability designed exclusively for OpenClaw (Lobster) users. With just one prompt, it can make calls and get things done for you, supporting call transcript viewing, call status checking, and real-time conversation streaming.

> **Skill Version**: `1.0.0` — All scripts and API requests carry a version number, and the server validates version consistency.

## 1. Account Registration

Visit the official website of Stepone AI to register a new account:
- **Website**: https://open-skill.steponeai.com
- **openclaw-friendly operation**
- **New User Benefit**: Get RMB 1 free credit upon registration
- **Professional communication with just one prompt**
- **Supports batch outbound calls**
- **Natural Chinese voice interaction**
- **Charged by call minute**

## 2. Obtain API Key

1. After logging in, visit: https://open-skill.steponeai.com/keys
2. Click "Create API Key"
3. Copy the generated Key (format: `sk_xxxxx`)

## 3. Configure Environment Variables

### Method 1: Environment Variables (Recommended)

```bash
export STEPONEAI_API_KEY="sk_xxxxxxxxxxxxx"
```

### Method 2: Secrets File

```bash
echo '{ "steponeai_api_key": "sk_xxxxxxxxxxxxx" }' > ~/.clawd/secrets.json
```

## 4. Usage Methods

### 4.1 Initiate Outbound Call

```bash
./callout.sh <phone_number> <call_requirement>
```

**Parameter Description:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| phone_number | Yes | Phone number, e.g., "13800138000" |
| call_requirement | Yes | Description of call content |

**Examples:**
```bash
./callout.sh "13800138000" "Notify you about tomorrow's 9 AM meeting"
./callout.sh "13800138000,13900139000" "Notify about annual meeting time change"
```

**Returns:** Contains `call_id` for subsequent call record queries and real-time conversation streaming

---

### 4.2 Query Call Records

```bash
./callinfo.sh <call_id> [options]
```

**Parameter Description:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| call_id | Yes | Call ID returned from outbound call |
| --json | No | Output raw JSON |

**Examples:**
```bash
./callinfo.sh "abc123xyz"
./callinfo.sh "abc123xyz" --json
```

**Features:**
- Automatic retry mechanism: Waits 10 seconds before retrying if no record found
- Maximum 5 retries (customizable)
- Returns call status, duration, content, and other information

---

### 4.3 Real-time Conversation Streaming (SSE)

Stream the real-time AI-user conversation during an active phone call.

```bash
./stream_chat.sh <call_id> [options]
```

**Parameter Description:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| call_id | Yes | Call ID returned from outbound call |
| --json | No | Output raw SSE data (no formatting) |

**Examples:**
```bash
# Start listening immediately after initiating a call
./callout.sh "13800138000" "Notify about tomorrow's meeting"
# Use the returned call_id
./stream_chat.sh "8bbbbbbb-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**SSE Data Format:**
| role | content | Description |
|------|---------|-------------|
| `assistant` | text | AI's response |
| `user` | text | User's speech-to-text |
| `system` | `[DONE]` | Call ended normally |
| `system` | `[TIMEOUT]` | Not answered within 30 seconds |

**Notes:**
- Can be called **immediately** after initiating a call (no need to wait for answer)
- Server sends heartbeat (`: keep-alive`) every 0.5s while waiting
- Timeout after 30 seconds if not answered (`[TIMEOUT]`)
- Stream closes with `[DONE]` when call ends

---

### 4.4 Low-level API Wrapper

```bash
./stepone.sh <command> [options]
```

| Command | Description |
|---------|-------------|
| `call '<json>'` | Make a call (raw JSON) |
| `callinfo <id>` | Query call records |
| `stream <id>` | Real-time conversation stream |
| `version` | Check skill version |
| `balance` | Check balance |

---

## 5. API Interface Description

All API requests require the following Headers:
```
X-API-Key: <API_KEY>
X-Skill-Version: 1.0.0
```

> If `X-Skill-Version` does not match the server version, the API will return HTTP 426 prompting an update.

### Initiate Outbound Call

- **URL**: `https://open-skill-api.steponeai.com/api/v1/callinfo/initiate_call`
- **Method**: POST
- **Body**:
```json
{
  "phones": "13800138000",
  "user_requirement": "Notification content"
}
```

### Query Call Records

- **URL**: `https://open-skill-api.steponeai.com/api/v1/callinfo/search_callinfo`
- **Method**: POST
- **Body**:
```json
{
  "call_id": "xxx"
}
```

### Real-time Conversation Streaming (SSE)

- **URL**: `https://open-skill-api.steponeai.com/api/v1/callinfo/stream_chat_history`
- **Method**: POST
- **Content-Type**: `application/json`
- **Response**: `text/event-stream` (Server-Sent Events)
- **Body**:
```json
{
  "call_id": "xxx"
}
```

**Response Stream Format:**
```text
: keep-alive
: keep-alive
data: {"role": "assistant", "content": "Hello, is this Mr. Zhang?"}

data: {"role": "user", "content": "Yes, it's me."}

data: {"role": "assistant", "content": "Mr. Zhang, I'm calling to let you know about tomorrow's 9 AM meeting."}

data: {"role": "system", "content": "[DONE]"}
```

### Check Version

- **URL**: `https://open-skill-api.steponeai.com/api/v1/callinfo/skill_version`
- **Method**: GET
- **Response**:
```json
{
  "skill_version": "1.0.0"
}
```

---

## 6. Version Control

All scripts and API requests pass the current Skill version via the `X-Skill-Version` Header.

- Server validates the version: returns HTTP 426 with an update prompt on mismatch
- Check version: `./stepone.sh version`
- Update: pull the latest code

---

## 7. Important Notes

### Identity Confirmation
- Must confirm the recipient's identity before initiating calls
- Address the recipient by name/title and wait for confirmation

### Phone Number Format
- Multiple phone numbers separated by English commas `,`
- Ensure correct phone number format (11 digits for Chinese mobile numbers)

### Call Record Query
- call_id is returned by the outbound call interface
- Call record generation has delays, requires patience
- Retry interval is fixed at 10 seconds

### Real-time Conversation
- Can call stream_chat.sh immediately after initiating a call
- Auto-timeout after 30 seconds if not answered
- Ideal for scenarios requiring real-time display of AI conversation

### user_requirement Suggestions
- Clear and specific descriptions
- Include specific time, location, person names, and other information
