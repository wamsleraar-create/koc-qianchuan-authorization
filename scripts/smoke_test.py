#!/usr/bin/env python3
"""Offline smoke test for the KOC 千川 skill scripts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from parse_koc_message import REQUIRED_FIELDS, parse_message


SAMPLE_MESSAGE = """@部门龙虾
发布链接：https://www.douyin.com/video/123
抖音号：987654321
合作码：KOC-001
商品ID：3818510027619172445
日预算：300
出价/ROI目标：ROI 1.2
转化目标：商品成交
投放时段：全天
定向/人群：不限
素材规则：使用发布链接视频
计划命名：KOC测试-987654321
"""

MINIMAL_MESSAGE = """复制打开抖音，看看【示例达人的作品】示例商品视频标题 - 抖音 https://v.douyin.com/example/
示例达人
合作码：EXAMPLE-CODE
抖音号：EXAMPLE_DOUYIN_ID
账号UID：EXAMPLE_UID
商品ID：EXAMPLE_PRODUCT_ID
商品名称：示例商品
"""


def run_cmd(args: list[str]) -> dict:
    proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"command did not return JSON: {proc.stdout}") from exc


def assert_parse() -> None:
    result = parse_message(SAMPLE_MESSAGE)
    assert result.ok, result.to_dict()
    assert not result.missing_fields, result.to_dict()
    for field in REQUIRED_FIELDS:
        assert result.task.get(field), f"missing parsed field: {field}"


def assert_cli_flow(script_dir: Path) -> None:
    helper = script_dir / "lark_koc_flow.py"
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config_path = tmpdir / "groups.json"
        ledger_path = tmpdir / "ledger.json"

        config = run_cmd(
            [
                sys.executable,
                str(helper),
                "write-group-config",
                "--output",
                str(config_path),
                "--project-chat-id",
                "oc_project",
                "--project-group-name",
                "KOC项目测试群",
                "--feedback-chat-id",
                "oc_feedback",
                "--customer-account-name",
                "测试客户",
                "--customer-account-id",
                "123456",
                "--responsible-pm",
                "测试追投PM",
                "--browser-runtime",
                "测试PM的Chrome运行环境",
                "--login-note",
                "首次由测试追投PM登录",
                "--daily-budget",
                "300",
                "--roi-target",
                "3",
                "--conversion-goal",
                "净成交ROI目标",
                "--schedule",
                "全天",
                "--audience",
                "无",
                "--asset-rule",
                "使用发布链接视频",
                "--smart-coupon",
                "启用",
                "--allow-smart-coupon",
                "true",
                "--bidder-initials",
                "WMQ",
                "--plan-name-template",
                "【{bidder_initials}】-{mmdd}-{koc_name}-{product_name}",
            ]
        )
        assert config["ok"] is True
        assert config["group"]["responsible_pm"] == "测试追投PM"
        assert config["group"]["browser_runtime"] == "测试PM的Chrome运行环境"
        assert config_path.exists()

        registered = run_cmd(
            [
                sys.executable,
                str(helper),
                "--ledger",
                str(ledger_path),
                "register-from-text",
                "--chat-id",
                "oc_project",
                "--feedback-chat-id",
                "oc_feedback",
                "--customer-account-name",
                "测试客户",
                "--customer-account-id",
                "123456",
                "--text",
                SAMPLE_MESSAGE,
            ]
        )
        created = registered["created"]
        assert len(created) == 1, registered
        task_key = created[0]["task_key"]

        feedback = run_cmd(
            [
                sys.executable,
                str(helper),
                "--ledger",
                str(ledger_path),
                "send-auth-feedback",
                "--task-key",
                task_key,
            ]
        )
        text = feedback["dry_run_send"]["text"]
        assert "已发起 KOC 千川授权" in text
        assert "987654321" in text
        assert "KOC-001" in text
        assert "3818510027619172445" in text

        minimal = run_cmd(
            [
                sys.executable,
                str(helper),
                "--ledger",
                str(ledger_path),
                "register-from-text",
                "--chat-id",
                "oc_project",
                "--config",
                str(config_path),
                "--text",
                MINIMAL_MESSAGE,
            ]
        )
        minimal_task = minimal["created"][0]["task"]
        assert minimal_task["daily_budget"] == "300"
        assert minimal_task["bid_or_roi_target"] == "3"
        assert minimal_task["smart_coupon"] == "启用"
        assert minimal_task["plan_name"].endswith("-示例达人-示例商品")


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    assert_parse()
    assert_cli_flow(script_dir)
    print(json.dumps({"ok": True, "checked": ["parse", "group_config", "register_from_text", "feedback_dry_run"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
