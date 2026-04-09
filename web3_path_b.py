import json
import os
import time
from pathlib import Path

import typer
from dotenv import load_dotenv

from tradingagents.web3_layer import HackathonWeb3Client


load_dotenv()

app = typer.Typer(help="Standalone ERC-8004 Path B Web3 runner (Sepolia shared contracts).")


def _client() -> HackathonWeb3Client:
    rpc_url = os.getenv("SEPOLIA_RPC_URL", "").strip()
    operator_private_key = os.getenv("OPERATOR_PRIVATE_KEY", "").strip()
    agent_private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY", "").strip()

    if not rpc_url:
        raise typer.BadParameter("Missing SEPOLIA_RPC_URL in environment.")
    if not operator_private_key:
        raise typer.BadParameter("Missing OPERATOR_PRIVATE_KEY in environment.")
    if not agent_private_key:
        raise typer.BadParameter("Missing AGENT_WALLET_PRIVATE_KEY in environment.")

    addresses = {
        "agent_registry": os.getenv("AGENT_REGISTRY_ADDRESS", "").strip(),
        "hackathon_vault": os.getenv("HACKATHON_VAULT_ADDRESS", "").strip(),
        "risk_router": os.getenv("RISK_ROUTER_ADDRESS", "").strip(),
        "reputation_registry": os.getenv("REPUTATION_REGISTRY_ADDRESS", "").strip(),
        "validation_registry": os.getenv("VALIDATION_REGISTRY_ADDRESS", "").strip(),
    }
    addresses = {k: v for k, v in addresses.items() if v}

    return HackathonWeb3Client(
        rpc_url=rpc_url,
        operator_private_key=operator_private_key,
        agent_private_key=agent_private_key,
        addresses=addresses,
    )


@app.command("register")
def register_agent(
    name: str = typer.Option(...),
    description: str = typer.Option(...),
    capabilities: str = typer.Option("trading,eip712-signing"),
    agent_uri: str = typer.Option(""),
    out_file: Path = typer.Option(Path("agent-id.json")),
) -> None:
    client = _client()
    caps = [c.strip() for c in capabilities.split(",") if c.strip()]
    agent_id, tx_result = client.register_agent(name, description, caps, agent_uri)

    payload = {
        "agentId": agent_id,
        "txHash": tx_result.tx_hash,
        "operatorWallet": client.operator_account.address,
        "agentWallet": client.agent_account.address,
    }
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    typer.echo(json.dumps(payload, indent=2))


@app.command("claim")
def claim(agent_id: int = typer.Option(..., envvar="AGENT_ID")) -> None:
    client = _client()
    tx_result = client.claim_allocation(agent_id)
    balance_wei = client.get_allocation_balance(agent_id)
    typer.echo(
        json.dumps(
            {
                "agentId": agent_id,
                "txHash": tx_result.tx_hash,
                "balanceWei": balance_wei,
                "balanceEth": str(client.w3.from_wei(balance_wei, "ether")),
            },
            indent=2,
        )
    )


@app.command("balance")
def balance(agent_id: int = typer.Option(..., envvar="AGENT_ID")) -> None:
    client = _client()
    has_claimed = client.has_claimed_allocation(agent_id)
    balance_wei = client.get_allocation_balance(agent_id)
    typer.echo(
        json.dumps(
            {
                "agentId": agent_id,
                "hasClaimed": has_claimed,
                "balanceWei": balance_wei,
                "balanceEth": str(client.w3.from_wei(balance_wei, "ether")),
            },
            indent=2,
        )
    )


@app.command("simulate-intent")
def simulate_intent(
    agent_id: int = typer.Option(..., envvar="AGENT_ID"),
    pair: str = typer.Option("XBTUSD"),
    action: str = typer.Option(...),
    amount_usd_scaled: int = typer.Option(...),
    max_slippage_bps: int = typer.Option(100),
    deadline_seconds: int = typer.Option(300),
) -> None:
    client = _client()
    intent = client.build_trade_intent(
        agent_id=agent_id,
        pair=pair,
        action=action,
        amount_usd_scaled=amount_usd_scaled,
        max_slippage_bps=max_slippage_bps,
        deadline=int(time.time()) + deadline_seconds,
    )
    valid, reason = client.simulate_intent(intent)
    typer.echo(json.dumps({"intent": intent, "valid": valid, "reason": reason}, indent=2))


@app.command("submit-intent")
def submit_intent(
    agent_id: int = typer.Option(..., envvar="AGENT_ID"),
    pair: str = typer.Option("XBTUSD"),
    action: str = typer.Option(...),
    amount_usd_scaled: int = typer.Option(...),
    max_slippage_bps: int = typer.Option(100),
    deadline_seconds: int = typer.Option(300),
    skip_simulation: bool = typer.Option(False),
    out_file: Path = typer.Option(Path("last-intent.json")),
) -> None:
    client = _client()
    intent = client.build_trade_intent(
        agent_id=agent_id,
        pair=pair,
        action=action,
        amount_usd_scaled=amount_usd_scaled,
        max_slippage_bps=max_slippage_bps,
        deadline=int(time.time()) + deadline_seconds,
    )

    if not skip_simulation:
        valid, reason = client.simulate_intent(intent)
        if not valid:
            raise typer.BadParameter(f"simulateIntent rejected: {reason}")

    signature = client.sign_trade_intent(intent)
    tx_result = client.submit_trade_intent(intent, signature)

    payload = {
        "intent": intent,
        "signature": signature.hex(),
        "txHash": tx_result.tx_hash,
    }
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    typer.echo(json.dumps(payload, indent=2))


@app.command("post-checkpoint")
def post_checkpoint(
    agent_id: int = typer.Option(..., envvar="AGENT_ID"),
    action: str = typer.Option(...),
    pair: str = typer.Option("XBTUSD"),
    amount_usd_scaled: int = typer.Option(...),
    price_usd_scaled: int = typer.Option(...),
    score: int = typer.Option(...),
    reasoning: str = typer.Option(...),
    notes: str = typer.Option(""),
    checkpoints_file: Path = typer.Option(Path("checkpoints.jsonl")),
) -> None:
    client = _client()

    checkpoint_hash, checkpoint = client.build_checkpoint_hash(
        agent_id=agent_id,
        action=action,
        pair=pair,
        amount_usd_scaled=amount_usd_scaled,
        price_usd_scaled=price_usd_scaled,
        reasoning=reasoning,
    )

    tx_result = client.post_checkpoint_attestation(
        agent_id=agent_id,
        checkpoint_hash=checkpoint_hash,
        score=score,
        notes=notes,
    )

    client.append_checkpoint_jsonl(
        log_file=checkpoints_file,
        checkpoint_hash=checkpoint_hash,
        checkpoint=checkpoint,
        score=score,
        notes=notes,
    )

    typer.echo(
        json.dumps(
            {
                "agentId": agent_id,
                "checkpointHash": checkpoint_hash,
                "txHash": tx_result.tx_hash,
                "checkpoint": checkpoint,
            },
            indent=2,
        )
    )


@app.command("scores")
def scores(agent_id: int = typer.Option(..., envvar="AGENT_ID")) -> None:
    client = _client()
    validation = client.get_validation_score(agent_id)
    reputation = client.get_reputation_score(agent_id)

    typer.echo(
        json.dumps(
            {
                "agentId": agent_id,
                "validationScore": validation,
                "reputationScore": reputation,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    app()
