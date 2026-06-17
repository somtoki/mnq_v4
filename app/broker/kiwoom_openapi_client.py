"""Optional Kiwoom OpenAPI client skeleton for live paper trading only."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from PyQt5.QAxContainer import QAxWidget  # type: ignore
    from PyQt5.QtCore import QEventLoop, QTimer  # type: ignore
    from PyQt5.QtWidgets import QApplication  # type: ignore
except ImportError:  # pragma: no cover - optional dependency for future integration only.
    QApplication = None
    QAxWidget = None
    QEventLoop = None
    QTimer = None

from app.broker.kiwoom_live_bridge import KiwoomLiveBridge


def build_sample_fid_payloads(symbol: str = "MNQ") -> List[Dict[str, object]]:
    """Builds fake FID dictionaries that cross multiple 15-minute boundaries."""

    return [
        {
            "symbol": symbol,
            "current_price": "21010.25",
            "volume": "1",
            "trade_date": "20260102",
            "trade_time": "093005",
        },
        {
            "symbol": symbol,
            "current_price": "21013.00",
            "volume": "2",
            "trade_date": "20260102",
            "trade_time": "094459",
        },
        {
            "symbol": symbol,
            "current_price": "21015.50",
            "volume": "1",
            "trade_date": "20260102",
            "trade_time": "094501",
        },
        {
            "symbol": symbol,
            "current_price": "21018.25",
            "volume": "3",
            "trade_date": "20260102",
            "trade_time": "095959",
        },
        {
            "symbol": symbol,
            "current_price": "21017.75",
            "volume": "2",
            "trade_date": "20260102",
            "trade_time": "100001",
        },
    ]


class KiwoomOpenApiClient:
    """PyQt/QAxWidget-based Kiwoom client skeleton with paper-only safeguards."""

    def __init__(self, bridge: KiwoomLiveBridge, symbol: str = "MNQ") -> None:
        """Stores the target bridge and optional Kiwoom runtime handles."""

        self._bridge = bridge
        self._symbol = symbol
        self._qt_application = None  # type: Optional[QApplication]
        self._control = None  # type: Optional[QAxWidget]
        self._events_connected = False
        self._registered_symbols = set()  # type: set[str]
        self._login_event_loop = None  # type: Optional[QEventLoop]
        self._login_error_code = None  # type: Optional[int]
        self._login_completed = False
        self.discovery_mode = False
        self.fid_log_path = Path(__file__).resolve().parents[2] / "data" / "live" / "kiwoom_fid_discovery.csv"
        self.candidate_fids = self._build_default_candidate_fids()

    def is_available(self) -> bool:
        """Returns whether PyQt5 and QAxContainer are available in this environment."""

        return QApplication is not None and QAxWidget is not None

    def login(self) -> None:
        """Runs CommConnect and waits for the OnEventConnect result."""

        if not self.is_available():
            raise RuntimeError(
                "PyQt5/QAxContainer is not available. Kiwoom OpenAPI login skeleton cannot start."
            )
        if QEventLoop is None:
            raise RuntimeError("PyQt5.QtCore.QEventLoop is not available for Kiwoom login.")

        if self._qt_application is None:
            self._qt_application = QApplication.instance() or QApplication([])
        if self._control is None:
            self._control = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        if self._control is None:
            raise RuntimeError("Kiwoom OpenAPI control could not be initialized.")
        self._bind_login_event()
        self._login_error_code = None
        self._login_completed = False
        self._login_event_loop = QEventLoop()
        result = self._control.dynamicCall("CommConnect()")
        if result not in (0, None):
            self._login_event_loop = None
            raise RuntimeError("CommConnect() failed to start. Return value: {0}".format(result))

        print("KiwoomOpenApiClient CommConnect requested")
        self._login_event_loop.exec_()
        self._login_event_loop = None

        if not self._login_completed:
            raise RuntimeError("Kiwoom login did not complete.")
        if self._login_error_code != 0:
            raise RuntimeError(
                "Kiwoom login failed with error code: {0}".format(self._login_error_code)
            )

        print("KiwoomOpenApiClient login completed successfully")

    def connect_events(self) -> None:
        """Binds optional OpenAPI events when the control is available."""

        if not self.is_available():
            print("KiwoomOpenApiClient event binding skipped because PyQt/QAx is unavailable")
            return
        if self._control is None:
            raise RuntimeError("Kiwoom control is not initialized. Call login() first.")

        self._bind_login_event()
        if not self._events_connected and hasattr(self._control, "OnReceiveRealData"):
            self._control.OnReceiveRealData.connect(self.on_receive_real_data)
            self._events_connected = True
        print("KiwoomOpenApiClient event binding skeleton connected")

    def register_realtime(self, symbol: str) -> None:
        """Prints intended realtime registration without requiring a live login."""

        self._registered_symbols.add(symbol)
        print(
            "KiwoomOpenApiClient realtime registration is not finalized for symbol: {0}".format(
                symbol
            )
        )
        print("KiwoomOpenApiClient SetRealReg format/FID mapping is still pending discovery")

    def get_qt_application(self) -> Optional[QApplication]:
        """Returns the cached QApplication instance when available."""

        return self._qt_application

    def has_qt_timer(self) -> bool:
        """Returns whether QTimer is importable for timed runner shutdown."""

        return QTimer is not None

    def schedule_stop(self, duration_minutes: float, stop_callback: Any) -> None:
        """Schedules a stop callback using QTimer when PyQt is available."""

        if QTimer is None:
            raise RuntimeError("PyQt5.QtCore.QTimer is not available for timed shutdown.")
        milliseconds = max(int(duration_minutes * 60 * 1000), 0)
        QTimer.singleShot(milliseconds, stop_callback)

    def unregister_realtime(self, symbol: str) -> None:
        """Prints intended realtime unregistration."""

        self._registered_symbols.discard(symbol)
        print(
            "KiwoomOpenApiClient skeleton would unregister realtime for symbol: {0}".format(symbol)
        )

    def start(self) -> None:
        """Runs the paper-safe startup skeleton."""

        self.login()
        self.connect_events()
        self.register_realtime(self._symbol)

    def stop(self) -> None:
        """Runs the paper-safe shutdown skeleton."""

        self.unregister_realtime(self._symbol)

    def on_receive_real_data(self, code: str, real_type: str, real_data: str) -> int:
        """Collects candidate FIDs, optionally logs them, and forwards a valid raw tick."""

        fid_values = self.extract_candidate_fids(code=code, real_type=real_type)
        fid_values["symbol"] = code or self._symbol
        fid_values["real_type"] = real_type
        fid_values["real_data"] = real_data

        if self.discovery_mode:
            self.log_fid_snapshot(code=code or self._symbol, real_type=real_type, fid_values=fid_values)

        try:
            raw_tick = self.build_raw_tick_from_fids(code=code or self._symbol, fid_values=fid_values)
        except ValueError as error:
            print("KiwoomOpenApiClient warning: unable to build raw tick from FIDs ({0})".format(error))
            return 0
        return self._bridge.on_raw_tick(raw_tick)

    def enable_discovery_mode(
        self,
        fid_log_path: Optional[str] = None,
        candidate_fids: Optional[List[str]] = None,
    ) -> Path:
        """Enables CSV logging for incoming realtime FID snapshots."""

        self.discovery_mode = True
        if fid_log_path:
            self.fid_log_path = Path(fid_log_path)
            if not self.fid_log_path.is_absolute():
                self.fid_log_path = Path(__file__).resolve().parents[2] / self.fid_log_path
        if candidate_fids:
            self.candidate_fids = self._normalize_candidate_fids(candidate_fids)
        self.fid_log_path.parent.mkdir(parents=True, exist_ok=True)
        return self.fid_log_path

    def log_fid_snapshot(self, code: str, real_type: str, fid_values: Dict[str, object]) -> None:
        """Appends one realtime FID snapshot row to the discovery CSV."""

        self.fid_log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "received_at": datetime.now().replace(microsecond=0).isoformat(),
            "code": code,
            "real_type": real_type,
            "fid_values_json": json.dumps(fid_values, ensure_ascii=True, sort_keys=True),
        }
        write_header = not self.fid_log_path.exists()
        with self.fid_log_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["received_at", "code", "real_type", "fid_values_json"],
            )
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    def extract_candidate_fids(
        self,
        code: str,
        real_type: str,
        fid_values: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        """Extracts candidate FIDs from Kiwoom when available or returns injected dry-run values."""

        if fid_values is not None:
            extracted = dict(fid_values)
            extracted.setdefault("symbol", code or self._symbol)
            extracted.setdefault("real_type", real_type)
            return extracted

        extracted = {
            "symbol": code or self._symbol,
            "real_type": real_type,
        }
        if self._control is not None:
            for fid in self.candidate_fids:
                try:
                    value = self._control.dynamicCall("GetCommRealData(QString, int)", code, int(fid))
                except Exception:
                    value = ""
                extracted[str(fid)] = value

        extracted.setdefault("trade_date", datetime.now().strftime("%Y%m%d"))
        extracted.setdefault("trade_time", datetime.now().strftime("%H%M%S"))
        extracted.setdefault("current_price", extracted.get("10", ""))
        extracted.setdefault("volume", extracted.get("15", ""))
        return extracted

    def build_raw_tick_from_fids(self, code: str, fid_values: Dict[str, object]) -> Dict[str, object]:
        """Maps a future overseas futures FID snapshot into the raw bridge tick format."""

        current_price = fid_values.get("current_price", fid_values.get("price", fid_values.get("10", "")))
        volume = fid_values.get("volume", fid_values.get("qty", fid_values.get("15", "")))
        trade_date = fid_values.get("trade_date", fid_values.get("date", ""))
        trade_time = fid_values.get("trade_time", fid_values.get("time", fid_values.get("20", "")))
        if not current_price:
            raise ValueError("missing current_price candidate")
        if not trade_time and "timestamp" not in fid_values:
            raise ValueError("missing trade_time candidate")

        symbol = str(fid_values.get("symbol") or code or self._symbol)
        raw_tick = {
            "symbol": symbol,
            "date": str(trade_date or datetime.now().strftime("%Y%m%d")),
            "time": str(trade_time or datetime.now().strftime("%H%M%S")),
            "current_price": current_price,
            "volume": volume,
        }
        if "timestamp" in fid_values:
            raw_tick["timestamp"] = fid_values["timestamp"]
        return raw_tick

    def send_order(self, *args: Any, **kwargs: Any) -> None:
        """Explicitly blocks real order placement in this client."""

        raise RuntimeError("Real orders are disabled in this paper trading client.")

    def is_logged_in(self) -> bool:
        """Returns whether the last login callback completed successfully."""

        return self._login_completed and self._login_error_code == 0

    def _build_default_candidate_fids(self) -> List[str]:
        """Returns placeholder realtime FID candidates for discovery mode."""

        return self._normalize_candidate_fids(
            [
                "20",
                "10",
                "15",
                "21",
                "22",
                "27",
                "28",
            ]
        )

    def _normalize_candidate_fids(self, candidate_fids: List[str]) -> List[str]:
        """Normalizes candidate FIDs to a stable string list without duplicates."""

        normalized = []  # type: List[str]
        seen = set()
        for fid in candidate_fids:
            normalized_fid = str(fid).strip()
            if not normalized_fid or normalized_fid in seen:
                continue
            seen.add(normalized_fid)
            normalized.append(normalized_fid)
        return normalized

    def _bind_login_event(self) -> None:
        """Binds the Kiwoom login callback once when available."""

        if self._control is None or not hasattr(self._control, "OnEventConnect"):
            return
        if getattr(self, "_login_event_bound", False):
            return
        self._control.OnEventConnect.connect(self._on_event_connect)
        self._login_event_bound = True

    def _on_event_connect(self, error_code: int) -> None:
        """Handles the asynchronous Kiwoom login result."""

        self._login_error_code = int(error_code)
        self._login_completed = True
        print("KiwoomOpenApiClient OnEventConnect received: {0}".format(self._login_error_code))
        if self._login_event_loop is not None and self._login_event_loop.isRunning():
            self._login_event_loop.quit()
