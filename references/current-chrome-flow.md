# 当前 Chrome 登录态执行流程

Use this path when the user says the 巨量方舟 / 千川 session is already logged in in their normal Chrome.

## Browser Rules

- Use the Chrome plugin / current Chrome tab control, not `scripts/qianchuan_flow.py`, when live login state matters.
- If no controllable Chrome/browser node is available, stop direct 千川 operation and switch to manual-assist mode. Tell the group that this runtime can parse and prepare the checklist, but a browser-enabled 龙虾 or responsible PM must operate 千川.
- Claim an existing tab if it is already on `agent.oceanengine.com`; otherwise open `https://agent.oceanengine.com/admin/optimizeModule/qianchuan/promotion/domain/roi2-adv` in Chrome.
- Never inspect cookies, local storage, passwords, or profile files.
- First-time login must be completed by the responsible project 追投 PM. Stop for CAPTCHA, SMS, scan code, password, account-risk verification, or missing login state.

## Live Operation Checklist

1. Parse the KOC task and resolve the bound customer account.
2. In current Chrome, open `https://agent.oceanengine.com/admin/optimizeModule/qianchuan/promotion/domain/roi2-adv`.
3. If the page is not already logged in, stop and ask the responsible project 追投 PM to complete login; continue only after 千川 is open.
4. Use the page's 【客户账户】 search with `customer_account_id` first; if missing, search `customer_account_name`.
5. If one exact match is visible, enter it. If there are zero or multiple plausible matches, stop.
6. Navigate to 【抖音号授权】 and search the KOC达人名称 first. If the row is not found, search by 抖音号/ID. Capture the matched达人名称、抖音号、授权类型、授权状态、授权时间.
7. Navigate to 【全域投放授权】, switch to 【非官方抖音号授权管理】 when applicable, and search the same KOC达人名称 first. If the row is not found, search by 抖音号/ID. For KOC视频带货, only treat `商品全域投放` / `商品全域投放权限` as the correct permission.
8. Branch from visible status:
   - Both rows show `授权生效`: update the ledger to `授权通过` and go directly to plan building.
   - A row shows waiting/pending status such as `等待达人通过`, `待处理`, `待确认`, `审核中`, or `申请中`: update the ledger to `等待达人授权`, send Feishu feedback telling the colleague who @龙虾 to push the达人 confirmation, and stop.
   - A row is missing: initiate only the missing authorization. For 全域投放授权 choose `商品全域投放权限`, then send feedback based on the submit result.
9. Before plan submit, summarize all critical fields. Submit only when the run has explicit user/test approval or captured group confirmation.

## Evidence To Capture

- Matched customer account name and ID.
- Visible authorization rows and status for 【抖音号授权】 and 【全域投放授权】.
- Visible success state or toast for any newly initiated authorization request.
- Feishu feedback dry-run or sent message result.
- Authorization status text before building the plan.
- Plan creation result or the final pre-submit field summary.
