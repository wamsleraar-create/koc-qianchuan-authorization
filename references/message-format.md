# KOC 群消息格式

## Standard Trigger

```text
@部门龙虾
发布链接：https://www.douyin.com/...
抖音号：123456789
合作码：KOC-ABC-001
商品ID：3818510027619172445
商品名称：柚子香
日预算：300
出价/ROI目标：ROI 1.2
转化目标：商品成交
投放时段：全天
定向/人群：不限，按项目默认
素材规则：使用发布链接视频
智能优惠券：按项目配置
计划命名：KOC-项目名-达人名-0611
```

## Field Meaning

| Field | Required | Meaning |
| --- | --- | --- |
| 发布链接 | yes | Douyin content/video link used for authorization or asset selection. |
| 抖音号 | yes | KOC Douyin account identifier. |
| 合作码 | yes | Core authorization identifier. |
| 商品ID | yes | Product ID used in 千川 【添加商品】 search. It can come from the project group's remembered default product ID only when the group has one unambiguous product. |
| 商品名称 | recommended | Short product alias used for plan naming and human feedback. Required when one brand has multiple active products. |
| 日预算 | yes | Daily plan budget. |
| 出价/ROI目标 | yes | Bid or ROI target. Preserve the original wording. |
| 转化目标 | yes | Conversion goal to select in 千川. |
| 投放时段 | yes | Schedule window. |
| 定向/人群 | yes | Targeting / audience rule. |
| 素材规则 | yes | Which asset/video to use. |
| 智能优惠券 | recommended | Coupon policy for this plan. Accepts `启用`, `不启用`, or `按项目配置`. If omitted, use project/brand config; if unknown, stop before publishing. |
| 计划命名 | yes | Plan name to create. |

## Accepted Aliases

- 发布链接: `发布地址`, `视频链接`, `内容链接`, `链接`
- 抖音号: `douyin号`, `达人抖音号`, `账号`
- 合作码: `授权码`, `合作授权码`
- 商品ID: `商品id`, `商品 Id`, `商品编号`, `商品`
- 商品名称: `商品名`, `商品别名`, `商品简称`
- 日预算: `预算`, `每日预算`
- 出价/ROI目标: `ROI目标`, `出价`, `投放目标`
- 转化目标: `优化目标`
- 投放时段: `时段`, `投放时间`
- 定向/人群: `人群`, `定向`
- 素材规则: `素材`, `视频规则`
- 智能优惠券: `优惠券`, `券策略`, `优惠券启用状态`, `智能优惠券启用状态`
- 计划命名: `计划名称`, `计划名`
