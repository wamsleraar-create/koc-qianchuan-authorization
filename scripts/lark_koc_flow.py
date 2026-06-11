#!/usr/bin/env python3
"""Feishu group helper for KOC 千川 tasks.

This script wraps lark-cli for message lookup/reply and stores a local task ledger.
It avoids sending messages unless --send is passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parse_koc_message import REQUIRED_FIELDS, parse_message


STATUSES = {
    "待授权",
    "已发起抖音号授权",
    "已发起全域投放授权",
    "等待达人授权",
    "授权通过",
    "计划已创建",
    "异常需人工处理",
}


def run_lark(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        ["lark-cli", *args, "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"lark-cli failed: {proc.stderr.strip() or proc.stdout.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"lark-cli returned non-JSON output: {proc.stdout[:500]}") from exc


def load_config(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "groups" not in data or not isinstance(data["groups"], dict):
        raise ValueError("config must contain a groups object")
    return data


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"tasks": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


def _today_mmdd() -> str:
    return datetime.now().strftime("%m%d")


def _format_plan_name(template: str, group: dict[str, Any], task: dict[str, str]) -> str:
    values = {
        "bidder_initials": group.get("bidder_initials", ""),
        "date": _today_mmdd(),
        "mmdd": _today_mmdd(),
        "koc_name": task.get("koc_name") or task.get("douyin_id", ""),
        "product_name": task.get("product_name", ""),
        "product_id": task.get("product_id", ""),
    }
    try:
        return template.format(**values)
    except KeyError:
        return template


def apply_group_defaults(task: dict[str, str], group: dict[str, Any]) -> dict[str, str]:
    merged = dict(task)
    defaults = group.get("plan_defaults") if isinstance(group.get("plan_defaults"), dict) else {}
    for field in [
        "daily_budget",
        "bid_or_roi_target",
        "conversion_goal",
        "schedule",
        "audience",
        "asset_rule",
        "smart_coupon",
    ]:
        if not merged.get(field) and defaults.get(field):
            merged[field] = str(defaults[field])

    product_defaults = group.get("product_defaults")
    if isinstance(product_defaults, dict) and len(product_defaults) == 1:
        product_id, product_name = next(iter(product_defaults.items()))
        if not merged.get("product_id"):
            merged["product_id"] = str(product_id)
        if not merged.get("product_name"):
            merged["product_name"] = str(product_name)

    if not merged.get("plan_name"):
        template = defaults.get("plan_name_template") or group.get("plan_name_template")
        if template:
            merged["plan_name"] = _format_plan_name(str(template), group, merged)
        elif group.get("bidder_initials") and merged.get("koc_name") and merged.get("product_name"):
            merged["plan_name"] = f"【{group['bidder_initials']}】-{_today_mmdd()}-{merged['koc_name']}-{merged['product_name']}"
    return merged


def missing_required(task: dict[str, str]) -> list[str]:
    return [field for field in REQUIRED_FIELDS if not task.get(field)]


def task_key(chat_id: str, task: dict[str, str]) -> str:
    seed = "|".join(
        [
            chat_id,
            task.get("douyin_id", ""),
            task.get("cooperation_code", ""),
            task.get("publish_link", ""),
            task.get("plan_name", ""),
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]


def read_chat_messages(chat_id: str, limit: int) -> list[dict[str, Any]]:
    result = run_lark(
        [
            "im",
            "+chat-messages-list",
            "--chat-id",
            chat_id,
            "--page-size",
            str(limit),
            "--as",
            "user",
        ]
    )
    data = result.get("data", result)
    messages = data.get("messages") or data.get("items") or result.get("messages") or []
    if not isinstance(messages, list):
        raise RuntimeError("unexpected lark message response shape")
    return messages


def message_text(message: dict[str, Any]) -> str:
    for key in ("text", "content", "body"):
        value = message.get(key)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed.get("text") or parsed.get("content") or value
            except json.JSONDecodeError:
                return value
        if isinstance(value, dict):
            return value.get("text") or value.get("content") or json.dumps(value, ensure_ascii=False)
    return json.dumps(message, ensure_ascii=False)


def send_message(chat_id: str, text: str, send: bool) -> None:
    if not send:
        print(json.dumps({"dry_run_send": {"chat_id": chat_id, "text": text}}, ensure_ascii=False))
        return
    run_lark(["im", "+messages-send", "--chat-id", chat_id, "--text", text, "--as", "user"])


def _chat_id_from_item(item: dict[str, Any]) -> str:
    for key in ("chat_id", "open_chat_id", "id"):
        value = item.get(key)
        if isinstance(value, str) and value.startswith("oc_"):
            return value
    detail = item.get("detail")
    if isinstance(detail, dict):
        return _chat_id_from_item(detail)
    return ""


def _chat_name_from_item(item: dict[str, Any]) -> str:
    for key in ("name", "chat_name", "title"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    detail = item.get("detail")
    if isinstance(detail, dict):
        return _chat_name_from_item(detail)
    return ""


def search_chat(args: argparse.Namespace) -> int:
    result = run_lark(
        [
            "im",
            "+chat-search",
            "--query",
            args.query,
            "--page-size",
            str(args.limit),
            "--as",
            "user",
        ]
    )
    data = result.get("data", result)
    items = data.get("items") or data.get("chats") or data.get("groups") or result.get("items") or []
    chats = []
    for item in items:
        if not isinstance(item, dict):
            continue
        chats.append(
            {
                "chat_id": _chat_id_from_item(item),
                "name": _chat_name_from_item(item),
                "raw": item if args.raw else None,
            }
        )
    print(json.dumps({"query": args.query, "chats": chats}, ensure_ascii=False, indent=2))
    return 0


def write_group_config(args: argparse.Namespace) -> int:
    if not args.project_chat_id.startswith("oc_"):
        raise ValueError("project_chat_id must be an oc_xxx chat id")
    if args.feedback_chat_id and not args.feedback_chat_id.startswith("oc_"):
        raise ValueError("feedback_chat_id must be an oc_xxx chat id")

    output = Path(args.output)
    config = load_config(str(output)) if output.exists() and args.merge else {"groups": {}}
    group: dict[str, Any] = {
        "group_name": args.project_group_name,
        "customer_account_name": args.customer_account_name,
        "customer_account_id": args.customer_account_id or "",
        "feedback_chat_id": args.feedback_chat_id or args.project_chat_id,
    }
    plan_defaults = {
        "daily_budget": args.daily_budget or "",
        "bid_or_roi_target": args.roi_target or "",
        "conversion_goal": args.conversion_goal or "",
        "schedule": args.schedule or "",
        "audience": args.audience or "",
        "asset_rule": args.asset_rule or "",
        "smart_coupon": args.smart_coupon or "",
        "plan_name_template": args.plan_name_template or "",
    }
    plan_defaults = {key: value for key, value in plan_defaults.items() if value}
    if plan_defaults:
        group["plan_defaults"] = plan_defaults
    if args.bidder_initials:
        group["bidder_initials"] = args.bidder_initials
    if args.allow_smart_coupon is not None:
        group["allow_smart_coupon"] = args.allow_smart_coupon

    config["groups"][args.project_chat_id] = group
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "group": config["groups"][args.project_chat_id]}, ensure_ascii=False, indent=2))
    return 0


def register_from_chat(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    group = config["groups"].get(args.chat_id)
    if not group:
        raise ValueError(f"chat_id {args.chat_id} not found in config")

    messages = read_chat_messages(args.chat_id, args.limit)
    ledger_path = Path(args.ledger)
    ledger = load_ledger(ledger_path)
    created: list[dict[str, Any]] = []

    for message in messages:
        text = message_text(message)
        result = parse_message(text)
        task = apply_group_defaults(result.task, group)
        missing = missing_required(task)
        if missing:
            continue
        key = task_key(args.chat_id, task)
        if key in ledger["tasks"] and not args.overwrite:
            continue
        record = {
            "task_key": key,
            "status": "待授权",
            "chat_id": args.chat_id,
            "feedback_chat_id": group.get("feedback_chat_id") or args.chat_id,
            "message_id": message.get("message_id") or message.get("id"),
            "customer_account_name": group.get("customer_account_name", ""),
            "customer_account_id": group.get("customer_account_id", ""),
            "task": task,
            "warnings": result.warnings,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        ledger["tasks"][key] = record
        created.append(record)

    save_ledger(ledger_path, ledger)
    print(json.dumps({"created": created, "ledger": str(ledger_path)}, ensure_ascii=False, indent=2))
    return 0


def register_from_text(args: argparse.Namespace) -> int:
    group = {}
    if args.config:
        config = load_config(args.config)
        group = dict(config["groups"].get(args.chat_id) or {})
    group.setdefault("feedback_chat_id", args.feedback_chat_id or args.chat_id)
    group.setdefault("customer_account_name", args.customer_account_name or "")
    group.setdefault("customer_account_id", args.customer_account_id or "")
    if bool(args.text) == bool(args.file):
        raise ValueError("provide exactly one of --text or --file")
    text = args.text if args.text else Path(args.file).read_text(encoding="utf-8")
    result = parse_message(text)
    task = apply_group_defaults(result.task, group)
    missing = missing_required(task)
    ledger_path = Path(args.ledger)
    ledger = load_ledger(ledger_path)

    if missing:
        output = {
            "ok": False,
            "missing_fields": missing,
            "warnings": result.warnings,
            "task": task,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 2

    key = task_key(args.chat_id, task)
    if key in ledger["tasks"] and not args.overwrite:
        print(json.dumps({"created": [], "existing": ledger["tasks"][key], "ledger": str(ledger_path)}, ensure_ascii=False, indent=2))
        return 0

    record = {
        "task_key": key,
        "status": "待授权",
        "chat_id": args.chat_id,
        "feedback_chat_id": group["feedback_chat_id"],
        "message_id": args.message_id,
        "customer_account_name": group["customer_account_name"],
        "customer_account_id": group["customer_account_id"],
        "task": task,
        "warnings": result.warnings,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    ledger["tasks"][key] = record
    save_ledger(ledger_path, ledger)
    print(json.dumps({"created": [record], "ledger": str(ledger_path)}, ensure_ascii=False, indent=2))
    return 0


def update_status(args: argparse.Namespace) -> int:
    if args.status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(STATUSES))}")
    ledger_path = Path(args.ledger)
    ledger = load_ledger(ledger_path)
    record = ledger["tasks"].get(args.task_key)
    if not record:
        raise KeyError(f"task not found: {args.task_key}")
    record["status"] = args.status
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    if args.note:
        record.setdefault("notes", []).append({"at": record["updated_at"], "text": args.note})
    save_ledger(ledger_path, ledger)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def feedback_text(record: dict[str, Any]) -> str:
    task = record["task"]
    koc_name = task.get("koc_name") or task.get("douyin_id", "")
    status = record.get("status", "")
    if status == "授权通过":
        return (
            "KOC 千川授权已生效，准备进入计划搭建\n"
            f"客户账户：{record.get('customer_account_name', '')}（{record.get('customer_account_id', '')}）\n"
            f"达人：{koc_name}\n"
            f"抖音号：{task.get('douyin_id', '')}\n"
            f"合作码：{task.get('cooperation_code', '')}\n"
            f"商品ID：{task.get('product_id', '')}\n"
            f"商品名称：{task.get('product_name', '')}\n"
            f"智能优惠券：{task.get('smart_coupon', '按项目配置')}\n"
            "授权状态：抖音号授权=授权生效；全域投放授权=商品全域投放/授权生效\n"
            f"计划名称：{task.get('plan_name', '')}"
        )
    if status == "等待达人授权":
        latest_note = ""
        notes = record.get("notes") or []
        if notes:
            latest_note = notes[-1].get("text", "")
        return (
            "KOC 千川授权待达人处理\n"
            f"客户账户：{record.get('customer_account_name', '')}（{record.get('customer_account_id', '')}）\n"
            f"达人：{koc_name}\n"
            f"抖音号：{task.get('douyin_id', '')}\n"
            f"合作码：{task.get('cooperation_code', '')}\n"
            f"商品ID：{task.get('product_id', '')}\n"
            f"商品名称：{task.get('product_name', '')}\n"
            f"当前状态：{latest_note or '等待达人通过授权'}\n"
            "请 @龙虾 的同学推动达人在抖音APP站内信或官方千川账户里确认授权；授权生效后再继续搭建计划。"
        )
    if status == "异常需人工处理":
        latest_note = ""
        notes = record.get("notes") or []
        if notes:
            latest_note = notes[-1].get("text", "")
        return (
            "KOC 千川授权异常，需人工处理\n"
            f"客户账户：{record.get('customer_account_name', '')}（{record.get('customer_account_id', '')}）\n"
            f"达人：{koc_name}\n"
            f"抖音号：{task.get('douyin_id', '')}\n"
            f"合作码：{task.get('cooperation_code', '')}\n"
            f"商品ID：{task.get('product_id', '')}\n"
            f"商品名称：{task.get('product_name', '')}\n"
            f"异常原因：{latest_note or '后台返回异常，请人工确认'}"
        )
    return (
        "已发起 KOC 千川授权\n"
        f"客户账户：{record.get('customer_account_name', '')}（{record.get('customer_account_id', '')}）\n"
        f"达人：{koc_name}\n"
        f"抖音号：{task.get('douyin_id', '')}\n"
        f"合作码：{task.get('cooperation_code', '')}\n"
        f"商品ID：{task.get('product_id', '')}\n"
        f"商品名称：{task.get('product_name', '')}\n"
        f"智能优惠券：{task.get('smart_coupon', '按项目配置')}\n"
        f"发布链接：{task.get('publish_link', '')}\n"
        "状态：已发起抖音号授权 + 全域投放授权，等待达人授权通过"
    )


def send_feedback(args: argparse.Namespace) -> int:
    ledger = load_ledger(Path(args.ledger))
    record = ledger["tasks"].get(args.task_key)
    if not record:
        raise KeyError(f"task not found: {args.task_key}")
    chat_id = args.chat_id or record.get("feedback_chat_id") or record.get("chat_id")
    send_message(chat_id, feedback_text(record), args.send)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="KOC 千川 Feishu group task helper.")
    parser.add_argument("--ledger", default="state/koc_qianchuan_tasks.json")
    sub = parser.add_subparsers(dest="cmd", required=True)

    chat = sub.add_parser("search-chat", help="Search visible Feishu group chats by name.")
    chat.add_argument("--query", required=True)
    chat.add_argument("--limit", type=int, default=10)
    chat.add_argument("--raw", action="store_true", help="Include raw lark-cli chat objects.")
    chat.set_defaults(func=search_chat)

    cfg = sub.add_parser("write-group-config", help="Write a group-to-customer-account binding config.")
    cfg.add_argument("--output", required=True)
    cfg.add_argument("--project-chat-id", required=True)
    cfg.add_argument("--project-group-name", required=True)
    cfg.add_argument("--feedback-chat-id")
    cfg.add_argument("--customer-account-name", required=True)
    cfg.add_argument("--customer-account-id", default="")
    cfg.add_argument("--daily-budget", default="")
    cfg.add_argument("--roi-target", default="")
    cfg.add_argument("--conversion-goal", default="")
    cfg.add_argument("--schedule", default="")
    cfg.add_argument("--audience", default="")
    cfg.add_argument("--asset-rule", default="")
    cfg.add_argument("--smart-coupon", default="", help="启用, 不启用, or 按项目配置.")
    cfg.add_argument("--allow-smart-coupon", type=lambda value: value.lower() in {"1", "true", "yes", "y", "启用", "允许"}, default=None)
    cfg.add_argument("--bidder-initials", default="")
    cfg.add_argument("--plan-name-template", default="")
    cfg.add_argument("--merge", action="store_true", help="Merge into an existing config file.")
    cfg.set_defaults(func=write_group_config)

    reg = sub.add_parser("register-from-chat", help="Read latest group messages and register valid KOC tasks.")
    reg.add_argument("--config", required=True)
    reg.add_argument("--chat-id", required=True)
    reg.add_argument("--limit", type=int, default=20)
    reg.add_argument("--overwrite", action="store_true")
    reg.set_defaults(func=register_from_chat)

    text = sub.add_parser("register-from-text", help="Register one KOC task from pasted text or a text file.")
    text.add_argument("--chat-id", required=True)
    text.add_argument("--config", help="Optional group config used to apply project defaults.")
    text.add_argument("--feedback-chat-id")
    text.add_argument("--customer-account-name", default="")
    text.add_argument("--customer-account-id", default="")
    text.add_argument("--message-id")
    text.add_argument("--text")
    text.add_argument("--file")
    text.add_argument("--overwrite", action="store_true")
    text.set_defaults(func=register_from_text)

    upd = sub.add_parser("update-status", help="Update a ledger task status.")
    upd.add_argument("--task-key", required=True)
    upd.add_argument("--status", required=True)
    upd.add_argument("--note")
    upd.set_defaults(func=update_status)

    fb = sub.add_parser("send-auth-feedback", help="Send or preview the authorization feedback message.")
    fb.add_argument("--task-key", required=True)
    fb.add_argument("--chat-id")
    fb.add_argument("--send", action="store_true")
    fb.set_defaults(func=send_feedback)

    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
