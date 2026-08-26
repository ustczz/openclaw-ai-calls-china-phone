# OpenClaw AI 外呼实测：一句话让 AI 真正打电话

<!-- markdownlint-disable MD013 -->

> Meta description：OpenClaw AI 外呼不只是生成话术。本文演示如何安装 ClawCall，让 AI 在逐次确认后拨打国内手机号，并查询状态、转写、费用及配置 AI 呼入接待。

很多人说的“AI 外呼”，实际只是让大模型写一段电话话术。真正的 OpenClaw AI 外呼应该完成
四件事：理解任务、拨出真实电话、与对方交流、把结果带回来。ClawCall 把这套能力封装成了一个
OpenClaw Skill，用户可以直接说“帮我给餐厅打电话”或“电话问一下商家什么时候发货”。

这篇文章面向已经部署 OpenClaw、希望让 Agent 处理真实中文电话任务的个人和团队。你会看到
完整安装流程、一次外呼的确认机制、呼入接待配置方式，以及哪些场景不应该使用它。

## 先看结论

- Skill 当前版本为 `1.0.14`，可拨打 11 位或 `+86` 中国大陆手机号。
- 每次只能拨打 1 个号码；没有当次明确确认，客户端不会真实外呼。
- 通话后可以查询状态、费用、转写，并监听实时对话。
- 网页控制台已经支持 AI 呼入接待，可配置共享号码或独立号码。
- 新用户当前有 5 通体验额度，实际额度和价格以控制台实时显示为准。

项目已在 [ClawHub](https://clawhub.ai/ustczz/skills/ai-calls-china-phone) 上架，源码和安全边界在
[GitHub](https://github.com/ustczz/openclaw-ai-calls-china-phone) 公开。[OpenClaw 官方文档](https://docs.openclaw.ai/tools/skills)
说明，Skill 是 AgentSkills 兼容的能力目录，可通过 `openclaw skills install` 安装到工作区。

## 为什么不直接使用普通语音通话插件

OpenClaw 自带的语音通话插件更适合已经准备好 Twilio、Telnyx 等运营商账号，并愿意自己配置
号码、Webhook 和线路的开发者。ClawCall 解决的是另一类问题：用户希望 Agent 直接处理中国
大陆真实电话任务，而不先搭建一套电话基础设施。

它不是批量营销系统，也不以“无限群呼”为目标。一个请求只对应一个号码，适合订位、预约、
商家咨询、通知和已经获得授权的客户回访。

## 第一步：安装 Skill

在 OpenClaw 工作区执行：

```bash
openclaw skills verify @ustczz/ai-calls-china-phone
openclaw skills install @ustczz/ai-calls-china-phone
```

安装后可以直接告诉 OpenClaw：

```text
帮我配置 AI 外呼
```

OpenClaw 会引导你打开 ClawCall 控制台、创建 API Key，并完成只读自检。API Key 只应放在环境
变量中，不要粘贴到聊天消息、SKILL.md 或 Git 仓库。

```bash
export STEPONEAI_API_KEY="YOUR_STEPONEAI_API_KEY"
export STEPONEAI_CLIENT_PLATFORM="clawhub"
./stepone.sh doctor
```

`doctor` 用于检查 Key、余额、模型和音色是否可用，不会拨打电话。先完成自检，再处理真实任务，
可以把“配置错误”与“电话未接通”区分开。

## 第二步：把任务说清楚

一个有效的电话任务至少包含身份、目标、必要背景、边界和成功条件。例如：

```text
帮我给餐厅打电话，询问今晚 7 点是否有 4 人桌。接通后说明你是受我委托的 AI 助手；没有位置
就询问 7:30，不要支付订金。拨号前先展示号码、任务和可能费用，等我确认。
```

不要只写“你看着办”。Agent 需要知道哪些信息可以说、哪些承诺不能做、拿到什么结果后应该结束。
密码、验证码、支付卡号和不必要的个人信息都不应放进电话任务。

## 第三步：确认后才拨号

ClawCall 会先向用户展示完整号码、通话目的和可能产生的费用。只有用户对这一次电话明确确认后，
客户端才允许加入 `--confirm`：

```bash
./callout.sh \
  "13800138000" \
  "提醒对方明天下午三点参加会议；先确认身份，再说明事项" \
  --confirm \
  --wait
```

客户端接受 11 位手机号和 `+86` 格式，并在发送前统一规范化。`--wait` 最长等待 10 分钟，适合
在同一轮任务中拿到最终状态。网络结果不明确时不能盲目重拨，应先查询控制台或通话记录，避免
同一个人收到两通重复电话。

## 第四步：查询电话结果

发起成功后会返回 `call_id`。可以查询最终状态、实时转写、费用和余额：

```bash
./callinfo.sh CALL_ID
./stream_chat.sh CALL_ID
./stepone.sh balance
```

实时流中的 `assistant` 代表 AI 发言，`user` 代表电话对方发言。电话未接通、占线或被拒接并不
等于 Skill 没有运行；是否拨出、是否接通、是否完成应分别记录。当前 [v1.0.14 Release](https://github.com/ustczz/openclaw-ai-calls-china-phone/releases/tag/v1.0.14)
通过了 17 项单元测试、Ruff 和 Bandit 检查，并完成了授权号码的真实电话验收。

## 新功能：让 AI 接听来电

外呼解决“Agent 主动联系别人”，呼入接待解决“客户主动打进来”。配置分两步：

1. 在[智能体页面](https://open-skill.steponeai.com/agents)设置身份、开场白、业务范围、模型和音色。
2. 在[呼入设置](https://open-skill.steponeai.com/inbound)绑定共享号码白名单，或为独立号码选择默认智能体。

共享呼入只接收与白名单主叫完全匹配的电话，适合测试和固定客户；独立号码适合正式接待。提示词
应明确可回答范围、需要收集的信息、禁止承诺事项、人工升级方式和结束语。

## 哪些场景适合，哪些不适合

适合：

- 询问餐厅、门店或机构的公开信息
- 预约、订位、催办和订单状态确认
- 向已经同意联系的用户发送一次明确通知
- 对已授权客户进行售后回访
- 配置 AI 前台，接听客户来电并记录需求

不适合：

- 未经同意的批量营销和陌生私人的冷呼
- 冒充真人、企业、政府或金融机构
- 索取验证码、密码、支付信息或过度个人信息
- 拨打紧急服务、短号码或规避对方拒绝

[《消费者权益保护法实施条例》第二十四条](https://www.gov.cn/zhengce/content/202403/content_6940158.htm)
明确要求，未经消费者同意不得拨打商业性电话；同意后也必须提供明确、便捷的取消方式。真实电话
能力越强，确认、身份告知和拒绝机制越不能省略。

## 常见问题

### ClawCall 是只能写电话话术吗

不是。它会在确认后调用真实电话服务，并返回 `call_id`、状态、转写和费用等结果。

### 可以一次拨打很多号码吗

这个 Skill 不允许。客户端强制一次只处理一个号码，定位是 Agent 完成具体电话任务，不是批量
营销平台。

### 支持海外号码吗

国内入口只处理中国大陆手机号。国际 E.164 号码使用独立的
[ClawCall International](https://clawhub.ai/ustczz/skills/clawcall-ai-phone-calls)，两套 Skill
不会混用脚本和后端。

### 为什么要先运行 doctor

`doctor` 是只读检查，可以提前发现 Key、余额、模型或音色问题，避免把配置失败误判成线路问题。

### 电话一定能接通吗

不能保证。无人接听、关机、欠费、占线、运营商限制和对方拒接都会影响结果。正确的增长指标应
同时观察发起、接通、完成和二次使用，而不是只看 Skill downloads。

## 开始第一通电话

先从一个自己控制或已经获得授权的测试号码开始，任务保持简单，确认 AI 身份告知、状态、转写
和费用都能查询后，再用于真实业务。

[打开 ClawCall 控制台](https://open-skill.steponeai.com/?utm_source=github&utm_medium=repository&utm_campaign=clawcall-china-v1014&utm_content=guide-primary) ·
[查看并安装 Skill](https://clawhub.ai/ustczz/skills/ai-calls-china-phone) ·
[阅读源码](https://github.com/ustczz/openclaw-ai-calls-china-phone)

## 发布素材清单

发布前在文中加入三张真实、脱敏截图：

1. `doctor` 自检成功截图，不显示 API Key。
2. 拨号前确认截图，只显示 `186****8262` 形式的号码。
3. 通话状态和转写截图，隐藏姓名、完整任务和无关通话记录。
