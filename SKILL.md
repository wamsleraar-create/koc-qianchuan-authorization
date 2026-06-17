---
name: koc-qianchuan-authorization-20260616
description: 2026-06-16 version. Handle KOC 巨量千川 authorization and plan-building workflows for a Feishu project group assistant such as “部门龙虾”. Use when a user needs to process KOC group messages containing 发布链接、抖音号、合作码 and plan parameters, search/select a bound 巨量方舟/巨量千川 customer account, identify existing plans/materials, initiate 抖音号授权 and 全域投放授权 when needed, send Feishu group feedback, check authorization status, or build a semi-automatic 千川 test/production plan.
---

# KOC 千川授权建计划 - 20260616

## Workflow

Use this skill for the semi-automatic “部门龙虾” flow in KOC project groups.

1. Read the latest group message that mentions 龙虾 or contains the fixed KOC fields.
2. Parse and validate the message with `scripts/parse_koc_message.py`.
3. Resolve the bound customer account from a group config JSON. Prefer `customer_account_id`; use account name only when the ID is missing.
   - For a new KOC project group, create a group preset before processing posts. Presets can include customer account, budget, ROI, conversion goal, schedule, audience, asset rule, smart coupon policy, bidder initials, and plan name template.
   - For multi-PM usage, the group preset should also record the responsible 追投 PM, the browser-enabled runtime/session that PM owns, and the expected Chrome profile when known. The skill is shared by all 龙虾 / 司南 instances, but 千川 login state and account permission are per PM/browser session.
   - After a group preset exists, content teammates may send a shorter KOC post message. Missing plan fields are filled from the group preset; 商品ID and 商品名称 should still be supplied when the brand has multiple products.
4. Open 巨量方舟 / 巨量千川 from `https://agent.oceanengine.com/admin/optimizeModule/qianchuan/promotion/domain/roi2-adv` with the user's current Chrome login state. First-time login for a project must be completed by the responsible 追投 PM; the skill only reuses an already-authenticated browser session. Prefer the Chrome plugin for live backend operations. Use `scripts/qianchuan_flow.py` only as a Playwright fallback when a separate browser profile is acceptable.
   - Before any live backend operation, run the browser preflight in `references/current-chrome-flow.md`: confirm the expected runtime/profile, Chrome connector availability, logged-in 千川 tab, selected customer account, and visible page state.
   - On Multica comment reruns/resume runs, repeat the browser preflight before clicking anything. Do not assume the resumed session still has a valid browser backend just because the previous direct run had one.
   - If the browser preflight detects a different Chrome profile, a blank/non-千川 tab, a missing Codex Chrome Extension connection, or a non-matching 千川 customer account, stop and write the blocker to the issue. Do not keep clicking, do not open a fresh generic Chrome profile, and do not claim the task is a business-flow failure.
   - When resuming after a user approval such as `继续发布计划`, `点击我知道了`, or `发布计划`, first re-locate the exact pending plan/draft or matching plan detail. If that state cannot be recovered, rebuild the pre-submit state from the task record and ask for confirmation again instead of guessing.
   - If the current runtime has no controllable Chrome/browser connector, do not claim the workflow can operate 千川 directly. Switch to manual-assist mode: parse the task, apply group presets, report the exact authorization/plan-building checklist, and ask for the PM to run it in a browser-enabled runtime.
   - If a group is assigned to a different 追投 PM than the current browser login, stop before backend operation and ask that PM to open/login from the assigned runtime. Do not operate a project through another PM's 千川 login unless the user explicitly confirms that account has the correct permission.
5. After entering the target customer account, perform plan-state triage before initiating any authorization work:
   - Search existing 商品全域投放 / 全域推商品 plans by the KOC达人名称, 抖音号/账号UID, 商品ID, 商品名称, and expected plan-name pattern when available.
   - If an exact same达人/抖音号 + 商品ID plan already exists and the current发布链接/视频素材 is already in that plan, record `素材已存在` or `PM已完成`, then send group feedback and stop. Do not check or initiate authorization again.
   - If an exact same达人/抖音号 + 商品ID plan already exists but the current发布链接/视频素材 is missing, record `计划已存在`, then add the new KOC video under the existing plan's 【素材】. Only check authorization if the page blocks the material append or shows an authorization-related error.
   - If a PM has already created the correct plan and it is active/valid, do not rebuild it. Feedback the visible plan status, plan name/ID, 商品ID, and whether the current素材 is present.
   - If no matching plan exists, continue to authorization status checks before creating a new plan.
6. Before initiating any new authorization, search the target 千川 account's 【抖音号授权】 and 【全域投放授权】 lists by KOC达人名称 first; if needed also search by 抖音号/ID. Prefer exact matches on达人名称 + 抖音号.
7. Read the visible authorization status for both rows:
   - If 【抖音号授权】 and 【全域投放授权】 both show `授权生效`, record `授权通过` and go directly to plan building.
   - If either row shows waiting/pending text such as `等待达人通过`, `待处理`, `待确认`, `审核中`, or `申请中`, record `等待达人授权` and send group feedback reminding the colleague who @龙虾 to push the达人完成授权确认.
   - If either authorization row is missing, initiate only the missing authorization. Do not duplicate an authorization that already shows `授权生效`. After initiating missing authorization for a new/unauthorized抖音号, stop the backend flow, record `等待达人授权`, and send group feedback to the content teammate who triggered the task: they must push the KOC达人 to approve both 【抖音号授权】 and 【全域投放授权】. Do not continue to plan building until a later check confirms both rows are `授权生效`.
8. For KOC视频带货, 全域投放授权 must use `商品全域投放权限` / `全域投放-商品投放`, not直播权限.
9. Send group feedback after status is known: plan/material already complete, authorized and entering plan, waiting for达人, newly initiated, or abnormal. Newly initiated authorization feedback must say which authorization(s) were initiated and that content teammates need to push the KOC达人 to approve before plan building can continue. For any plan/material result, first open the plan detail page and verify the final state from the detail tabs, then send feedback. The first feedback line must @ the responsible 追投 PM from the group preset, then use the fixed issue feedback format in `references/runbook.md`: `计划`、`计划 ID`、`搭建好时间`、`素材 ID`、`商品 ID`、`状态`、`预算`、`ROI`、`优惠券`、`达人`、`商品`、`结论`.
10. In the plan builder, click 【投放商品】 / 【添加商品】 and search/select by `商品ID` before filling budget/ROI. A brand can have multiple products, so do not infer the product from the brand/account alone.
11. If 千川 says `当前商品在该抖音号下已存在全域推商品-控成本投放计划`, do not create a duplicate plan. Open 【查看计划详情】, switch to 【素材】, and use 【添加视频】 to append the new KOC video as 自选投放素材 to the existing plan.
12. For KOC video-commerce plans, use 【自选投放素材】 when material selection is required; do not rely only on default intelligent material selection if the workflow asks for the KOC video asset. Search by the Douyin share link. If 千川 reports that the homepage video's cart product does not match the selected product ID, stop and feedback that the 商品ID is likely wrong.
13. Treat 【智能优惠券】 as a project/brand policy setting. It is allowed for the current 得宝 KOC test project, but other brands must not have coupons enabled unless the group config or message explicitly allows it. If 千川 defaults coupons on and the project policy is unknown or disallows coupons, stop before submission and feedback for confirmation.
14. Plan name convention comes from the project/group preset. A common template is `【{bidder_initials}】-{mmdd}-{koc_name}-{product_name}`. `WMQ` is only a test/project example, not a fixed default.
15. Before final plan submission, summarize account, 抖音号, 合作码, 商品ID, 商品名称, 发布链接, budget, bid/ROI, conversion goal, schedule, audience, asset rule, coupon policy, and plan name. In production, wait for group confirmation; in an explicitly approved test run, pass the submit flag. After a plan is created, a material is appended, or an existing plan/material is confirmed, open 【计划详情】 before closing: verify 【详情】 for达人、商品、预算、ROI、投放日期、智能优惠券, and verify 【素材】 for the current发布链接/video素材 ID and审核状态. Only then close the issue with the fixed feedback format. If the detail page does not match the trigger message or group preset, stop and report `异常需人工处理`.
16. At the end of every Multica-run KOC issue, write a short execution retrospective into the issue or operator notes: runtime used, run ID when visible, Chrome profile/runtime state, whether the browser preflight passed, plan-state branch taken, authorization branch taken, create/append/confirm result, detail-page readback, feedback message target/message ID, and any browser/UI blockers. If a human/Codex operator takes over after Multica stalls, explicitly record which steps were Multica-completed and which steps were manually completed.

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
- `计划已存在`
- `素材已存在`
- `已追加素材`
- `PM已完成`
- `计划已创建`
- `异常需人工处理`

Use `references/runbook.md` for operator rules, confirmation points, and known stop conditions.

## Safety Rules

- Never choose among multiple customer accounts silently.
- Never submit a plan unless the user has explicitly approved submission for that run or a group confirmation has been captured.
- Never force the task through authorization or plan creation when an existing matching plan/material state already closes the business request. Report the visible state and stop.
- Never send feedback to a real business group during testing unless the target chat is explicitly configured.
- Treat CAPTCHA, SMS, password, and扫码 steps as user-handled.
- First-time 巨量方舟/千川 login must be performed by the responsible project 追投 PM. Do not bypass login security; resume only after the browser is already inside 千川.
- A Feishu bot or cloud text-only agent without a controllable browser can read messages and prepare instructions, but cannot directly operate 千川.
- Do not reuse one PM's authenticated 千川 browser session as a global login for all projects. Route each project group to its configured responsible PM/browser runtime.
- If the backend UI wording differs from the expected labels, pause and report the visible alternatives instead of guessing.
