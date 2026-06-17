"""Runner for Kiwoom realtime FID discovery logging in paper-only mode."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.broker.kiwoom_live_bridge import KiwoomLiveBridge
from app.broker.kiwoom_openapi_client import KiwoomOpenApiClient


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments for the Kiwoom FID discovery runner."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="MNQ", help="Target symbol for discovery.")
    parser.add_argument("--bar-minutes", type=int, default=15, help="Bridge bar size in minutes.")
    parser.add_argument(
        "--log-path",
        type=str,
        default="data/live/kiwoom_fid_discovery.csv",
        help="CSV path for realtime FID discovery logs.",
    )
    parser.add_argument(
        "--duration-minutes",
        type=float,
        default=0,
        help="Run duration in minutes. Use 0 to run until manually stopped.",
    )
    return parser.parse_args()


def main() -> int:
    """Runs Kiwoom realtime FID discovery mode with safe failure handling."""

    args = parse_args()
    bridge = KiwoomLiveBridge(symbol=args.symbol, bar_minutes=args.bar_minutes)
    client = KiwoomOpenApiClient(bridge=bridge, symbol=args.symbol)
    log_path = client.enable_discovery_mode(fid_log_path=args.log_path)

    print("Kiwoom FID Discovery Started")
    print("Symbol: {0}".format(args.symbol))
    print("Log path: {0}".format(log_path))
    print("Paper trading only. Real orders disabled.")

    if not client.is_available():
        print("Kiwoom FID discovery failed: PyQt5/QAxContainer is not available in this environment.")
        return 1

    try:
        bridge.start()
        client.login()
        client.connect_events()
        client.register_realtime(args.symbol)
    except Exception as error:
        print("Kiwoom FID discovery failed: {0}".format(error))
        try:
            client.stop()
        except Exception:
            pass
        bridge.stop()
        return 1

    app = client.get_qt_application()
    if app is None:
        print("Kiwoom FID discovery failed: QApplication was not initialized.")
        client.stop()
        bridge.stop()
        return 1

    def stop_runner() -> None:
        """Stops realtime discovery safely."""

        client.stop()
        bridge.stop()
        app.quit()

    if args.duration_minutes > 0:
        try:
            client.schedule_stop(args.duration_minutes, stop_runner)
        except Exception as error:
            print("Kiwoom FID discovery failed: {0}".format(error))
            stop_runner()
            return 1

    try:
        return int(app.exec_())
    except KeyboardInterrupt:
        stop_runner()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
