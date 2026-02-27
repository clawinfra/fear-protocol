"""StateManager — load/save/query executor state."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fear_protocol.state.models import ExecutorState


DEFAULT_STATE_DIR = Path.home() / ".fear-protocol" / "state"


class StateManager:
    """
    Manages persistent executor state across sessions.

    Backwards-compatible with FearHarvester executor_state.json.
    Supports multiple exchanges/modes via separate state files.
    """

    def __init__(
        self,
        state_dir: Path = DEFAULT_STATE_DIR,
        exchange: str = "paper",
        mode: str = "paper",
        strategy: str = "fear-greed-dca",
    ) -> None:
        """
        Initialize the state manager.

        Args:
            state_dir: Directory to store state files.
            exchange: Exchange name for state file scoping.
            mode: Trading mode (paper/live).
            strategy: Strategy name.
        """
        self.state_dir = state_dir
        self.exchange = exchange
        self.mode = mode
        self.strategy = strategy
        self.state_dir.mkdir(parents=True, exist_ok=True)

    @property
    def state_file(self) -> Path:
        """Path to the current state file."""
        if self.mode == "live":
            return self.state_dir / f"{self.exchange}_live_state.json"
        return self.state_dir / f"{self.exchange}_paper_state.json"

    def load(self) -> ExecutorState:
        """
        Load state from disk.

        Returns:
            ExecutorState, or fresh state if file doesn't exist.
        """
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            state = ExecutorState.from_dict(data)
            state.exchange = self.exchange
            state.mode = self.mode
            state.strategy = self.strategy
            return state
        return ExecutorState(
            exchange=self.exchange,
            mode=self.mode,
            strategy=self.strategy,
        )

    def save(self, state: ExecutorState) -> None:
        """
        Save state to disk.

        Args:
            state: ExecutorState to persist.
        """
        self.state_file.write_text(json.dumps(state.to_dict(), indent=2))

    def add_position(
        self,
        state: ExecutorState,
        position: dict[str, Any],
    ) -> ExecutorState:
        """
        Add a new position to state and persist.

        Args:
            state: Current executor state.
            position: Position dict to add.

        Returns:
            Updated ExecutorState.
        """
        state.positions.append(position)
        state.total_invested += float(position.get("usd_amount", 0))
        self.save(state)
        return state

    def close_positions(
        self,
        state: ExecutorState,
        position_indices: list[int],
        exit_price: float,
        exit_timestamp: str,
    ) -> ExecutorState:
        """
        Mark positions as closed.

        Args:
            state: Current executor state.
            position_indices: Indices into state.positions to close.
            exit_price: Exit price for P&L calculation.
            exit_timestamp: ISO timestamp of exit.

        Returns:
            Updated ExecutorState.
        """
        for i in position_indices:
            pos = state.positions[i]
            pos["status"] = "closed"
            pos["exit_price"] = exit_price
            pos["exit_timestamp"] = exit_timestamp
            entry_price = pos.get("entry_price", exit_price)
            pos["pnl_pct"] = (exit_price - entry_price) / entry_price * 100
            state.total_invested -= float(pos.get("usd_amount", 0))
        self.save(state)
        return state

    def get_summary(self, state: ExecutorState, current_price: float) -> dict[str, Any]:
        """
        Build a position summary.

        Args:
            state: Current executor state.
            current_price: Current asset price for P&L calculation.

        Returns:
            Summary dict with counts, P&L, etc.
        """
        open_positions = state.open_positions
        closed_positions = [p for p in state.positions if p.get("status") == "closed"]

        total_base = sum(float(p.get("btc_qty", 0)) for p in open_positions)
        total_cost = sum(float(p.get("usd_amount", 0)) for p in open_positions)
        current_value = total_base * current_price
        unrealized_pnl = current_value - total_cost
        unrealized_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0
        avg_entry = (total_cost / total_base) if total_base > 0 else 0.0

        realized_pnl = sum(
            float(p.get("btc_qty", 0))
            * (float(p.get("exit_price", 0)) - float(p.get("entry_price", 0)))
            for p in closed_positions
        )

        return {
            "open_count": len(open_positions),
            "closed_count": len(closed_positions),
            "total_base": total_base,
            "avg_entry_price": avg_entry,
            "total_cost": total_cost,
            "current_value": current_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pct,
            "realized_pnl": realized_pnl,
            "total_invested": state.total_invested,
            "last_action": state.last_action,
            "mode": state.mode,
            "exchange": state.exchange,
        }
