#!/usr/bin/env python3
"""Parse a KOC Feishu group message into normalized task JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


FIELD_ALIASES: dict[str, list[str]] = {
    "koc_name": ["达人名称", "达人", "KOC名称", "KOC达人", "koc名称", "koc达人"],
    "publish_link": ["发布链接", "发布地址", "视频链接", "内容链接", "链接"],
    "douyin_id": ["抖音号", "douyin号", "达人抖音号", "账号"],
    "cooperation_code": ["合作码", "授权码", "合作授权码"],
    "account_uid": ["账号UID", "账号uid", "UID", "uid"],
    "product_id": ["商品ID", "商品id", "商品 Id", "商品编号", "商品"],
    "product_name": ["商品名称", "商品名", "商品别名", "商品简称"],
    "daily_budget": ["日预算", "预算", "每日预算"],
    "bid_or_roi_target": ["出价/ROI目标", "ROI目标", "出价", "投放目标"],
    "conversion_goal": ["转化目标", "优化目标"],
    "schedule": ["投放时段", "时段", "投放时间"],
    "audience": ["定向/人群", "人群", "定向"],
    "asset_rule": ["素材规则", "素材", "视频规则"],
    "smart_coupon": ["智能优惠券", "优惠券", "券策略", "优惠券启用状态", "智能优惠券启用状态"],
    "plan_name": ["计划命名", "计划名称", "计划名"],
}

OPTIONAL_FIELDS = {"koc_name", "account_uid", "product_name", "smart_coupon"}
REQUIRED_FIELDS = [field for field in FIELD_ALIASES if field not in OPTIONAL_FIELDS]


@dataclass
class ParseResult:
    ok: bool
    task: dict[str, str]
    missing_fields: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "task": self.task,
            "missing_fields": self.missing_fields,
            "warnings": self.warnings,
        }


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", "", label).strip().lower()


def _label_to_field() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            mapping[_normalize_label(alias)] = field
    return mapping


def _strip_mentions(text: str) -> str:
    text = re.sub(r"(?m)^\s*@\S+\s*", "", text)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _infer_koc_name(task: dict[str, str]) -> str:
    existing = task.get("koc_name", "").strip()
    if existing:
        return existing

    publish_link = task.get("publish_link", "")
    for pattern in [
        r"【([^】]{1,30})的作品】",
        r"\[([^]\n]{1,30})的作品[^\]]*\]",
    ]:
        match = re.search(pattern, publish_link)
        if match:
            return match.group(1).strip()

    plan_name = task.get("plan_name", "")
    parts = [part.strip() for part in re.split(r"[-_—]+", plan_name) if part.strip()]
    for part in parts:
        part = re.sub(r"^【[^】]+】", "", part).strip()
        if not part or re.fullmatch(r"\d{3,8}", part):
            continue
        if any(keyword in part for keyword in ["KOC", "测试", "抽纸", "纸巾", "计划"]):
            continue
        return part
    return ""


def _extract_by_lines(text: str) -> dict[str, str]:
    label_map = _label_to_field()
    task: dict[str, str] = {}
    current_field: str | None = None
    current_value: list[str] = []

    def flush() -> None:
        nonlocal current_field, current_value
        if current_field:
            value = "\n".join(part.strip() for part in current_value).strip()
            if value:
                task[current_field] = value
        current_field = None
        current_value = []

    label_pattern = re.compile(r"^([^:：]{1,30})\s*[:：]\s*(.*)$")
    for raw_line in _strip_mentions(text).split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        match = label_pattern.match(line)
        if match:
            label, value = match.groups()
            field = label_map.get(_normalize_label(label))
            if field:
                flush()
                current_field = field
                current_value = [value.strip()]
                continue
        if current_field:
            current_value.append(line)
    flush()
    return task


def _extract_inline(text: str, existing: dict[str, str]) -> dict[str, str]:
    """Fallback for compact messages where fields are not one per line."""
    label_map = _label_to_field()
    labels = sorted(label_map, key=len, reverse=True)
    label_re = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(rf"({label_re})\s*[:：]\s*", flags=re.IGNORECASE)
    compact = re.sub(r"\s+", " ", _strip_mentions(text)).strip()
    matches = list(pattern.finditer(_normalize_label(compact)))
    if not matches:
        return existing

    # Build spans on a compacted copy. This fallback is best-effort; line parsing is authoritative.
    raw_compact = re.sub(r"\s+", " ", _strip_mentions(text)).strip()
    raw_matches = list(re.finditer(r"([^:：\s]{1,30})\s*[:：]\s*", raw_compact))
    for idx, match in enumerate(raw_matches):
        field = label_map.get(_normalize_label(match.group(1)))
        if not field or field in existing:
            continue
        start = match.end()
        end = raw_matches[idx + 1].start() if idx + 1 < len(raw_matches) else len(raw_compact)
        value = raw_compact[start:end].strip()
        if value:
            existing[field] = value
    return existing


def _extract_freeform(text: str, existing: dict[str, str]) -> dict[str, str]:
    """Best-effort parser for common KOC group messages without all labels."""
    stripped = _strip_mentions(text)
    if not existing.get("publish_link"):
        link_match = re.search(r"https?://\S+", stripped)
        if link_match:
            existing["publish_link"] = link_match.group(0).rstrip(")）。，,")
        else:
            douyin_line = next(
                (
                    line.strip()
                    for line in stripped.splitlines()
                    if "抖音" in line and ("作品" in line or "http" in line or "#" in line)
                ),
                "",
            )
            if douyin_line:
                existing["publish_link"] = douyin_line

    if not existing.get("koc_name"):
        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if "合作码" in line or "抖音号" in line or "账号UID" in line:
                for prior in reversed(lines[:idx]):
                    if (
                        len(prior) <= 30
                        and "：" not in prior
                        and ":" not in prior
                        and "http" not in prior
                        and "抖音" not in prior
                        and not prior.startswith("@")
                    ):
                        existing["koc_name"] = prior
                        break
                break
    return existing


def parse_message(text: str) -> ParseResult:
    task = _extract_by_lines(text)
    task = _extract_inline(text, task)
    task = _extract_freeform(text, task)
    inferred_koc_name = _infer_koc_name(task)
    if inferred_koc_name:
        task["koc_name"] = inferred_koc_name
    warnings: list[str] = []

    link = task.get("publish_link", "")
    if link and not re.search(r"https?://", link):
        warnings.append("publish_link does not look like a URL")

    douyin = task.get("douyin_id", "")
    if douyin and len(re.sub(r"\D", "", douyin)) < 4:
        warnings.append("douyin_id looks unusually short")

    missing = [field for field in REQUIRED_FIELDS if not task.get(field)]
    return ParseResult(ok=not missing, task=task, missing_fields=missing, warnings=warnings)


def _read_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    return sys.stdin.read()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse a KOC 千川 group message.")
    parser.add_argument("--text", help="Message text to parse.")
    parser.add_argument("--file", help="UTF-8 text file containing the message.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON.")
    args = parser.parse_args(argv)

    result = parse_message(_read_text(args))
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
