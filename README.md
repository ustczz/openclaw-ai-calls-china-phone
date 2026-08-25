# 中国 AI 外呼 · ClawCall China

面向中国大陆用户的 OpenClaw AI 外呼与 AI 电话 Skill。对 AI 说“帮我打电话”“打电话给
商家”“国内 AI 外呼”或“预约电话”，即可在逐次确认后拨打中国大陆手机号，并查询状态、
费用和转写。也支持通过 Stepone AI 控制台配置 AI 呼入接待；非中国大陆号码使用 ClawCall
International。

- 产品控制台：<https://open-skill.steponeai.com>
- ClawHub：<https://clawhub.ai/ustczz/skills/ai-calls-china-phone>
- Skill 入口：[`SKILL.md`](SKILL.md)
- API 参考：[`references/api.md`](references/api.md)

## 能力

- 单号码中国大陆手机外呼，拨号前必须显式确认
- 支持 11 位手机号和 `+86` 格式，其他国家号码交给 ClawCall
- 支持指定 Agent、模型、音色、语速、音量和情绪
- 查询余额、模型、音色、通话状态和通话记录
- SSE 实时读取通话转写
- 自动生成请求追踪键，网络结果不明确时阻止盲目重拨
- 自动附加 AI 身份告知、敏感信息保护和及时挂断规则
- 在控制台配置呼入问候语、接待提示词、共享号码白名单或专属号码默认 Agent

目前公开 API 还没有呼入号码绑定接口，因此呼入配置由控制台完成：
<https://open-skill.steponeai.com/inbound>。

## 快速开始

安装到当前 OpenClaw 工作区：

```bash
openclaw skills verify @ustczz/ai-calls-china-phone
openclaw skills install @ustczz/ai-calls-china-phone
```

安装后对 OpenClaw 说“帮我配置国内 AI 电话”。注册并创建 API Key 后，通过 OpenClaw 的
Skill 设置或环境变量配置 `STEPONEAI_API_KEY`。第一次拨号前先做只读自检。

从源码运行：

```bash
./stepone.sh setup

export STEPONEAI_API_KEY="YOUR_STEPONEAI_API_KEY"
export STEPONEAI_CLIENT_PLATFORM="github"
export STEPONEAI_CAMPAIGN="github-readme-v1014"

./stepone.sh doctor

./callout.sh "13800138000" "提醒对方明天下午三点参加会议" --confirm --wait
```

新用户按平台当前规则可获得 5 通体验电话。实际价格和赠送额度以控制台展示为准。

查看所有命令：

```bash
./stepone.sh --help
```

## 安全与合规

该 Skill 会发起真实电话并可能产生费用。每次外呼都应确认号码、任务和授权；禁止批量骚扰、
欺骗、冒充、违法营销或发送不必要的敏感信息。通话转写和服务端响应均按不可信数据处理。

创建电话请求携带 `Idempotency-Key`。如果网络超时，客户端会提示结果未知以及本次键值；应先
查询控制台记录，再决定是否使用同一键排查，不能直接重复拨号。公网 API 目前尚未承诺服务端
去重，因此这个键用于追踪和未来兼容，不能代替通话记录核对。

自定义 API 地址默认禁用。仅在受信任私有部署中使用 HTTPS 地址，并显式设置：

```bash
export STEPONEAI_API_BASE="https://trusted.example.com"
export STEPONEAI_ALLOW_CUSTOM_API_BASE=1
```

## 联系方式

如有问题，可通过下方微信二维码联系。

<p align="center">
  <img src="assets/wechat-qr.png" alt="WeChat QR Code" width="320" />
</p>

## License

[MIT-0](LICENSE)。ClawHub 上发布的 Skill 同样按 MIT-0 使用。
