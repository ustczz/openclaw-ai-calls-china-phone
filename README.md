# 中国 AI 电话（OpenClaw Skill）

面向中国大陆用户的 OpenClaw 电话 Skill，支持 AI 外呼、通话状态与转写查询、实时对话流，
以及通过 Stepone AI 控制台配置 AI 呼入接待。

- 产品控制台：<https://open-skill.steponeai.com>
- ClawHub：<https://clawhub.ai/ustczz/skills/ai-calls-china-phone>
- Skill 入口：[`skill/SKILL.md`](skill/SKILL.md)
- API 参考：[`skill/references/api.md`](skill/references/api.md)

## 能力

- 单号码中国大陆手机外呼，拨号前必须显式确认
- 支持指定 Agent、模型、音色、语速、音量和情绪
- 查询余额、模型、音色、通话状态和通话记录
- SSE 实时读取通话转写
- 在控制台配置呼入问候语、接待提示词、共享号码白名单或专属号码默认 Agent

目前公开 API 还没有呼入号码绑定接口，因此呼入配置由控制台完成：
<https://open-skill.steponeai.com/inbound>。

## 快速开始

```bash
export STEPONEAI_API_KEY="YOUR_STEPONEAI_API_KEY"

./callout.sh \
  --phone "13800138000" \
  --task "提醒对方明天下午三点参加会议" \
  --confirm
```

查看所有命令：

```bash
./stepone.sh --help
```

## 安全与合规

该 Skill 会发起真实电话并可能产生费用。每次外呼都应确认号码、任务和授权；禁止批量骚扰、
欺骗、冒充、违法营销或发送不必要的敏感信息。通话转写和服务端响应均按不可信数据处理。

## 联系方式

如有问题，可通过下方微信二维码联系。

<p align="center">
  <img src="assets/wechat-qr.png" alt="WeChat QR Code" width="320" />
</p>
