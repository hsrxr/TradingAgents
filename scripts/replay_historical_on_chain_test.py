#!/usr/bin/env python3
"""Replay a historical TradingAgents run and submit it on-chain.

This script is meant for testing on-chain submission using a previously
recorded agent run structure from eval_results/**/TradingAgentsStrategy_logs.

Default behavior:
- Load the latest full_states_log_*.json for the given pair.
- Extract the historical final_trade_decision from that run.
- Submit the same decision to RiskRouter and ValidationRegistry.
- Print a compact summary of submission status.
- Write a small replay result JSON file for traceability.

Examples:
    python scripts/replay_historical_on_chain_test.py
    python scripts/replay_historical_on_chain_test.py --pair ETHUSD
    python scripts/replay_historical_on_chain_test.py --record "eval_results/ETHUSD/TradingAgentsStrategy_logs/full_states_log_2026-04-09 06-55-29.100215+00-00.json"
    python scripts/replay_historical_on_chain_test.py --wait-feedback --feedback-timeout 120
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from web3 import Web3

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tradingagents.web3_layer.on_chain_integration import create_on_chain_integrator

logger = logging.getLogger("replay_historical_on_chain_test")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _strip_code_fences(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _find_latest_historical_record(pair: str) -> Path:
    logs_dir = ROOT_DIR / "eval_results" / pair / "TradingAgentsStrategy_logs"
    if not logs_dir.exists():
        raise FileNotFoundError(f"No log directory found: {logs_dir}")

    candidates = sorted(logs_dir.glob("full_states_log_*.json"), key=lambda item: item.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No historical full_states_log_*.json files found in {logs_dir}")

    return candidates[-1]


def _extract_latest_run_state(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not payload:
        raise ValueError("Historical record is empty")

    # The recorded file usually stores a single timestamp key.
    if len(payload) == 1:
        run_key = next(iter(payload))
        run_state = payload[run_key]
        if not isinstance(run_state, dict):
            raise ValueError("Unexpected record structure: run payload is not an object")
        return run_key, run_state

    # Fallback: use the lexicographically latest timestamp-like key.
    run_key = sorted(payload.keys())[-1]
    run_state = payload[run_key]
    if not isinstance(run_state, dict):
        raise ValueError("Unexpected record structure: run payload is not an object")
    return run_key, run_state


def _extract_decision_json(run_state: dict[str, Any]) -> str:
    decision_raw = run_state.get("final_trade_decision") or run_state.get("trader_investment_decision")
    if decision_raw is None:
        raise ValueError("Historical record does not contain final_trade_decision")

    if isinstance(decision_raw, dict):
        return json.dumps(decision_raw, ensure_ascii=False)

    if not isinstance(decision_raw, str):
        raise TypeError(f"Unsupported decision type: {type(decision_raw)!r}")

    return _strip_code_fences(decision_raw)


def _extract_trade_pair(run_state: dict[str, Any], decision_json: str) -> str:
    pair = str(run_state.get("company_of_interest") or "").strip()
    if pair:
        return pair

    try:
        parsed = json.loads(decision_json)
        pair = str(parsed.get("pair") or "").strip()
        if pair:
            return pair
    except Exception:
        pass

    raise ValueError("Unable to determine trading pair from historical record")


def _refresh_trade_deadline(decision_json: str, ttl_seconds: int = 300) -> tuple[str, int | None, int | None]:
    parsed = json.loads(_strip_code_fences(decision_json))
    trade_intent = parsed.get("trade_intent")
    if not isinstance(trade_intent, dict):
        return json.dumps(parsed, ensure_ascii=False), None, None

    original_deadline = trade_intent.get("deadline")
    new_deadline = int(datetime.now(timezone.utc).timestamp()) + int(ttl_seconds)
    trade_intent["deadline"] = new_deadline
    return json.dumps(parsed, ensure_ascii=False), (
        int(original_deadline) if original_deadline is not None else None
    ), new_deadline


def _write_replay_result(output_dir: Path, result_payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    out_path = output_dir / f"historical_on_chain_test_{ts}.json"
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(result_payload, handle, ensure_ascii=False, indent=2)
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay a historical TradingAgents run and submit its decision on-chain.",
    )
    parser.add_argument(
        "--pair",
        default="ETHUSD",
        help="Trading pair folder to use when --record is not provided (default: ETHUSD)",
    )
    parser.add_argument(
        "--record",
        type=Path,
        default=None,
        help="Path to a specific full_states_log_*.json file to replay",
    )
    parser.add_argument(
        "--wait-feedback",
        action="store_true",
        help="Wait for RiskRouter approval/rejection after submitting the trade intent.",
    )
    parser.add_argument(
        "--feedback-timeout",
        type=int,
        default=180,
        help="Maximum seconds to wait for RiskRouter feedback when --wait-feedback is enabled.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Polling interval seconds for RiskRouter feedback.",
    )
    parser.add_argument(
        "--current-price-usd-scaled",
        type=int,
        default=0,
        help="Optional current price in cents used for checkpoint submission (default: 0).",
    )
    parser.add_argument(
        "--disable-simulation",
        action="store_true",
        help="Skip RiskRouter intent simulation before submitting.",
    )
    parser.add_argument(
        "--keep-historical-deadline",
        action="store_true",
        help="Keep the historical deadline instead of refreshing it for replay.",
    )
    parser.add_argument(
        "--submit-hold-decisions",
        action="store_true",
        help="Allow HOLD actions to be submitted as intent tests.",
    )
    return parser.parse_args()


def main() -> int:
    _configure_logging()
    load_dotenv()
    args = parse_args()

    required_env = [
        "SEPOLIA_RPC_URL",
        "OPERATOR_PRIVATE_KEY",
        "AGENT_WALLET_PRIVATE_KEY",
        "AGENT_ID",
        "AGENT_WALLET_ADDRESS",
    ]
    missing = [name for name in required_env if not (str(os.getenv(name) or "").strip())]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        return 1

    record_path = args.record
    if record_path is None:
        record_path = _find_latest_historical_record(args.pair)

    logger.info("Using historical record: %s", record_path)
    raw_payload = _load_json_file(record_path)
    run_key, run_state = _extract_latest_run_state(raw_payload)
    decision_json = _extract_decision_json(run_state)
    pair = _extract_trade_pair(run_state, decision_json)
    trade_date = str(run_state.get("trade_date") or run_key)

    original_decision = json.loads(_strip_code_fences(decision_json))
    original_deadline = None
    if isinstance(original_decision.get("trade_intent"), dict):
        original_deadline = original_decision["trade_intent"].get("deadline")

    effective_decision_json = decision_json
    refreshed_deadline = None
    if not args.keep_historical_deadline:
        effective_decision_json, original_deadline, refreshed_deadline = _refresh_trade_deadline(decision_json)
        logger.info(
            "Refreshed historical trade deadline for replay: original=%s new=%s",
            original_deadline,
            refreshed_deadline,
        )

    logger.info("Replay run key: %s", run_key)
    logger.info("Replay pair: %s", pair)
    logger.info("Replay trade_date: %s", trade_date)

    integrator = create_on_chain_integrator(
        enable_simulation=not args.disable_simulation,
        submit_hold_decisions=args.submit_hold_decisions,
    )
    if integrator is None:
        logger.error("Failed to initialize on-chain integrator; check .env and RPC connectivity.")
        return 1

    agent_wallet_address = integrator.client.agent_account.address
    agent_wallet_balance_wei = integrator.client.w3.eth.get_balance(agent_wallet_address)
    logger.info(
        "Agent wallet balance: %s ETH (%s wei)",
        Web3.from_wei(agent_wallet_balance_wei, "ether"),
        agent_wallet_balance_wei,
    )
    if agent_wallet_balance_wei == 0:
        logger.warning(
            "Agent wallet has no Sepolia ETH. RiskRouter submission can still work, but ValidationRegistry checkpoint submission may fail until the wallet is funded."
        )

    logger.info("Submitting historical final_trade_decision to RiskRouter and ValidationRegistry...")
    submission_result = integrator.submit_decision(
        final_decision_json=effective_decision_json,
        current_price_usd_scaled=args.current_price_usd_scaled,
        trade_date=trade_date,
    )

    feedback_result: dict[str, Any] | None = None
    if args.wait_feedback and submission_result.trade_submitted:
        logger.info("Waiting for RiskRouter feedback...")
        submission_result = integrator.wait_for_feedback(
            submission_result,
            max_wait_seconds=args.feedback_timeout,
            poll_interval_seconds=args.poll_interval,
        )
        feedback_result = {
            "trade_approved": submission_result.trade_approved,
            "trade_rejected": submission_result.trade_rejected,
            "approval_event": submission_result.approval_event,
            "rejection_event": submission_result.rejection_event,
            "rejection_reason": submission_result.rejection_reason,
            "metadata": submission_result.metadata,
        }

    summary = {
        "record_path": str(record_path),
        "run_key": run_key,
        "pair": pair,
        "trade_date": trade_date,
        "historical_trade_intent_deadline": original_deadline,
        "replay_trade_intent_deadline": refreshed_deadline,
        "decision_json": json.loads(_strip_code_fences(effective_decision_json)),
        "submission": {
            "submission_skipped": bool((submission_result.metadata or {}).get("submission_skipped", False)),
            "trade_submitted": bool(submission_result.trade_submitted),
            "checkpoint_submitted": bool(submission_result.checkpoint_submitted),
            "trade_intent_hash": submission_result.trade_intent_hash,
            "checkpoint_hash": submission_result.checkpoint_hash,
            "trade_error": submission_result.trade_error,
            "checkpoint_error": submission_result.checkpoint_error,
            "agent_wallet_balance_wei": agent_wallet_balance_wei,
            "metadata": submission_result.metadata,
        },
        "feedback": feedback_result,
    }

    results_dir = ROOT_DIR / "eval_results" / pair / "historical_on_chain_test_results"
    out_path = _write_replay_result(results_dir, summary)

    logger.info("Replay result saved to: %s", out_path)
    logger.info(
        "submission_skipped=%s | trade_submitted=%s | checkpoint_submitted=%s",
        summary["submission"]["submission_skipped"],
        summary["submission"]["trade_submitted"],
        summary["submission"]["checkpoint_submitted"],
    )

    if submission_result.trade_error:
        logger.error("Trade submission error: %s", submission_result.trade_error)
    if submission_result.checkpoint_error:
        logger.error("Checkpoint submission error: %s", submission_result.checkpoint_error)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
