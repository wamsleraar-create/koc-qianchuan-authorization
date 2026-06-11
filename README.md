# KOC Qianchuan Authorization Skill

This Codex skill supports KOC 巨量千川 authorization and product-plan workflows for group assistants such as 部门龙虾 / 司南.

## What It Does

- Reads KOC project group messages.
- Applies project-group defaults for customer account, budget, ROI, coupon policy, and plan naming.
- Checks 抖音号授权 and 全域投放授权 status before requesting new authorization.
- Uses 巨量方舟 / 巨量千川 current Chrome login state.
- Builds a 商品全域投放 plan or appends a new KOC video to an existing product plan.
- Sends Feishu group feedback for authorization, waiting, abnormal, or created-plan states.

## Deployment Model

The skill can be installed by cloud agents and by multiple 龙虾 assistants from the same GitHub repository. The skill code is shared, but each runtime still needs its own:

- Feishu/Lark app or user permissions.
- Project group config.
- 巨量方舟/千川 account permission.
- Browser session or login state.

First-time 巨量方舟/千川 login must be completed by the responsible project 追投 PM. The skill resumes after 千川 is already open and authenticated.

Entry URL:

```text
https://agent.oceanengine.com/admin/optimizeModule/qianchuan/promotion/domain/roi2-adv
```

## New Project Group Setup

When a new KOC project group pulls in 部门龙虾 / 司南, create a group config preset first:

```bash
python3 scripts/lark_koc_flow.py write-group-config \
  --output state/koc_groups.json \
  --project-chat-id oc_project_group \
  --project-group-name "KOC 项目群" \
  --feedback-chat-id oc_feedback_group \
  --customer-account-name "客户账户名称" \
  --customer-account-id "123456789" \
  --daily-budget "300" \
  --roi-target "3" \
  --conversion-goal "净成交ROI目标" \
  --schedule "全天" \
  --audience "无" \
  --asset-rule "使用发布链接视频" \
  --smart-coupon "启用" \
  --allow-smart-coupon true \
  --bidder-initials "WMQ" \
  --plan-name-template "【{bidder_initials}】-{mmdd}-{koc_name}-{product_name}"
```

After that, content teammates can send a shorter KOC message with the post details. If a brand has multiple products, the message should include 商品ID and 商品名称.

## Minimal KOC Message

```text
发布链接：https://v.douyin.com/xxxx/
达人名称：大甜甜
合作码：65638236777
抖音号：L9908311
账号UID：1814643757557485
商品ID：3823114170367345046
商品名称：柚子香
```

If 商品ID / 商品名称 are omitted, the group config must have exactly one unambiguous default product.

## Important Rules

- KOC video-commerce uses 全域投放 -> 商品投放.
- 全域投放授权 must be 商品全域投放权限, not live-room permission.
- If a product already has a full-domain product plan for the same Douyin account, open the existing plan and add the video under 素材 instead of creating a duplicate plan.
- If 千川 says the video cart product does not match the selected product ID, stop and ask for the correct product ID.
- 智能优惠券 follows project/brand policy. Do not enable it for unknown brands unless the group config or message explicitly allows it.
- Production submission requires group confirmation unless the current run is explicitly approved as a test submission.

## Local Validation

```bash
python3 scripts/smoke_test.py
```

