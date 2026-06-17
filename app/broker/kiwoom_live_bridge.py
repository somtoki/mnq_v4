"""Skeleton bridge between future Kiwoom realtime ticks and live paper trading."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

try:
    from PyQt5.QAxContainer import QAxWidget  # type: ignore
    from PyQt5.QtWidgets import QApplication  # type: ignore
except ImportError:  # pragma: no cover - optional dependency for future integration only.
    QApplication = None
    QAxWidget = None

from app.broker.kiwoom_tick_adapter import KiwoomTickAdapter
from app.paper.live_paper_trader import LivePaperTrader
from app.realtime.live_bar_feed import LiveBarFeed


def build_sample_kiwoom_raw_ticks(symbol: str = "MNQ") -> List[Dict[str, object]]:
    """Builds sample raw ticks that cross multiple 15-minute boundaries."""

    return [
        {
            "symbol": symbol,
            "datetime": "2026-01-02T09:30:05",
            "current_price": "21000.25",
            "volume": "1",
        },
        {
            "symbol": symbol,
            "date": "20260102",
            "time": "094459",
            "current_price": "21002.50",
            "volume": "2",
        },
        {
            "code": symbol,
            "date": "20260102",
            "trade_time": "094501",
            "close": "21004.00",
            "qty": "1",
        },
        {
            "symbol_code": symbol,
            "date": "20260102",
            "time": "095959",
            "price": "21006.75",
            "contract_volume": "3",
        },
        {
            "symbol": symbol,
            "timestamp": "2026-01-02T10:00:01",
            "price": "21005.50",
            "volume": "2",
        },
    ]


class KiwoomLiveBridge:
    """Normalizes future Kiwoom ticks and forwards completed bars to paper trading."""

    def __init__(
        self,
        symbol: str = "MNQ",
        bar_minutes: int = 15,
        live_paper_trader: Optional[LivePaperTrader] = None,
        live_bar_feed: Optional[LiveBarFeed] = None,
        tick_adapter: Optional[KiwoomTickAdapter] = None,
    ) -> None:
        """Initializes bridge dependencies with paper-safe defaults."""

        self.symbol = symbol
        self.bar_minutes = bar_minutes
        self._project_root = Path(__file__).resolve().parents[2]
        self._tick_adapter = tick_adapter or KiwoomTickAdapter(symbol=symbol)
        self._live_bar_feed = live_bar_feed or LiveBarFeed(symbol=symbol, bar_minutes=bar_minutes)
        self._live_paper_trader = live_paper_trader or LivePaperTrader(
            project_root=self._project_root,
            symbol=symbol,
            bar_minutes=bar_minutes,
        )
        self._completed_bars_processed = 0
        self._last_tick = None  # type: Optional[Dict[str, object]]
        self._last_completed_bar = None  # type: Optional[Dict[str, object]]
        self._started = False
        self._qt_application_class = QApplication
        self._qax_widget_class = QAxWidget

    def start(self) -> None:
        """Starts the paper-safe bridge skeleton without opening Kiwoom."""

        self._started = True
        print(
            "KiwoomLiveBridge skeleton started for {0} {1}-minute bars (paper only, no Kiwoom connection)".format(
                self.symbol,
                self.bar_minutes,
            )
        )

    def stop(self) -> None:
        """Stops the bridge skeleton."""

        self._started = False
        print("KiwoomLiveBridge skeleton stopped")

    def on_raw_tick(self, raw_tick: Dict[str, object]) -> int:
        """Normalizes one raw tick, ingests it, and processes completed bars."""

        normalized_tick = self._tick_adapter.normalize(raw_tick)
        self._last_tick = dict(normalized_tick)
        processed_count = 0
        completed_bars = self._live_bar_feed.ingest_tick(normalized_tick)
        for bar in completed_bars:
            self._live_paper_trader.process_completed_bar(bar)
            self._completed_bars_processed += 1
            processed_count += 1
            self._last_completed_bar = dict(bar)
        return processed_count

    def get_status(self) -> Dict[str, object]:
        """Returns a bridge status snapshot suitable for manual verification."""

        return {
            "symbol": self.symbol,
            "bar_minutes": self.bar_minutes,
            "completed_bars_processed": self._completed_bars_processed,
            "last_tick": None if self._last_tick is None else dict(self._last_tick),
            "last_completed_bar": (
                None if self._last_completed_bar is None else dict(self._last_completed_bar)
            ),
            "final_position": self._live_paper_trader.get_open_position(),
            "realized_pnl": self._live_paper_trader.get_realized_pnl(),
            "pending_orders": self._live_paper_trader.get_pending_orders(),
        }
