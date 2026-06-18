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
      "responsible_pm": "负责该项目的追投PM",
      "browser_runtime": "该PM已登录的可控浏览器环境名称",
      "chrome_profile_name": "可选，例如 Profile 4",
      "chrome_preferences_path": "可选，例如 /Users/xxx/Library/Application Support/Google/Chrome/Profile 4/Preferences",
      "login_note": "首次由负责PM在该环境登录，验证码/扫码由PM处理",
      "feedback_chat_id": "oc_xxx"
    }
  }
}
```

`customer_account_id` is preferred. If absent, the browser flow searches by `customer_account_name` and requires exactly one visible match.

For new KOC project groups, configure project defaults before content teammates start sending KOC posts. The preset can include:

- `customer_account_name` / `customer_account_id`
- `responsible_pm`
- `browser_runtime`
- `chrome_profile_name`
- `chrome_preferences_path`
- `login_note`
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

- Browser preflight: required before every direct 千川 operation and before every Multica comment rerun/resume. Check the configured runtime/profile, Chrome connector, logged-in 千川 tab, customer account, and current page state. If any browser condition fails, stop with a runtime blocker; do not continue as if it were an authorization or plan-building problem.
- Plan-state lookup: after entering the correct customer account, do this before authorization work. Search for existing same达人/抖音号 + 商品ID plans and confirm whether the current KOC video/material is already present. Also search whether this same达人/抖音号 already has another active/valid 商品全域投放 / 全域推商品 plan in the same account.
- Plan result verification: after creating a plan, appending material, or finding an existing matching plan, open 【计划详情】 before group feedback. Read back final fields from the detail page, not only from the creation page or plan list.
- Authorization status lookup: do this only when no matching plan exists and no same达人 historical active/valid 商品全域 plan exists in the same account, or when the plan/material append/new商品 build flow is explicitly blocked by authorization. Search both 【抖音号授权】 and 【全域投放授权】 using the KOC达人名称, then 抖音号/ID if needed.
- Authorization request: may proceed from a valid @龙虾 message only when the matching authorization row is missing or clearly not active. Do not duplicate requests that already show `授权生效`.
- Authorization wait gate: after initiating 抖音号授权 or 全域投放授权 for a new/unauthorized KOC达人, stop. Send group feedback telling the content teammate who triggered the task to push the KOC达人 to approve both authorizations. Continue plan building only after a later check confirms both authorization rows are `授权生效`.
- Feishu feedback: send only to the configured feedback chat.
- Plan submit: production requires group confirmation. Test runs can pass the submit flag only after the user explicitly allows it.
- Dismissible pre-submit warnings: if 千川 shows 商品前置检测 / `当前商品可能审核不通过` and provides `我知道了` or a similar acknowledgement button, record the warning text, click the acknowledgement, and continue automatically. Do not pause only for this warning. Stop only for hard blockers such as 商品ID/挂车商品不一致, missing required fields, authorization/account mismatch, no submit path after acknowledgement, or submit failure.

## Runtime And Resume Handling

This workflow commonly spans multiple Multica runs. Treat every continuation as a fresh browser-control operation.

Required handling:

1. Read the issue/task record and identify the last business state: plan-state triage, authorization wait, published plan, appended material, completed feedback, or a hard blocker. Dismissible warnings should normally be acknowledged and continued in the same run.
2. Run browser preflight before any 千川 click:
   - current runtime/agent
   - configured `browser_runtime`
   - configured `chrome_profile_name` / `chrome_preferences_path`
   - Chrome connector availability
   - visible 千川 domain/login state
   - visible customer account
   - current page state
3. If the current Chrome profile differs from the configured profile, stop and record `浏览器Profile不匹配`. Example from JCMA-263: the resumed run fell back to another Chrome profile while the logged-in 千川 account was in `Profile 4`; the correct behavior is to stop and report the runtime blocker, not to open a blank page and continue.
4. If the page is currently on a dismissible warning, verify the visible plan fields still match the issue, click `我知道了`, and continue. If the warning is a hard blocker or the fields no longer match, stop and report the blocker.
5. If the pending plan/draft is gone, do not assume it was submitted. Return to the plan list, search same达人/抖音号 + 商品ID, and decide whether the plan now exists. If not, rebuild to pre-submit and ask for confirmation again.
6. If a human/Codex operator completes steps after Multica stalls, write exactly which steps were automated and which were manually completed.

Required issue recap after every run:

```text
执行复盘：
Run ID：{run_id_or_unknown}
Runtime/Profile：{runtime} / {chrome_profile_or_unknown}
Browser preflight：{passed_or_blocked_reason}
业务分支：{已有计划素材已存在/已有计划追加素材/新建计划/等待达人授权/异常}
授权状态：抖音号授权={status}；全域投放授权={status}
计划详情回读：{plan_name} / {plan_id} / {budget} / {roi} / {coupon} / {material_id}
群反馈：{feedback_chat_or_group} / {message_id_or_not_sent}
人工接管：{无/有，说明接管步骤和原因}
```

## Plan-State Triage

After entering the target 千川 customer account, check whether the business task is already closed before doing authorization work:

1. Search 商品全域投放 / 全域推商品 plans by KOC达人名称、抖音号/账号UID、商品ID、商品名称、计划名 pattern. Keep two result sets: exact same达人/抖音号 + same商品ID plans, and same达人/抖音号 historical plans for other商品 in the same account.
2. If an exact same达人/抖音号 + 商品ID plan exists, open the plan detail and check:
   - plan name and ID
   - plan status, such as 投放中、暂停、审核中、异常
   - budget/ROI when visible
   - whether the current发布链接/视频素材 is already present under 【素材】
3. If the plan exists and the current素材 is already present, record `素材已存在` or `PM已完成`, feedback the visible plan state, and stop. Do not check authorization or create anything else.
4. If the plan exists but the current素材 is missing, record `计划已存在` and add the KOC video under 【素材】. Only branch to authorization lookup if 千川 blocks the append because authorization is missing/invalid.
5. If the plan exists but is paused/abnormal or does not clearly match the current达人 + 商品ID, stop and feedback the ambiguity instead of repairing or duplicating the plan.
6. If no same商品ID matching plan exists but there is an active/valid same达人/抖音号 商品全域投放 / 全域推商品 plan for another商品 in this account, treat authorization as already proven. Skip 【抖音号授权】 and 【全域投放授权】 checks, go directly to 【投放商品】 / 【添加商品】, select the new商品 by exact商品ID, and build the new商品 plan. Only return to authorization checks if 千川 explicitly blocks the new商品 flow with an authorization error.
7. If no matching same商品ID plan exists and no same达人 historical active/valid 商品全域 plan exists, continue to authorization checks and then build a new plan when authorization is active.

## Plan Detail Verification

Before sending a plan/material completion feedback, the agent must click into 【计划详情】 and verify the final plan state. This applies to all three branches: newly created plan, existing plan with appended material, and PM/already-existing plan.

Required verification:

1. Open the matching plan's detail page from the plan list or success result. Do not close the task from the list row alone.
2. In 【详情】, verify:
   - plan name and plan ID
   - plan status, such as `投放中`
   - selected达人 / 抖音号
   - selected商品 / 商品ID
   - optimization target and ROI target
   - daily budget
   -投放日期/投放时段 when visible
   - smart coupon status
   - creative/material selection settings, such as 自选投放素材、智能优选素材、AIGC动态创意
3. In 【素材】, verify:
   - the current发布链接/video is present
   - 素材 ID
   - material review status, such as `审核通过`
   - material is tied to the expected商品
4. Use the detail-page values in the group feedback. Do not rely only on the requested values or creation-form values.
5. If any verified field conflicts with the trigger message or group preset, stop and feedback `异常需人工处理`; do not say the task is closed.
6. If a field is not visible after checking the relevant detail tab, keep the field in the feedback and write `未获取到，需PM复核`.

## Authorization Status Branching

Search the target 千川 account before initiating authorization only after plan-state triage indicates that a new plan is needed or an append is blocked:

1. 【抖音号授权】: search KOC达人名称 first; if no exact match, search 抖音号/ID.
2. 【全域投放授权】: search KOC达人名称 first; if no exact match, search 抖音号/ID. For KOC视频带货, the required permission is `商品全域投放` / `商品全域投放权限`.
3. If both rows show `授权生效`, set the ledger status to `授权通过` and continue directly to plan building.
4. If either row shows `等待达人通过`, `待处理`, `待确认`, `审核中`, `申请中`, or similar pending text, set the ledger status to `等待达人授权`, send a group reminder, and stop until the达人 confirms.
5. If a required row is missing, initiate only that missing authorization. For 全域投放授权, select `商品全域投放权限`.
6. After initiating any missing authorization, set the task to `等待达人授权`, send feedback to the project group, and stop. The feedback must tell the content teammate who @龙虾/司南 to push the KOC达人 to approve both 【抖音号授权】 and 【全域投放授权】 in Douyin/official 千川 confirmation channels.
7. Do not build or submit a plan while either authorization is pending, even if the authorization request was successfully sent. Resume only after rechecking and seeing both rows as `授权生效`.

## Browser Selection

- For the real service-provider backend, prefer the current Chrome session via the Chrome plugin. This reuses the user's existing 巨量方舟 login state.
- Cloud/text-only agents without a browser connector cannot directly click 千川. They should run manual-assist mode: parse messages, apply group defaults, and output the exact PM checklist.
- Use `scripts/qianchuan_flow.py` only as a fallback with an explicit Chrome profile, because it starts a separate Playwright-controlled browser context and may require another login.

## Multi-PM Login Routing

- The skill package can be installed once and used by all 龙虾 / 司南 assistants, but 千川 login must be routed per project group.
- Each KOC project group should record the responsible 追投 PM and the browser-enabled runtime/session where that PM logs into 巨量方舟/千川.
- Before live backend operation, confirm that the current browser login belongs to the responsible PM or has explicit permission for the configured customer account.
- If the current runtime has no browser connector, or the browser login is from a different PM without confirmed permission, do not continue in 千川. Output the manual checklist and ask the responsible PM to run/login from the assigned browser runtime.
- Never treat one PM's authenticated browser as a shared global account for all KOC projects.

## Plan Building Rules

- Each project group can remember a default `商品ID`; if the trigger message omits `商品ID`, use the group memory only when it is unambiguous. Otherwise reply with the missing field and stop.
- A brand can have multiple products. Prefer the `商品ID` and `商品名称` provided in the trigger message for each KOC post; do not infer product solely from the customer account or brand.
- Before creating a new plan, confirm that no exact same达人/抖音号 + 商品ID plan already exists. If PM has already built it correctly, close the task with a status feedback instead of rebuilding. If only another商品 plan exists for the same达人 in the same account, skip repeated authorization checks and proceed to 【投放商品】 for the new商品 plan.
- In 【竞价投放】 -> 【全域投放】 -> 【推商品】, click 【投放商品】 / 【添加商品】 and search by `商品ID`.
- Select the exact product ID match. If the product list does not return that ID, stop and ask for the correct商品ID.
- If the product row says `当前商品在该抖音号下已存在全域推商品-控成本投放计划`, open 【查看计划详情】 instead of adding the product to a new plan. In the existing plan, switch to 【素材】 -> 【视频】 and click 【添加视频】 to add the current KOC video.
- For KOC视频带货 material setup, choose 【自选投放素材】 and select the KOC video/material tied to the发布链接. Do not rely only on default intelligent material selection when the business flow requires the posted KOC video.
- When adding a video, search by the Douyin share link. If 千川 says the homepage video's cart product does not match the selected product ID, stop and feedback that the 商品ID is likely wrong; ask the sender to provide the product ID actually mounted on the video.
- 【智能优惠券】 must follow the project/brand policy. For the current 得宝 KOC test project it can stay enabled. For other brands, default to not enabling coupons unless `allow_smart_coupon=true` is present in the group config or the trigger message explicitly says coupons are allowed. If the page defaults coupons on and policy is not allowed/unknown, stop before submission and ask for confirmation.
- Fill 日预算、净成交ROI目标、计划名称 after 商品 and素材 are selected; then stop at pre-submit summary unless the run is explicitly approved for submission.
- Plan naming comes from the project/group preset. A common template is `【{bidder_initials}】-{mmdd}-{koc_name}-{product_name}`. Values such as `WMQ`, `300`, `3`, and `柚子香` are examples from one test project, not fixed defaults.

## Stop Conditions

Stop and report `异常需人工处理` when:

- Required message fields are missing.
- Customer account search returns no result or multiple plausible results.
- The page asks for CAPTCHA, SMS, password, scan code, or other human verification.
- The expected authorization or plan-building controls are not visible.
- The required 商品ID is missing or the product drawer cannot find an exact product ID match.
- A matching plan exists but its status is paused/abnormal/ambiguous and the user has not asked to repair it.
- The page cannot confirm whether the current发布链接/视频素材 is already in the matching plan.
- 千川提示发布链接对应视频的挂车商品与所选商品ID不一致。
- The parsed plan budget or ROI target is inconsistent with the message.
- 智能优惠券 is enabled while the project/brand policy is unknown or disallows coupons.

## Required Issue Feedback Format

When reporting any plan/material result back to the project group, first @ the responsible 追投 PM from the group preset, then use this exact field order. Do not replace it with a long narrative. Fill these fields from the plan detail page after clicking 【计划详情】. Fill unknown values with `未获取到，需PM复核` only when the detail page does not expose the field after a reasonable check.

```text
@{responsible_pm}
计划：{plan_name}
计划 ID：{plan_id}
搭建好时间：{built_at}
素材 ID：{material_id}
商品 ID：{product_id}
状态：{plan_status}，{material_status}（{build_source}）
预算：{daily_budget}
ROI：{roi_target}
优惠券：{smart_coupon}
达人：{koc_name}（抖音号：{douyin_id}）
商品：{product_name}（商品ID：{product_id}）
结论：{conclusion}
```

Field rules:

- `@{responsible_pm}`: must be the configured responsible 追投 PM. If the Feishu API path supports rich-text mention by `open_id`, send a real mention; otherwise put `@姓名` as the first text line and report that the PM mention ID is missing from the group preset.
- `计划`: the visible 千川 plan name, such as `【WMQ】-0616-钱炸炸-柚子香`.
- `计划 ID`: the visible 千川 plan ID.
- `搭建好时间`: use the actual creation/append/completion time when visible; otherwise use the time the issue was verified and closed.
- `素材 ID`: the visible素材 ID for the current发布链接/video. If the task closed because the same素材 was already in the plan, still report that existing素材 ID when visible.
- `商品 ID`: the product ID from the trigger message or matched plan.
- `状态`: combine the visible plan state and material review state, then append source in parentheses:
  - `issue搭建` when 龙虾/司南 created the plan or appended the material during this task.
  - `人工已搭建好` when a PM had already created the plan/material before 龙虾/司南 operated.
  - `issue确认已有计划` when 龙虾/司南 only verified an existing plan and did not change it.
- `预算`: the visible daily budget read from 【计划详情】, not only the requested budget.
- `ROI`: the visible ROI target read from 【计划详情】, not only the requested ROI.
- `优惠券`: the visible smart coupon status read from 【计划详情】. If the project policy disallows coupons but the plan shows coupons enabled, stop and report `异常需人工处理` instead of closing.
- `达人`: the matched KOC达人 and 抖音号/ID read from 【计划详情】. If the visible plan达人 differs from the trigger message, stop and report ambiguity.
- `商品`: the matched product name and product ID read from 【计划详情】. If the visible plan商品 differs from the trigger 商品ID, stop and report ambiguity.
- `结论`: summarize the business closure. Examples:
  - `本次发布链接对应视频已经在计划里，所以没有追加、没有重复建计划。`
  - `已有同达人/抖音号 + 商品ID计划，本次仅追加素材，没有重复建计划。`
  - `未找到同达人/抖音号 + 商品ID计划，本次已新建计划并添加发布链接对应视频。`

Example:

```text
@翁美祺
计划：【WMQ】-0616-钱炸炸-柚子香
计划 ID：1868150564460612
搭建好时间：2026-06-16 18:30
素材 ID：7651944609197326370
商品 ID：3823114170367345046
状态：计划投放中，素材审核通过（人工已搭建好）
预算：300元/日
ROI：2.7（净成交ROI）
优惠券：已开启
达人：钱炸炸（抖音号：7474803）
商品：柚子香（商品ID：3823114170367345046）
结论：本次发布链接对应视频已经在计划里，所以没有追加、没有重复建计划。
```

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
内容同学：请推动 KOC 达人完成授权确认
抖音号：{douyin_id}
合作码：{cooperation_code}
发布链接：{publish_link}
已发起授权：{initiated_authorizations}
当前状态：等待达人通过授权
下一步：达人通过【抖音号授权】和【全域投放授权】后，龙虾/司南才能继续检查并搭建计划。
```

Plan created:

```text
@{responsible_pm}
计划：{plan_name}
计划 ID：{plan_id}
搭建好时间：{built_at}
素材 ID：{material_id}
商品 ID：{product_id}
状态：{plan_status}，{material_status}（issue搭建）
预算：{daily_budget}
ROI：{roi_target}
优惠券：{smart_coupon}
达人：{koc_name}（抖音号：{douyin_id}）
商品：{product_name}（商品ID：{product_id}）
结论：未找到同达人/抖音号 + 商品ID计划，本次已新建计划并添加发布链接对应视频。
```

Plan/material already complete:

```text
@{responsible_pm}
计划：{plan_name}
计划 ID：{plan_id}
搭建好时间：{built_at}
素材 ID：{material_id}
商品 ID：{product_id}
状态：{plan_status}，{material_status}（人工已搭建好）
预算：{daily_budget}
ROI：{roi_target}
优惠券：{smart_coupon}
达人：{koc_name}（抖音号：{douyin_id}）
商品：{product_name}（商品ID：{product_id}）
结论：本次发布链接对应视频已经在计划里，所以没有追加、没有重复建计划。
```

Existing plan, material appended:

```text
@{responsible_pm}
计划：{plan_name}
计划 ID：{plan_id}
搭建好时间：{built_at}
素材 ID：{material_id}
商品 ID：{product_id}
状态：{plan_status}，{material_status}（issue搭建）
预算：{daily_budget}
ROI：{roi_target}
优惠券：{smart_coupon}
达人：{koc_name}（抖音号：{douyin_id}）
商品：{product_name}（商品ID：{product_id}）
结论：已有同达人/抖音号 + 商品ID计划，本次仅追加素材，没有重复建计划。
```
