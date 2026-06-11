---
name: koc-qianchuan-authorization
description: Handle KOC 巨量千川 authorization and plan-building workflows for a Feishu project group assistant such as “部门龙虾”. Use when a user needs to process KOC group messages containing 发布链接、抖音号、合作码 and plan parameters, search/select a bound 巨量方舟/巨量千川 customer account, initiate 抖音号授权 and 全域投放授权, send Feishu group feedback, check authorization status, or build a semi-automatic 千川 test/production plan.
---

# KOC 千川授权

## Workflow

Use this skill for the semi-automatic “部门龙虾” flow in KOC project groups.

1. Read the latest group message that mentions 龙虾 or contains the fixed KOC fields.
2. Parse and validate the message with `scripts/parse_koc_message.py`.
3. Resolve the bound customer account from a group config JSON. Prefer `customer_account_id`; use account name only when the ID is missing.
   - For a new KOC project group, create a group preset before processing posts. Presets can include customer account, budget, ROI, conversion goal, schedule, audience, asset rule, smart coupon policy, bidder initials, and plan name template.
   - After a group preset exists, content teammates may send a shorter KOC post message. Missing plan fields are filled from the group preset; 商品ID and 商品名称 should still be supplied when the brand has multiple products.
4. Open 巨量方舟 / 巨量千川 from `https://agent.oceanengine.com/admin/optimizeModule/qianchuan/promotion/domain/roi2-adv` with the user's current Chrome login state. First-time login for a project must be completed by the responsible 追投 PM; the skill only reuses an already-authenticated browser session. Prefer the Chrome plugin for live backend operations. Use `scripts/qianchuan_flow.py` only as a Playwright fallback when a separate browser profile is acceptable.
5. Before initiating any new authorization, search the target 千川 account's 【抖音号授权】 and 【全域投放授权】 lists by KOC达人名称 first; if needed also search by 抖音号/ID. Prefer exact matches on达人名称 + 抖音号.
6. Read the visible authorization status for both rows:
   - If 【抖音号授权】 and 【全域投放授权】 both show `授权生效`, record `授权通过` and go directly to plan building.
   - If either row shows waiting/pending text such as `等待达人通过`, `待处理`, `待确认`, `审核中`, or `申请中`, record `等待达人授权` and send group feedback reminding the colleague who @龙虾 to push the达人完成授权确认.
   - If either authorization row is missing, initiate only the missing authorization. Do not duplicate an authorization that already shows `授权生效`.
7. For KOC视频带货, 全域投放授权 must use `商品全域投放权限` / `全域投放-商品投放`, not直播权限.
8. Send group feedback after status is known: authorized and entering plan, waiting for达人, newly initiated, or abnormal.
9. In the plan builder, click 【投放商品】 / 【添加商品】 and search/select by `商品ID` before filling budget/ROI. A brand can have multiple products, so do not infer the product from the brand/account alone.
10. If 千川 says `当前商品在该抖音号下已存在全域推商品-控成本投放计划`, do not create a duplicate plan. Open 【查看计划详情】, switch to 【素材】, and use 【添加视频】 to append the new KOC video as 自选投放素材 to the existing plan.
11. For KOC video-commerce plans, use 【自选投放素材】 when material selection is required; do not rely only on default intelligent material selection if the workflow asks for the KOC video asset. Search by the Douyin share link. If 千川 reports that the homepage video's cart product does not match the selected product ID, stop and feedback that the 商品ID is likely wrong.
12. Treat 【智能优惠券】 as a project/brand policy setting. It is allowed for the current 得宝 KOC test project, but other brands must not have coupons enabled unless the group config or message explicitly allows it. If 千川 defaults coupons on and the project policy is unknown or disallows coupons, stop before submission and feedback for confirmation.
13. Plan name convention comes from the project/group preset. A common template is `【{bidder_initials}】-{mmdd}-{koc_name}-{product_name}`. `WMQ` is only a test/project example, not a fixed default.
14. Before final plan submission, summarize account, 抖音号, 合作码, 商品ID, 商品名称, 发布链接, budget, bid/ROI, conversion goal, schedule, audience, asset rule, coupon policy, and plan name. In production, wait for group confirmation; in an explicitly approved test run, pass the submit flag.

## Message Contract

Required group message fields:

```text
发布链接：
抖音号：
合作码：
商品ID：
商品名称：
日预算：
出价/ROI目标：
转化目标：
投放时段：
定向/人群：
素材规则：
智能优惠券：
计划命名：
```

The parser also accepts common aliases such as `发布地址`, `视频链接`, `ROI目标`, `人群`, `智能优惠券启用状态`, and `计划名称`.

For groups with a preset, the content message can be reduced to:

```text
发布链接：
达人名称：
合作码：
抖音号：
账号UID：
商品ID：
商品名称：
```

The preset supplies customer account, budget, ROI, conversion goal, schedule, audience, material rule, smart coupon policy, and default plan name template.

Use `references/message-format.md` when preparing examples or debugging parsing.

## Scripts

- `scripts/parse_koc_message.py`: Parse one Feishu message into normalized JSON and report missing fields.
- `scripts/lark_koc_flow.py`: Parse pasted messages or search/list group messages, maintain a local status ledger, and optionally send Feishu replies through `lark-cli`.
- `scripts/qianchuan_flow.py`: Playwright fallback helper for the 千川 authorization and plan-building steps. It is intentionally conservative and stops at ambiguity; it does not attach to an already-open Chrome tab.
- `scripts/smoke_test.py`: Offline verification for parsing, group config creation, task registration, and feedback dry-run.

Use the scripts from this skill directory. Example:

```bash
python3 scripts/parse_koc_message.py --text "发布链接：https://... 抖音号：123 合作码：ABC 日预算：300 出价/ROI目标：1.2 转化目标：下单 投放时段：全天 定向/人群：不限 素材规则：使用发布链接视频 计划命名：KOC测试-123"
```

For real tests that must reuse the user's active Chrome session, read `references/current-chrome-flow.md` and use the Chrome plugin/browser control path instead of launching a separate Playwright profile.

Use `references/test-intake-template.md` when asking the user for the minimum real test inputs.

## State Model

Record each KOC task in the ledger with one of these statuses:

- `待授权`
- `已发起抖音号授权`
- `已发起全域投放授权`
- `等待达人授权`
- `授权通过`
- `计划已创建`
- `异常需人工处理`

Use `references/runbook.md` for operator rules, confirmation points, and known stop conditions.

## Safety Rules

- Never choose among multiple customer accounts silently.
- Never submit a plan unless the user has explicitly approved submission for that run or a group confirmation has been captured.
- Never send feedback to a real business group during testing unless the target chat is explicitly configured.
- Treat CAPTCHA, SMS, password, and扫码 steps as user-handled.
- First-time 巨量方舟/千川 login must be performed by the responsible project 追投 PM. Do not bypass login security; resume only after the browser is already inside 千川.
- If the backend UI wording differs from the expected labels, pause and report the visible alternatives instead of guessing.
