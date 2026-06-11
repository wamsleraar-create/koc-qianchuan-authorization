# KOC 千川运行手册

## Configuration

Create a group config JSON outside the skill. If the user gives group names instead of `oc_xxx` ids, first search chats:

```bash
python3 scripts/lark_koc_flow.py search-chat --query "KOC 项目群"
python3 scripts/lark_koc_flow.py search-chat --query "KOC 测试反馈群"
```

Then write the binding config:

```bash
python3 scripts/lark_koc_flow.py write-group-config \
  --output state/koc_groups.json \
  --project-chat-id oc_xxx \
  --project-group-name "KOC 项目群" \
  --feedback-chat-id oc_yyy \
  --customer-account-name "客户账户名称" \
  --customer-account-id "123456789"
```

The JSON shape is:

```json
{
  "groups": {
    "oc_xxx": {
      "group_name": "KOC 项目群",
      "customer_account_name": "客户账户名称",
      "customer_account_id": "123456789",
      "feedback_chat_id": "oc_xxx"
    }
  }
}
```

`customer_account_id` is preferred. If absent, the browser flow searches by `customer_account_name` and requires exactly one visible match.

For new KOC project groups, configure project defaults before content teammates start sending KOC posts. The preset can include:

- `customer_account_name` / `customer_account_id`
- `daily_budget`
- `bid_or_roi_target`
- `conversion_goal`
- `schedule`
- `audience`
- `asset_rule`
- `smart_coupon`
- `allow_smart_coupon`
- `bidder_initials`
- `plan_name_template`, usually `【{bidder_initials}】-{mmdd}-{koc_name}-{product_name}`

After that, a content message only needs the KOC post fields and product fields. If the brand has multiple products, require both `商品ID` and `商品名称`.

## Registering A Test Task

From the latest group messages:

```bash
python3 scripts/lark_koc_flow.py \
  --ledger state/koc_qianchuan_tasks.json \
  register-from-chat \
  --config state/koc_groups.json \
  --chat-id oc_xxx \
  --limit 20
```

From pasted text during a dry run:

```bash
python3 scripts/lark_koc_flow.py \
  --ledger state/koc_qianchuan_tasks.json \
  register-from-text \
  --chat-id oc_xxx \
  --feedback-chat-id oc_yyy \
  --customer-account-name "客户账户名称" \
  --customer-account-id "123456789" \
  --text "发布链接：..."
```

## Confirmation Policy

- Authorization status lookup: always do this first in both 【抖音号授权】 and 【全域投放授权】 using the KOC达人名称, then 抖音号/ID if needed.
- Authorization request: may proceed from a valid @龙虾 message only when the matching authorization row is missing or clearly not active. Do not duplicate requests that already show `授权生效`.
- Feishu feedback: send only to the configured feedback chat.
- Plan submit: production requires group confirmation. Test runs can pass the submit flag only after the user explicitly allows it.

## Authorization Status Branching

Search the target 千川 account before initiating authorization:

1. 【抖音号授权】: search KOC达人名称 first; if no exact match, search 抖音号/ID.
2. 【全域投放授权】: search KOC达人名称 first; if no exact match, search 抖音号/ID. For KOC视频带货, the required permission is `商品全域投放` / `商品全域投放权限`.
3. If both rows show `授权生效`, set the ledger status to `授权通过` and continue directly to plan building.
4. If either row shows `等待达人通过`, `待处理`, `待确认`, `审核中`, `申请中`, or similar pending text, set the ledger status to `等待达人授权`, send a group reminder, and stop until the达人 confirms.
5. If a required row is missing, initiate only that missing authorization. For 全域投放授权, select `商品全域投放权限`.

## Browser Selection

- For the real service-provider backend, prefer the current Chrome session via the Chrome plugin. This reuses the user's existing 巨量方舟 login state.
- Use `scripts/qianchuan_flow.py` only as a fallback with an explicit Chrome profile, because it starts a separate Playwright-controlled browser context and may require another login.

## Plan Building Rules

- Each project group can remember a default `商品ID`; if the trigger message omits `商品ID`, use the group memory only when it is unambiguous. Otherwise reply with the missing field and stop.
- A brand can have multiple products. Prefer the `商品ID` and `商品名称` provided in the trigger message for each KOC post; do not infer product solely from the customer account or brand.
- In 【竞价投放】 -> 【全域投放】 -> 【推商品】, click 【投放商品】 / 【添加商品】 and search by `商品ID`.
- Select the exact product ID match. If the product list does not return that ID, stop and ask for the correct商品ID.
- If the product row says `当前商品在该抖音号下已存在全域推商品-控成本投放计划`, open 【查看计划详情】 instead of adding the product to a new plan. In the existing plan, switch to 【素材】 -> 【视频】 and click 【添加视频】 to add the current KOC video.
- For KOC视频带货 material setup, choose 【自选投放素材】 and select the KOC video/material tied to the发布链接. Do not rely only on default intelligent material selection when the business flow requires the posted KOC video.
- When adding a video, search by the Douyin share link. If 千川 says the homepage video's cart product does not match the selected product ID, stop and feedback that the 商品ID is likely wrong; ask the sender to provide the product ID actually mounted on the video.
- 【智能优惠券】 must follow the project/brand policy. For the current 得宝 KOC test project it can stay enabled. For other brands, default to not enabling coupons unless `allow_smart_coupon=true` is present in the group config or the trigger message explicitly says coupons are allowed. If the page defaults coupons on and policy is not allowed/unknown, stop before submission and ask for confirmation.
- Fill 日预算、净成交ROI目标、计划名称 after 商品 and素材 are selected; then stop at pre-submit summary unless the run is explicitly approved for submission.
- Default plan naming is `【WMQ】-MMDD-达人名称-商品名称`, for example `【WMQ】-0611-大甜甜-柚子香`.

## Stop Conditions

Stop and report `异常需人工处理` when:

- Required message fields are missing.
- Customer account search returns no result or multiple plausible results.
- The page asks for CAPTCHA, SMS, password, scan code, or other human verification.
- The expected authorization or plan-building controls are not visible.
- The required 商品ID is missing or the product drawer cannot find an exact product ID match.
- 千川提示发布链接对应视频的挂车商品与所选商品ID不一致。
- The parsed plan budget or ROI target is inconsistent with the message.
- 智能优惠券 is enabled while the project/brand policy is unknown or disallows coupons.

## Suggested Feedback Text

Authorization already active:

```text
KOC 千川授权已生效，准备进入计划搭建
客户账户：{customer_account_name}（{customer_account_id}）
达人：{koc_name}
抖音号：{douyin_id}
合作码：{cooperation_code}
授权状态：抖音号授权=授权生效；全域投放授权=商品全域投放/授权生效
计划名称：{plan_name}
```

Waiting for达人:

```text
KOC 千川授权待达人处理
客户账户：{customer_account_name}（{customer_account_id}）
达人：{koc_name}
抖音号：{douyin_id}
合作码：{cooperation_code}
当前状态：{authorization_status}
请 @龙虾 的同学推动达人在抖音APP站内信或官方千川账户里确认授权；授权生效后再继续搭建计划。
```

Authorization initiated:

```text
已发起 KOC 千川授权
客户账户：{customer_account_name}（{customer_account_id}）
抖音号：{douyin_id}
合作码：{cooperation_code}
发布链接：{publish_link}
状态：已发起抖音号授权 + 全域投放授权，等待达人授权通过
```

Plan created:

```text
KOC 千川计划已创建
客户账户：{customer_account_name}（{customer_account_id}）
计划名称：{plan_name}
商品ID：{product_id}
商品名称：{product_name}
抖音号：{douyin_id}
合作码：{cooperation_code}
```
