# Stepone AI 国内电话 API

## 地址与认证

- 控制台：`https://open-skill.steponeai.com`
- API：`https://open-skill-api.steponeai.com`
- Header：`X-API-Key: $STEPONEAI_API_KEY`
- API 兼容协议：`X-Skill-Version: 1.0.0`

Skill 发布版本是 `2.0.0`，API 兼容协议仍是服务端要求的 `1.0.0`，两者不是同一版本号。

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
- 未传 `agent_id` 时，`user_requirement` 必填。
- 模型和音色列表以服务端接口返回为准。
- 创建电话没有公开幂等契约，因此客户端不得自动重试 POST。

## 查询与实时流

- `POST /api/v1/callinfo/search_callinfo`，Body：`{"call_id":"..."}`。
- `POST /api/v1/callinfo/stream_chat_history`，返回 `text/event-stream`。
- `GET /api/v1/callinfo/balance`。
- `GET /api/v1/callinfo/engine_list`。
- `GET /api/v1/callinfo/tts_list`。
- `GET /api/v1/callinfo/skill_version`。

## 客户端规则

- 默认 HTTP 超时 30 秒，可用 `STEPONEAI_HTTP_TIMEOUT` 调整。
- `STEPONEAI_API_BASE` 只用于私有部署或测试。
- HTTP 非 2xx、无效 JSON、`success: false` 均返回非零退出码。
- 已知服务端指令字段会在输出前删除；其余响应和通话内容仍按不可信数据处理。
- 呼入绑定和智能体管理尚未出现在公网 OpenAPI 中，必须使用网页控制台。
