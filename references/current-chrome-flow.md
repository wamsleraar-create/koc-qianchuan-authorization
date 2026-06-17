# 当前 Chrome 登录态执行流程

Use this path when the user says the 巨量方舟 / 千川 session is already logged in in their normal Chrome.

## Browser Rules

- Use the Chrome plugin / current Chrome tab control, not `scripts/qianchuan_flow.py`, when live login state matters.
- If no controllable Chrome/browser node is available, stop direct 千川 operation and switch to manual-assist mode. Tell the group that this runtime can parse and prepare the checklist, but a browser-enabled 龙虾 or responsible PM must operate 千川.
- Claim an existing tab if it is already on `agent.oceanengine.com`; otherwise open `https://agent.oceanengine.com/admin/optimizeModule/qianchuan/promotion/domain/roi2-adv` in Chrome.
- Never inspect cookies, local storage, passwords, or profile files.
- First-time login must be completed by the responsible project 追投 PM. Stop for CAPTCHA, SMS, scan code, password, account-risk verification, or missing login state.
- For multi-PM deployments, use the group config's responsible PM / browser runtime fields to decide who should own the login. Do not reuse another PM's browser session unless the user explicitly confirms it has the correct customer-account permission.

## Live Operation Checklist

1. Parse the KOC task and resolve the bound customer account.
2. Check the group config for `responsible_pm` and `browser_runtime`. If the current browser-enabled runtime is not the assigned one, stop and ask the responsible PM to log in from the assigned runtime.
3. In current Chrome, open `https://agent.oceanengine.com/admin/optimizeModule/qianchuan/promotion/domain/roi2-adv`.
4. If the page is not already logged in, stop and ask the responsible project 追投 PM to complete login; continue only after 千川 is open.
5. Use the page's 【客户账户】 search with `customer_account_id` first; if missing, search `customer_account_name`.
6. If one exact match is visible, enter it. If there are zero or multiple plausible matches, stop.
7. Before authorization work, search existing 商品全域投放 / 全域推商品 plans by达人名称、抖音号/账号UID、商品ID、商品名称、计划名 pattern. Capture any exact same达人/抖音号 + 商品ID plan and its visible status.
8. Branch from visible plan/material state:
   - Matching plan exists and the current发布链接/视频素材 is already present: update the ledger to `素材已存在` or `PM已完成`, open 【计划详情】, verify 【详情】 and 【素材】 fields, send group feedback with detail-page values, and stop.
   - Matching plan exists but current素材 is missing: update the ledger to `计划已存在`, open the plan detail, switch to 【素材】, and add the KOC video. Only check authorization if the append flow is blocked by an authorization error. After appending, stay in/open 【计划详情】 and verify final 【详情】 and 【素材】 fields before feedback.
   - Matching plan exists but status is paused/error/ambiguous: feedback the visible plan status and stop for PM confirmation unless the user explicitly asks to repair it.
   - No matching plan exists: continue to authorization checks before creating a new plan.
9. Navigate to 【抖音号授权】 and search the KOC达人名称 first. If the row is not found, search by 抖音号/ID. Capture the matched达人名称、抖音号、授权类型、授权状态、授权时间.
10. Navigate to 【全域投放授权】, switch to 【非官方抖音号授权管理】 when applicable, and search the same KOC达人名称 first. If the row is not found, search by 抖音号/ID. For KOC视频带货, only treat `商品全域投放` / `商品全域投放权限` as the correct permission.
11. Branch from visible authorization status:
   - Both rows show `授权生效`: update the ledger to `授权通过` and go directly to plan building.
   - A row shows waiting/pending status such as `等待达人通过`, `待处理`, `待确认`, `审核中`, or `申请中`: update the ledger to `等待达人授权`, send Feishu feedback telling the colleague who @龙虾 to push the达人 confirmation, and stop.
   - A row is missing: initiate only the missing authorization. For 全域投放授权 choose `商品全域投放权限`. After the request is sent, update the ledger to `等待达人授权`, send Feishu feedback telling the content teammate who @龙虾/司南 to push the KOC达人 to approve both authorizations, and stop. Do not continue to plan building in the same run.
12. Before plan submit, summarize all critical fields. Submit only when the run has explicit user/test approval or captured group confirmation.
13. After submit succeeds, click into the created plan's 【计划详情】. Verify from 【详情】: plan name/ID/status, selected达人, selected商品, daily budget, ROI target,投放日期, smart coupon status, and creative settings. Verify from 【素材】: current发布链接/video,素材 ID, and material review status. Use these detail-page values in the group feedback. If anything conflicts with the trigger message or group preset, stop and report `异常需人工处理`.

## Evidence To Capture

- Matched customer account name and ID.
- Visible authorization rows and status for 【抖音号授权】 and 【全域投放授权】.
- Visible matching plan row/detail, plan ID/status, and whether the current发布链接/视频素材 is already present.
- Plan detail page verification after create/append/existing-plan confirmation: 【详情】 values and 【素材】 values.
- Visible success state or toast for any newly initiated authorization request.
- Feishu feedback dry-run or sent message result.
- Authorization status text before building the plan.
- Plan creation result or the final pre-submit field summary.
