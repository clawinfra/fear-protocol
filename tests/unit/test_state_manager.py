"""Tests for the StateManager."""
from __future__ import annotations

import pytest

from fear_protocol.state.manager import StateManager
from fear_protocol.state.models import ExecutorState


class TestStateManager:
    def test_load_fresh_state(self, tmp_path) -> None:
        mgr = StateManager(state_dir=tmp_path, exchange="mock", mode="paper")
        state = mgr.load()
        assert state.exchange == "mock"
        assert state.mode == "paper"
        assert state.positions == []
        assert state.total_invested == 0.0

    def test_save_and_load(self, tmp_path) -> None:
        mgr = StateManager(state_dir=tmp_path, exchange="mock", mode="paper")
        state = mgr.load()
        state.total_invested = 1000.0
        state.last_action = "DCA_BUY $500"
        mgr.save(state)

        state2 = mgr.load()
        assert state2.total_invested == 1000.0
        assert state2.last_action == "DCA_BUY $500"

    def test_add_position(self, tmp_path) -> None:
        mgr = StateManager(state_dir=tmp_path, exchange="mock", mode="paper")
        state = mgr.load()
        position = {
            "timestamp": "2023-01-01T12:00:00",
            "entry_price": 20000.0,
            "btc_qty": 0.025,
            "usd_amount": 500.0,
            "fg_at_entry": 15,
            "status": "open",
            "mode": "paper",
        }
        state = mgr.add_position(state, position)
        assert len(state.positions) == 1
        assert state.total_invested == 500.0

        # Reload and verify
        state2 = mgr.load()
        assert len(state2.positions) == 1

    def test_close_positions(self, tmp_path) -> None:
        mgr = StateManager(state_dir=tmp_path, exchange="mock", mode="paper")
        state = mgr.load()
        position = {
            "timestamp": "2023-01-01T12:00:00",
            "entry_price": 20000.0,
            "btc_qty": 0.025,
            "usd_amount": 500.0,
            "fg_at_entry": 15,
            "status": "open",
            "mode": "paper",
        }
        state = mgr.add_position(state, position)
        state = mgr.close_positions(state, [0], 25000.0, "2023-05-01T12:00:00")

        assert state.positions[0]["status"] == "closed"
        assert state.positions[0]["exit_price"] == 25000.0
        assert state.positions[0]["pnl_pct"] == pytest.approx(25.0)
        assert state.total_invested == 0.0

    def test_get_summary(self, tmp_path) -> None:
        mgr = StateManager(state_dir=tmp_path, exchange="mock", mode="paper")
        state = mgr.load()
        state.positions = [
            {
                "timestamp": "2023-01-01",
                "entry_price": 20000.0,
                "btc_qty": 0.025,
                "usd_amount": 500.0,
                "fg_at_entry": 15,
                "status": "open",
                "mode": "paper",
            }
        ]
        state.total_invested = 500.0
        summary = mgr.get_summary(state, 25000.0)
        assert summary["open_count"] == 1
        assert summary["total_base"] == 0.025
        assert summary["current_value"] == pytest.approx(625.0)
        assert summary["unrealized_pnl"] == pytest.approx(125.0)

    def test_live_vs_paper_state_files(self, tmp_path) -> None:
        mgr_paper = StateManager(state_dir=tmp_path, exchange="hl", mode="paper")
        mgr_live = StateManager(state_dir=tmp_path, exchange="hl", mode="live")
        assert mgr_paper.state_file != mgr_live.state_file


class TestExecutorState:
    def test_to_dict_from_dict(self) -> None:
        state = ExecutorState(
            exchange="hyperliquid",
            mode="live",
            total_invested=2500.0,
            last_action="DCA_BUY",
        )
        d = state.to_dict()
        state2 = ExecutorState.from_dict(d)
        assert state2.exchange == state.exchange
        assert state2.total_invested == state.total_invested

    def test_open_positions_filter(self) -> None:
        state = ExecutorState(
            positions=[
                {"status": "open", "btc_qty": 0.1},
                {"status": "closed", "btc_qty": 0.2},
                {"status": "open", "btc_qty": 0.05},
            ]
        )
        assert len(state.open_positions) == 2

    def test_total_invested_decimal(self) -> None:
        state = ExecutorState(total_invested=1500.5)
        from decimal import Decimal
        assert state.total_invested_decimal == Decimal("1500.5")
