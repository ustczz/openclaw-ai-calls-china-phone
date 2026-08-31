# ClawCall：AI 外呼、智能外呼与电话机器人

<!-- markdownlint-disable MD013 MD033 -->

对 OpenClaw 说一句话，让 AI 帮你拨打真实电话、完成沟通任务并返回通话结果。支持中文
AI 外呼、机器人外呼、智能外呼、电话回访，以及通过网页控制台配置 AI 呼入接待。

[立即安装](https://clawhub.ai/ustczz/skills/ai-calls-china-phone) ·
[注册并创建 API Key](https://open-skill.steponeai.com/keys?utm_source=github&utm_medium=repository&utm_campaign=clawcall-china-v1014&utm_content=readme-primary) ·
[配置呼入接待](https://open-skill.steponeai.com/inbound?utm_source=github&utm_medium=repository&utm_campaign=clawcall-china-v1014&utm_content=readme-inbound) ·
[完整实测教程](docs/openclaw-ai-outbound-guide.md) ·
[安装问题反馈](https://github.com/ustczz/openclaw-ai-calls-china-phone/issues/5)

> “帮我打电话给餐厅，预订今晚 7 点两个人的位置。”
>
> “给客户做一次售后回访，询问设备是否恢复正常。”
>
> “打电话催一下快递，确认今天能不能送到。”
>
> “配置一个电话机器人，接听客户来电并记录姓名和需求。”

## 安装

在 OpenClaw 工作区执行：

```bash
openclaw skills verify @ustczz/ai-calls-china-phone
openclaw skills install @ustczz/ai-calls-china-phone
```

安装后告诉 OpenClaw：

```text
帮我配置 AI 外呼
```

OpenClaw 会引导你注册 ClawCall、创建 API Key，并完成只读自检。注册后的体验额度和实际价格
以[控制台](https://open-skill.steponeai.com/?utm_source=github&utm_medium=repository&utm_campaign=clawcall-china-v1014&utm_content=readme-install)实时展示为准。

## 能做什么

- AI 外呼：订位、预约、通知、催办、询价、售后回访和客户确认
- 电话机器人：按目标自主交流，处理打断并返回通话结果
- AI 呼入：配置欢迎语、接待提示词、共享呼入号码或独立呼入号码
- 通话记录：查询状态、费用、转写和实时对话
- 声音配置：选择模型、音色、语速、音量和情绪
- 智能体管理：通过网页或 CLI 创建智能体、查看 ID，并按 ID 发起呼入/外呼
- 安全控制：每次只拨一个号码，必须逐次确认后才会真实呼叫

本 Skill 处理中国大陆手机号码，支持 11 位和 `+86` 格式。国际号码请使用
[ClawCall International](https://clawhub.ai/ustczz/skills/clawcall-ai-phone-calls)。

## 完整实测教程

[《OpenClaw AI 外呼实测：一句话让 AI 真正打电话》](docs/openclaw-ai-outbound-guide.md)
覆盖安装、API Key、`doctor`、逐次确认、状态与转写查询、AI 呼入接待和常见失败原因。

## 从源码运行

```bash
./stepone.sh setup

export STEPONEAI_API_KEY="YOUR_STEPONEAI_API_KEY"
export STEPONEAI_CLIENT_PLATFORM="github"
export STEPONEAI_CAMPAIGN="github-readme-v1014"

./stepone.sh doctor
./callout.sh "13800138000" "提醒对方明天下午三点参加会议" --confirm --wait
```

常用命令：

```bash
./stepone.sh balance
./stepone.sh engines
./stepone.sh voices
./stepone.sh agents
./stepone.sh agent-create \
  --name "会议提醒" \
  --prompt-file ./agent-prompt.txt \
  --greeting "您好，我是 AI 助手。"
./callout.sh "13800138000" --agent-id 123 --confirm
./callinfo.sh CALL_ID
./stream_chat.sh CALL_ID
./stepone.sh --help
```

完整能力说明见 [`SKILL.md`](SKILL.md)，接口约定见
[`references/api.md`](references/api.md)。

## 呼入接待

呼入号码当前通过网页控制台配置；智能体也可以使用 `stepone.sh agent-create` 创建：

1. 在[智能体](https://open-skill.steponeai.com/agents?utm_source=github&utm_medium=repository&utm_campaign=clawcall-china-v1014&utm_content=readme-agents)页面设置身份、开场白、业务范围、模型和音色。
2. 在[呼入设置](https://open-skill.steponeai.com/inbound?utm_source=github&utm_medium=repository&utm_campaign=clawcall-china-v1014&utm_content=readme-inbound-setup)页面绑定共享号码白名单，或为独立号码选择默认智能体。
3. 使用已授权的号码拨入，检查身份告知、打断、转写和通话记录。

目前公开 API 不提供呼入号码绑定接口，Skill 不会猜测或绕过控制台配置。网页智能体卡片会展示
可复制的智能体 ID，`stepone.sh agents` 也会返回同一 ID。

## 安全与合规

该 Skill 会发起真实电话并可能产生费用。每次外呼前都必须确认完整号码、通话目的和用户授权；
禁止批量骚扰、欺骗、冒充、违法营销、拨打紧急服务，或在任务中发送不必要的敏感信息。

客户端强制执行单号码与 `--confirm` 门禁，API Key 仅从环境变量读取。电话转写和服务端响应
均按不可信数据处理。请求会附带 `Idempotency-Key` 便于追踪；网络结果不明确时应先查询通话
记录，不能直接重复拨号。

自定义 API 地址默认禁用。仅在受信任私有部署中使用 HTTPS 地址，并显式设置：

```bash
export STEPONEAI_API_BASE="https://trusted.example.com"
export STEPONEAI_ALLOW_CUSTOM_API_BASE=1
```

## 联系我们

安装、接入或商务合作问题，可通过下方微信二维码联系。

安装、自检或首次接通问题也可以在[公开反馈帖](https://github.com/ustczz/openclaw-ai-calls-china-phone/issues/5)
提交脱敏信息。

<p align="center">
  <img src="assets/wechat-qr.png" alt="ClawCall 微信联系二维码" width="280" />
</p>

## License

[MIT-0](LICENSE)。ClawHub 上发布的 Skill 同样按 MIT-0 使用。
