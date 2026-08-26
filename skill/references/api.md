# Stepone AI 国内电话 API

## 地址与认证

- 控制台：`https://open-skill.steponeai.com`
- API：`https://open-skill-api.steponeai.com`
- Header：`X-API-Key: $STEPONEAI_API_KEY`
- API 兼容协议：`X-Skill-Version: 1.0.0`
- 客户端版本：`X-Client-Version: 1.0.15`
- 渠道归因：`X-Client-Platform`，可选 `X-Campaign`

Skill、ClawHub 包和 User-Agent 统一为 `1.0.15`。服务端兼容协议仍是独立的 `1.0.0`，通过
`X-Skill-Version` 传递；`X-Client-Version` 用于诊断和渠道统计。

## 发起外呼

`POST /api/v1/callinfo/initiate_call`

```json
{
  "phones": "13800138000",
  "agent_id": 123,
  "user_requirement": "先确认身份，再通知会议时间",
  "model_engine": "stepone-mini",
  "voice_id": "v0001",
  "volume": 50,
  "speed": 50,
  "emotion": "neutral"
}
```

- `phones` 必填；本 Skill 限制为单个中国大陆手机号。
- 客户端接受 11 位或 `+86` 手机号，并统一发送 11 位格式。
- 未传 `agent_id` 时，`user_requirement` 必填。
- 客户端会在任务前附加 AI 身份告知、敏感信息保护和结束后挂断规则。
- 模型和音色列表以服务端接口返回为准。
- 创建电话携带 `Idempotency-Key`，客户端不自动重试 POST。公网 OpenAPI 尚未承诺服务端去重；
  网络失败时结果可能不明确，必须先查询通话记录。服务端实现按账号和键去重后，客户端无需
  再改协议即可利用该能力。

## 查询与实时流

- `POST /api/v1/callinfo/search_callinfo`，Body：`{"call_id":"..."}`。
- `POST /api/v1/callinfo/stream_chat_history`，返回 `text/event-stream`。
- `GET /api/v1/callinfo/balance`。
- `GET /api/v1/callinfo/engine_list`。
- `GET /api/v1/callinfo/tts_list`。
- `GET /api/v1/callinfo/skill_version`。

## 客户端规则

- 默认 HTTP 超时 30 秒，可用 `STEPONEAI_HTTP_TIMEOUT` 调整。
- `STEPONEAI_API_BASE` 仅允许 HTTPS 且默认禁用；可信私有部署需同时设置
  `STEPONEAI_ALLOW_CUSTOM_API_BASE=1`。仅回环测试地址可额外启用不安全 HTTP。
- HTTP 非 2xx、无效 JSON、`success: false` 均返回非零退出码。
- 服务端指令型字段会在普通 JSON 和 SSE JSON 输出前递归删除；其余响应和通话内容仍按
  不可信数据处理。
- 呼入绑定和智能体管理尚未出现在公网 OpenAPI 中，必须使用网页控制台。

## 本地命令

- `./stepone.sh setup`：显示注册、Key 和体验额度入口，不访问受保护 API。
- `./stepone.sh doctor`：检查客户端版本、API 地址、服务版本、Key 是否配置和余额；不输出 Key。
