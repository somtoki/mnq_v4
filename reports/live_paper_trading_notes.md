# Live Paper Trading Notes

## Scope

This runtime is paper trading only. It does not place real orders, does not connect to a real account, and the Kiwoom live bridge currently stops at normalization plus completed-bar delivery.

## Live Paper Trading Flow

1. A market data source emits raw ticks for `MNQ`.
2. `KiwoomLiveBridge.on_raw_tick()` receives each raw tick payload.
3. `KiwoomTickAdapter.normalize()` converts the broker-specific payload into the internal tick format:
   - `symbol`
   - `timestamp`
   - `price`
   - `volume`
4. `LiveBarFeed.ingest_tick()` aggregates normalized ticks into 15-minute OHLCV bars.
5. Each completed bar is forwarded to `LivePaperTrader.process_completed_bar(bar)`.
6. `LivePaperTrader` runs the paper-only signal, pending-order, fill, and logging pipeline.

## Tick Normalization Point

The normalization boundary is `app/broker/kiwoom_tick_adapter.py`.

`KiwoomLiveBridge` should remain thin: it accepts raw Kiwoom event payloads, normalizes them once, and forwards normalized ticks downstream. This keeps broker-specific FID parsing separate from strategy and paper execution logic.

## Kiwoom Bridge Role

`app/broker/kiwoom_live_bridge.py` is the future integration seam between Kiwoom OpenAPI realtime events and the existing live paper trading runtime.

Current bridge responsibilities:

- Hold or create `KiwoomTickAdapter`, `LiveBarFeed`, and `LivePaperTrader`
- Accept raw Kiwoom-style tick payloads
- Normalize raw ticks into internal tick dictionaries
- Push normalized ticks into `LiveBarFeed`
- Forward completed 15-minute bars into `LivePaperTrader`
- Expose status for dry runs and manual validation

Current non-responsibilities:

- No Kiwoom login
- No PyQt event loop startup
- No real order routing
- No real account trading

## Next Steps For Real Kiwoom OpenAPI Connection

1. Add an optional Kiwoom API client wrapper that owns `QApplication`, `QAxWidget`, login state, and signal-slot wiring.
2. Subscribe to the overseas futures realtime event for the target symbol and map relevant FIDs into a raw tick payload.
3. Call `KiwoomLiveBridge.on_raw_tick(raw_tick)` from the realtime event callback.
4. Decide whether timestamps should use exchange time, local machine time, or a broker-provided trading date plus trade time combination.
5. Add reconnect, duplicate-event filtering, session-state handling, and structured logging around realtime callbacks.
6. Keep order placement out of this path until the paper runtime is fully validated against live incoming ticks.

## Warning

Paper trading only. No real orders should be sent from this bridge in its current or intended near-term form.
