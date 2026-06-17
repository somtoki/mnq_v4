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

## Kiwoom OpenAPI Client Role

`app/broker/kiwoom_openapi_client.py` is the optional PyQt/QAxWidget-facing wrapper that can later own Kiwoom login, event wiring, and overseas futures realtime subscriptions.

Current client responsibilities:

- Detect whether `PyQt5` and `QAxContainer` are available
- Hold the future `QApplication` and `QAxWidget` control handles
- Bind a skeleton realtime callback
- Build a raw tick from placeholder overseas futures FID values
- Forward the raw tick into `KiwoomLiveBridge.on_raw_tick(raw_tick)`

Safety constraints:

- No real orders
- No account trading implementation
- Any placeholder order method must raise: `Real orders are disabled in this paper trading client.`

## FID Discovery Workflow

Use discovery mode before mapping actual overseas futures realtime fields into the strategy pipeline.

1. Enable discovery mode on `KiwoomOpenApiClient`.
2. Register a candidate FID list such as time, current price, and volume candidates.
3. For each realtime event, collect available candidate FID values.
4. Append the event snapshot to `data/live/kiwoom_fid_discovery.csv` or a test CSV path.
5. Inspect the CSV to identify which real FIDs consistently contain trade time, last price, and volume for the overseas futures feed.

The current CSV format stores one row per realtime event with:

- `received_at`
- `code`
- `real_type`
- `fid_values_json`

Use the logged JSON field to compare candidate FID values across repeated events during market hours until the true overseas futures mapping is clear.

## Running Real FID Discovery

Use `run_kiwoom_fid_discovery.py` when you are ready to log real Kiwoom realtime events during market hours.

For MNQ and similar overseas futures workflows, the default API kind is `overseas_futures`, which selects `KFOPENAPI.KFOpenAPICtrl.1`.

If you need the domestic stock control instead, use the domestic fallback, which selects `KHOPENAPI.KHOpenAPICtrl.1`.

If the installed environment exposes a different COM control, override it directly with `--prog-id`.

Example:

`C:\Users\Cham\AppData\Local\Programs\Python\Python39-32\python.exe .\run_kiwoom_fid_discovery.py --symbol MNQ --log-path data/live/kiwoom_fid_discovery.csv`

You can also override the discovery registration inputs:

`C:\Users\Cham\AppData\Local\Programs\Python\Python39-32\python.exe .\run_kiwoom_fid_discovery.py --symbol MNQ --screen-no 9001 --realtime-fids 20;10;15 --duration-minutes 1`

Expected output file:

- `data/live/kiwoom_fid_discovery.csv`

Safe stop behavior:

- If `--duration-minutes 0` is used, the runner continues until manually stopped.
- Press `Ctrl+C` to stop safely.
- If `--duration-minutes` is greater than zero, the runner stops automatically after the requested duration.

Safety reminder:

- Paper trading only
- No real orders
- `send_order()` remains disabled
- Realtime registration is discovery-only and should only be used to log candidate FIDs

## Analyzing FID Discovery Logs

After collecting `data/live/kiwoom_fid_discovery.csv`, run:

`C:\Users\Cham\AppData\Local\Programs\Python\Python39-32\python.exe app/research/analyze_kiwoom_fid_log.py --input data/live/kiwoom_fid_discovery.csv`

The analyzer writes results to `reports/kiwoom_fid_analysis` by default.

Inspect these files first:

- `candidate_time_fields.csv`
- `candidate_price_fields.csv`
- `candidate_volume_fields.csv`
- `summary.md`

Use `fid_summary.csv` when you need the full field-by-field statistics, including sample values, numeric parse rate, changed count, and monotonic-like score.

## HeroMoonG / Overseas Futures API Discovery

Use `app/research/discover_kiwoom_overseas_api.py` to detect which Kiwoom COM ProgIDs are installed on the current PC before assuming the domestic stock API control is the right one.

This matters because domestic stock OpenAPI and overseas futures / HeroMoonG environments may expose different COM controls and different realtime behavior.

The next step should depend on the detected ProgID:

- If an overseas futures-like `KF...` ProgID is detected, prioritize that control for login and realtime discovery work.
- If only `KH...` ProgIDs are detected, verify whether the installed environment actually supports overseas futures through that control before wiring more logic.

## Next Steps For Real Kiwoom OpenAPI Connection

1. Add an optional Kiwoom API client wrapper that owns `QApplication`, `QAxWidget`, login state, and signal-slot wiring.
2. Subscribe to the overseas futures realtime event for the target symbol and map relevant FIDs into a raw tick payload.
3. Call `KiwoomLiveBridge.on_raw_tick(raw_tick)` from the realtime event callback.
4. Decide whether timestamps should use exchange time, local machine time, or a broker-provided trading date plus trade time combination.
5. Add reconnect, duplicate-event filtering, session-state handling, and structured logging around realtime callbacks.
6. Keep order placement out of this path until the paper runtime is fully validated against live incoming ticks.

## Next Step For Real Overseas Futures FID Mapping

After confirming the actual Kiwoom overseas futures realtime field list, map the real FIDs for symbol, trade date, trade time, last price, and volume into `KiwoomOpenApiClient.build_raw_tick_from_fids()`, then validate that the resulting raw tick is accepted by `KiwoomLiveBridge` unchanged in paper mode.

## Warning

Paper trading only. No real orders should be sent from this bridge in its current or intended near-term form.
