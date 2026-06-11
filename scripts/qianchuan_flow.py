#!/usr/bin/env python3
"""Conservative Playwright fallback for KOC 巨量千川 authorization and plan building.

This script starts a Playwright-controlled Chrome profile. It cannot attach to an
already-open user Chrome tab. For live runs that must reuse the user's current
Chrome login state, use the Chrome plugin flow described in references/current-chrome-flow.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

QIANCHUAN_URL = "https://agent.oceanengine.com/admin/optimizeModule/qianchuan/promotion/domain/roi2-adv"
DEFAULT_PROFILE = os.path.expanduser("~/.koc-qianchuan/chrome-profile")


@dataclass
class Account:
    name: str
    account_id: str = ""


@dataclass
class KocTask:
    publish_link: str
    douyin_id: str
    cooperation_code: str
    product_id: str
    daily_budget: str
    bid_or_roi_target: str
    conversion_goal: str
    schedule: str
    audience: str
    asset_rule: str
    plan_name: str
    koc_name: str = ""


def load_record(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "task" in data:
        return data
    return {"task": data}


async def click_first_text(page: Any, labels: list[str], timeout: int = 1500) -> str | None:
    for label in labels:
        try:
            await page.get_by_text(label, exact=True).first.click(timeout=timeout)
            return label
        except Exception:
            pass
        try:
            await page.get_by_role("button", name=label).first.click(timeout=timeout)
            return label
        except Exception:
            pass
    return None


async def visible_text(page: Any) -> str:
    try:
        return await page.evaluate("document.body ? document.body.innerText : ''")
    except Exception:
        return ""


async def stop_on_human_verification(page: Any) -> None:
    text = await visible_text(page)
    markers = ["验证码", "短信", "扫码", "安全验证", "密码", "登录"]
    if any(marker in text for marker in markers):
        raise RuntimeError("页面出现登录/验证步骤，需要人工处理")


async def fill_near_label(page: Any, label: str, value: str, timeout: int = 1500) -> bool:
    if not value:
        return False
    selectors = [
        f"xpath=//*[normalize-space()='{label}']/following::input[1]",
        f"xpath=//*[contains(normalize-space(),'{label}')]/following::input[1]",
        f"xpath=//*[normalize-space()='{label}']/following::textarea[1]",
        f"xpath=//*[contains(normalize-space(),'{label}')]/following::textarea[1]",
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            await loc.fill(value, timeout=timeout)
            return True
        except Exception:
            continue
    return False


async def open_browser(headless: bool, profile: str) -> tuple[Any, Any, Any]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required: pip install playwright && playwright install chromium") from exc
    playwright = await async_playwright().start()
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=profile,
        channel="chrome",
        headless=headless,
        viewport={"width": 1440, "height": 1000},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.pages[0] if context.pages else await context.new_page()
    return playwright, context, page


async def search_customer_account(page: Any, account: Account) -> None:
    await page.goto(QIANCHUAN_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)
    await stop_on_human_verification(page)

    query = account.account_id or account.name
    if not query:
        raise RuntimeError("missing customer account name/id")

    filled = False
    for label in ["客户账户", "账户", "搜索"]:
        if await fill_near_label(page, label, query):
            filled = True
            break
    if not filled:
        # Fallback to the first visible search input.
        for selector in ["input[placeholder*='客户账户']", "input[placeholder*='搜索']", "input"]:
            try:
                await page.locator(selector).first.fill(query, timeout=1500)
                filled = True
                break
            except Exception:
                continue
    if not filled:
        raise RuntimeError("未找到客户账户搜索框")

    await page.keyboard.press("Enter")
    await page.wait_for_timeout(2500)
    await stop_on_human_verification(page)

    text = await visible_text(page)
    if query not in text and account.name and account.name not in text:
        raise RuntimeError("客户账户搜索后未看到匹配账户")
    clicked = await click_first_text(page, [account.account_id, account.name, "进入", "选择"])
    if not clicked:
        raise RuntimeError("未能进入客户账户，请人工确认搜索结果")
    await page.wait_for_timeout(2500)


async def initiate_authorizations(page: Any, task: KocTask) -> dict[str, Any]:
    await stop_on_human_verification(page)
    actions: list[str] = []

    auth_entry = await click_first_text(page, ["授权", "达人授权", "抖音号授权", "账户授权"])
    if auth_entry:
        actions.append(f"进入授权入口:{auth_entry}")
        await page.wait_for_timeout(1500)

    if not await fill_near_label(page, "抖音号", task.douyin_id):
        await fill_near_label(page, "账号", task.douyin_id)
    if not await fill_near_label(page, "合作码", task.cooperation_code):
        await fill_near_label(page, "授权码", task.cooperation_code)

    dy_auth = await click_first_text(page, ["抖音号授权", "发起抖音号授权", "发起授权", "确定"])
    if not dy_auth:
        raise RuntimeError("未找到抖音号授权按钮")
    actions.append(f"抖音号授权:{dy_auth}")
    await page.wait_for_timeout(2000)
    await stop_on_human_verification(page)

    full_auth = await click_first_text(page, ["全域投放授权", "发起全域投放授权", "确认授权", "确定"])
    if not full_auth:
        raise RuntimeError("未找到全域投放授权按钮")
    actions.append(f"全域投放授权:{full_auth}")
    await page.wait_for_timeout(2000)
    await stop_on_human_verification(page)
    return {"ok": True, "actions": actions}


AUTHORIZED_MARKERS = ["授权生效", "授权通过", "已授权"]
WAITING_MARKERS = ["等待达人通过", "等待授权", "待处理", "待确认", "审核中", "申请中", "授权中", "待授权"]


def classify_authorization_status(text: str) -> str:
    if any(marker in text for marker in AUTHORIZED_MARKERS):
        return "authorized"
    if any(marker in text for marker in WAITING_MARKERS):
        return "waiting"
    return "unknown"


async def search_authorization_list(page: Any, task: KocTask, labels: list[str]) -> dict[str, Any]:
    query_values = [task.koc_name, task.douyin_id]
    clicked = await click_first_text(page, labels, timeout=1200)
    if clicked:
        await page.wait_for_timeout(1500)
    await stop_on_human_verification(page)

    for query in [value for value in query_values if value]:
        filled = False
        for label in ["搜索", "抖音号", "达人", "名称"]:
            if await fill_near_label(page, label, query, timeout=800):
                filled = True
                break
        if not filled:
            for selector in ["input[placeholder*='名称']", "input[placeholder*='抖音号']", "input[placeholder*='搜索']", "input"]:
                try:
                    await page.locator(selector).first.fill(query, timeout=800)
                    filled = True
                    break
                except Exception:
                    continue
        if not filled:
            continue
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1800)
        text = await visible_text(page)
        if query in text:
            return {
                "query": query,
                "found": True,
                "status": classify_authorization_status(text),
                "visible_text_excerpt": text[:1500],
            }
    text = await visible_text(page)
    return {
        "query": "",
        "found": False,
        "status": "missing",
        "visible_text_excerpt": text[:1500],
    }


async def check_authorization(page: Any, task: KocTask) -> dict[str, Any]:
    await stop_on_human_verification(page)
    douyin_auth = await search_authorization_list(page, task, ["抖音号授权"])
    full_domain_auth = await search_authorization_list(page, task, ["全域投放授权", "非官方抖音号授权管理"])
    authorized = douyin_auth["status"] == "authorized" and full_domain_auth["status"] == "authorized"
    waiting = douyin_auth["status"] == "waiting" or full_domain_auth["status"] == "waiting"
    missing = [name for name, result in [("抖音号授权", douyin_auth), ("全域投放授权", full_domain_auth)] if result["status"] == "missing"]
    next_action = "build-plan" if authorized else "send-waiting-feedback" if waiting else "initiate-missing-authorization"
    return {
        "ok": True,
        "authorized": authorized,
        "waiting": waiting,
        "missing": missing,
        "next_action": next_action,
        "douyin_auth": douyin_auth,
        "full_domain_auth": full_domain_auth,
    }


async def build_plan(page: Any, task: KocTask, submit: bool) -> dict[str, Any]:
    await stop_on_human_verification(page)
    clicked = await click_first_text(page, ["新建计划", "创建计划", "新建推广", "新建"])
    if not clicked:
        raise RuntimeError("未找到新建计划入口")
    await page.wait_for_timeout(2000)

    fill_results = {
        "计划名称": await fill_near_label(page, "计划名称", task.plan_name),
        "日预算": await fill_near_label(page, "日预算", task.daily_budget),
        "出价/ROI目标": await fill_near_label(page, "出价", task.bid_or_roi_target)
        or await fill_near_label(page, "ROI", task.bid_or_roi_target),
        "转化目标": await fill_near_label(page, "转化目标", task.conversion_goal),
        "投放时段": await fill_near_label(page, "投放时段", task.schedule),
        "定向/人群": await fill_near_label(page, "定向", task.audience)
        or await fill_near_label(page, "人群", task.audience),
        "素材规则": await fill_near_label(page, "素材", task.asset_rule),
    }

    missing = [name for name, ok in fill_results.items() if not ok]
    if missing:
        raise RuntimeError(f"以下计划字段未能自动填写，请人工处理: {', '.join(missing)}")

    if submit:
        submitted = await click_first_text(page, ["提交", "发布", "创建", "确认提交"], timeout=2000)
        if not submitted:
            raise RuntimeError("未找到计划提交按钮")
        await page.wait_for_timeout(3000)
        await stop_on_human_verification(page)
        return {"ok": True, "submitted": True, "submit_button": submitted}

    return {"ok": True, "submitted": False, "message": "计划字段已填写，停在提交前"}


async def run(args: argparse.Namespace) -> dict[str, Any]:
    record = load_record(args.record)
    task = KocTask(**record["task"])
    account = Account(
        name=args.customer_account_name or record.get("customer_account_name", ""),
        account_id=args.customer_account_id or record.get("customer_account_id", ""),
    )

    playwright, context, page = await open_browser(args.headless, args.chrome_profile)
    try:
        await search_customer_account(page, account)
        if args.action == "authorize":
            result = await initiate_authorizations(page, task)
        elif args.action == "check-auth":
            result = await check_authorization(page, task)
        elif args.action == "build-plan":
            result = await build_plan(page, task, args.submit_plan)
        else:
            raise ValueError(f"unsupported action: {args.action}")
        result["account"] = account.__dict__
        result["plan_name"] = task.plan_name
        return result
    finally:
        if args.keep_open:
            print("Browser left open for handoff. Press Ctrl+C to exit when done.", file=sys.stderr)
            while True:
                await asyncio.sleep(3600)
        await context.close()
        await playwright.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run KOC 千川 browser flow.")
    parser.add_argument("--record", required=True, help="JSON task record or parsed task file.")
    parser.add_argument("--action", choices=["authorize", "check-auth", "build-plan"], required=True)
    parser.add_argument("--customer-account-name")
    parser.add_argument("--customer-account-id")
    parser.add_argument("--chrome-profile", default=DEFAULT_PROFILE)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--submit-plan", action="store_true", help="Actually submit/create the plan.")
    parser.add_argument("--keep-open", action="store_true", help="Leave browser open for manual handoff.")
    args = parser.parse_args()

    try:
        result = asyncio.run(run(args))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
