# V4 Migration Notes

## Existing V4-related files

- `C:\Users\Cham\OneDrive\Desktop\autotrade\mnq_research\app\strategies\turtle_strategy_v4.py`
  - V4 wrapper. V3에 `blocked_entry_hours={15,16,17}`만 추가한다.
- `C:\Users\Cham\OneDrive\Desktop\autotrade\mnq_research\app\strategies\turtle_strategy_v3.py`
  - Canonical V3 definition. 실제 V4의 대부분 규칙은 여기서 `run_turtle_strategy_v2()` 인자를 고정하는 방식으로 결정된다.
- `C:\Users\Cham\OneDrive\Desktop\autotrade\mnq_research\app\strategies\turtle_strategy_v2.py`
  - 실제 진입/청산/체결/ATR stop/one-position-at-a-time 백테스트 로직이 들어있는 핵심 구현체.
- `C:\Users\Cham\OneDrive\Desktop\autotrade\mnq_research\app\indicators\turtle.py`
  - Donchian channel, exit channel, midline, ATR, MA 계열 지표 생성.
- `C:\Users\Cham\OneDrive\Desktop\autotrade\mnq_research\app\research\run_turtle_v4_mnq_15m.py`
  - 15분봉 MNQ 데이터에 V4를 실행하고 결과를 저장하는 진입점.
- `C:\Users\Cham\OneDrive\Desktop\autotrade\mnq_research\app\backtest\engine.py`
  - 전략 함수를 데이터프레임 전체에 적용하는 최소 실행 래퍼.
- `C:\Users\Cham\OneDrive\Desktop\autotrade\mnq_research\app\backtest\performance.py`
  - summary/equity curve 계산.
- `C:\Users\Cham\OneDrive\Desktop\autotrade\mnq_research\app\data\data_store.py`
  - `15min.csv` 로더. 헤더 없는 MNQ 15분봉 원본을 정규 컬럼으로 읽는다.

## Role of each file

- `turtle_strategy_v4.py`
  - 전략 버전 식별자 역할. V4 고유 규칙은 “15,16,17시 신규진입 금지”뿐이다.
- `turtle_strategy_v3.py`
  - V4가 의존하는 실제 규칙 세트 정의.
  - stop, entry mode, exit mode, MA filter type, MA500 slope tolerance, long channel width 예외 규칙이 이 파일에 고정되어 있다.
- `turtle_strategy_v2.py`
  - 상태 머신 역할.
  - bar-by-bar 평가, next-bar-open fill, ATR stop, opposite_10 exit, blocked entry hour 처리, position overlap 방지까지 모두 여기에 있다.
- `indicators/turtle.py`
  - 전략이 기대하는 입력 컬럼 스펙 정의서에 가깝다.
- `run_turtle_v4_mnq_15m.py`
  - 연구 환경에서 실제로 어떤 데이터와 파라미터 조합이 V4인지 보여준다.

## V4 strategy logic summary

### Data timeframe

- 기준 데이터는 `data/raw/15min.csv`
- 즉, V4 연구 기준은 MNQ 15분봉이다.

### Indicator settings

- Donchian entry window: `30`
- Donchian exit window: `10`
- ATR window: `20`
- Trend MA window: `500`
- 추가 계산 컬럼:
  - `rolling_high_20`, `rolling_low_20`는 이름은 20이지만 실제 window 인자는 30으로 주입될 수 있다.
  - V4 실행에서는 `entry_window=30`, `exit_window=10`, `trend_ma_window=500`로 사용된다.
  - `ma200` 컬럼은 사실상 trend MA 컬럼이며, V4에서는 MA500 역할로 사용된다.

### Entry conditions

V4는 V3를 그대로 사용한다. 실제 롱/숏 조건은 다음과 같다.

- 공통
  - 현재 포지션이 없을 때만 신규진입 가능
  - breakout은 현재 봉 `close` 기준으로 판정
  - 실제 체결은 다음 봉 `open`
- Long breakout
  - `close > rolling_high_20`
  - `allow_long=True`
  - long MA filter 통과
  - MA55 cross 필터는 V4에서 비활성
  - MA2000 position 필터는 V4에서 비활성
  - long MA500 distance 필터는 V4에서 비활성
- Short breakout
  - `close < rolling_low_20`
  - `allow_short=True`
  - short MA filter 통과

### MA500 filter behavior

V4의 핵심은 `ma_filter="long_channel_width_slope"` 이다.

- Long side
  - channel width ATR = `(rolling_high_20 - rolling_low_20) / atr20`
  - width `<= 3 ATR` 이면 long은 MA500 무시
  - width `< 5 ATR` 이면 long은 `ma500_slope >= -0.5` 허용
  - width `>= 5 ATR` 이면 long은 MA500 상승 필요 (`ma200 > ma200_previous`)
- Short side
  - short는 예외 없이 MA500 하락 필요 (`ma200 < ma200_previous`)

### Exit conditions

- exit mode는 `opposite_10`
- Long exit
  - `close < rolling_low_10`
- Short exit
  - `close > rolling_high_10`
- ATR stop도 항상 활성
  - 초기 stop only, `2.0 * atr_at_entry`
- slope weakening, MA cross exit 등은 V4에서 비활성
- trailing stop은 별도로 없다

### ATR usage

- `atr20` 사용
- entry 시점 ATR을 고정해 initial stop 계산
- ATR stop offset = `2.0 * atr_at_entry`

### Blocked entry hours

- V4 고유 규칙: `15, 16, 17`시 신규진입 금지
- legacy 백테스트에서는 signal bar 시간이 아니라 체결될 `next_bar["datetime"].hour` 기준이다.
- `mnq_v4`에서는 이 규칙을 strategy layer가 아니라 pending execution layer에서 맞추는 것이 정확하다.

## ATR stop legacy rule

- stop multiple은 고정 `2.0 ATR` 이다.
- ATR은 진입 신호가 발생한 bar의 `atr20` 값을 `atr_at_entry`로 고정한다.
- 롱 initial stop: `entry_price - (2.0 * atr_at_entry)`
- 숏 initial stop: `entry_price + (2.0 * atr_at_entry)`
- stop price는 포지션 보유 중 갱신되지 않는다.
- trailing ATR stop이나 매 봉 ATR 재계산 stop은 없다.
- stop trigger 판정은 보유 중 각 bar의 intrabar extreme으로 본다.
  - 롱: `bar["low"] <= stop_price`
  - 숏: `bar["high"] >= stop_price`
- stop이 trigger되어도 체결가는 stop_price가 아니라 다음 봉 `open` 이다.

## opposite_10 exit legacy rule

- V4/V3는 `exit_mode="opposite_10"` 을 고정한다.
- 롱 opposite exit: `close < rolling_low_10`
- 숏 opposite exit: `close > rolling_high_10`
- opposite_10 exit도 trigger bar에서 즉시 체결하지 않고 다음 봉 `open` 에서 청산된다.

## exit priority

- legacy 구현은 같은 bar에서 stop과 opposite_10이 동시에 성립해도 `atr_stop` 이 우선이다.
- 근거는 `stop_triggered` 가 exit OR 체인의 첫 조건이며, exit reason도 `if stop_triggered` 로 먼저 결정되기 때문이다.
- 따라서 우선순위는 `atr_stop > opposite_10`.
- 현재 `mnq_v4` adapter 단계에서는 stop 주문을 아직 완전 발행하지 않고, metadata의 debug 필드로만 priority를 노출한다.

## next_bar hour entry block rule

- blocked entry hour는 signal bar hour가 아니라 pending order가 실행되려는 다음 봉 hour 기준이다.
- legacy 코드:
  - `entry_hour = pd.Timestamp(next_bar["datetime"]).hour`
  - `if entry_hour in blocked_entry_hours: continue`
- 기본 blocked hours는 `{15, 16, 17}`.
- 이 규칙은 신규진입에만 적용되고, 청산에는 적용되지 않는다.

## mnq_v4 implementation plan

- `TurtleV4Adapter`
  - `atr_at_entry`, `initial_stop_price`, stop/opposite priority debug metadata 유지
  - `entry_block_hour_basis="next_bar_hour_pending_execution_layer"` 로 source of truth 명시
- `ExecutionEngine`
  - pending entry order만 next-bar hour 기준으로 취소
  - exit order는 항상 통과
  - cancellation event를 strategy callback과 execution log로 남김
- 다음 실제 이식 단계
  - stop priority를 반영한 실제 exit emission 추가
  - stop-only exit도 pending queue로 보내도록 상태 머신 확장
  - replay 결과를 legacy trade sample과 대조 검증

## Backtest / execution behavior that must match

### Fill timing

- signal evaluation: 현재 봉 close
- fill timing: 다음 봉 open
- entry
  - `entry_price = next_bar.open +/- slippage`
- exit
  - stop/opposite exit가 현재 봉에서 trigger되어도 체결은 다음 봉 open
  - `_close_trade()`에서 `next_open - slippage` (long exit), `next_open + slippage` (short exit)

### Commission and slippage

- 기본 V4 실행값은 `commission=0.0`, `slippage=0.0`
- 코드상 지원은 존재
- pnl_dollars = `pnl_points * point_value - commission`
- point_value 기본값은 `2.0`

### Position overlap / pyramiding

- 중복 포지션 불가
- 동시에 하나의 포지션만 허용 (`position is None`일 때만 진입)
- 추가진입, 분할진입, 멀티포지션 없음

### Long / short symmetry differences

- 롱은 channel width 기반 MA500 예외가 있음
- 숏은 일관되게 MA500 하락 필요
- exit는 opposite_10 기준으로 대칭적
- ATR stop도 대칭적

## Migration cautions

- `rolling_high_20` / `rolling_low_20` 라는 컬럼명만 보고 20봉으로 착각하면 안 된다.
  - V4 실행에서는 실제 entry window가 30이다.
- `ma200` 컬럼명도 실제 역할은 MA500이다.
  - `trend_ma_window=500`으로 만들어진 컬럼이기 때문이다.
- 실시간 시스템에서도 “현재 봉 close에서 판정, 다음 봉 open에서 체결” 모델을 유지할지 먼저 결정해야 한다.
  - 이 부분이 바뀌면 연구 결과와 실시간 리플레이 결과가 달라진다.
- blocked entry hour도 next bar 기준으로 맞춰야 한다.
- ATR stop은 intrabar high/low로 trigger를 보고, 체결가는 next bar open이다.
  - stop trigger 자체를 stop price 체결로 바꾸면 결과가 달라진다.

## Items to port directly into TurtleV4Adapter

- prior-bar Donchian entry/exit window semantics
- `entry_window=30`, `exit_window=10`, `atr_window=20`, `trend_ma_window=500`
- long/short breakout close-based checks
- MA500 slope / long channel width exception logic
- blocked entry hour rule using next bar hour semantics
- position state fields required for one-position-at-a-time behavior

## Items better split into separate modules

- indicator preparation
  - Donchian / ATR / trend MA helper functions
- execution model
  - next-bar-open fill model
  - slippage / commission handling
- position state machine
  - entry fill, exit fill, atr stop, opposite_10 checks
- replay/backtest bridge
  - historical bar replay vs live paper event loop

## Must-match items for backtest vs replay consistency

- 15-minute input bars
- prior-bar channel calculation
- current-bar close signal evaluation
- next-bar open fill timing
- blocked entry hours on next bar timestamp
- ATR fixed at entry
- 2 ATR initial stop
- opposite_10 exit rule
- one-position-at-a-time constraint
- point value / commission / slippage assumptions

## v4_indicator_helper 도입

- `mnq_v4/app/strategies/v4_indicator_helper.py` 는 legacy V4 지표 계산을 표준 라이브러리만으로 분리한 모듈이다.
- 이 helper는 현재 봉을 제외한 이전 봉만 사용해서 다음 값을 계산한다.
  - `entry_high`
  - `entry_low`
  - `exit_high`
  - `exit_low`
  - `atr`
  - `trend_ma`
  - `trend_ma_previous`
  - `trend_ma_previous_2`
  - `trend_ma_slope_up`
  - `trend_ma_slope_down`
  - `channel_width`
  - `channel_width_pct`
  - `channel_width_atr`
- helper 반환값의 `ready` 는 현재 단계에서 `trend_ma` 계산 가능 여부를 기준으로 한다.
- helper 반환값의 `required_bars` 는 현재 봉 제외 규칙까지 고려한 최소 history 판단에 사용된다.

## Current-bar exclusion policy

- Donchian 계산은 항상 현재 봉 제외다.
- SMA 계산도 항상 현재 봉 제외다.
- ATR 계산도 항상 현재 봉 제외다.
- 특히 ATR은 첫 true range에도 이전 close가 필요하므로, ATR window만 맞는다고 바로 계산되지 않을 수 있다.
- 이 정책은 `mnq_research/app/indicators/turtle.py` 의 prior-bar rolling 구조와 정렬을 맞추기 위한 것이다.

## Signal vs execution separation

- 현재 단계의 `TurtleV4Adapter` 는 신호 조건만 계산하고 실제 체결은 하지 않는다.
- legacy 백테스트는 “현재 봉에서 조건 판정, 다음 봉 시가 체결” 구조다.
- 따라서 실거래/리플레이 이식 시에는 체결 시점을 strategy layer가 아니라 execution layer에서 처리해야 한다.
- 백테스트 결과와 맞추려면 다음 봉 시가 체결 semantics를 execution queue 또는 pending order layer에서 동일하게 구현해야 한다.

## Next-bar-open execution queue

- `mnq_v4` execution layer에는 pending order queue 골격이 추가되었다.
- 흐름은 아래와 같다.
  - 현재 bar 시작 시: 이전 bar close에서 나온 signal들을 `bar["open"]` 가격으로 처리
  - 현재 bar 진행 후: strategy가 현재 bar close 기준 signal을 계산
  - 새 signal은 즉시 체결하지 않고 pending queue에 저장
  - 다음 bar open에서 실제 처리
- 이 구조는 legacy V4 백테스트의 “현재 봉 close 판단, 다음 봉 시가 체결” 모델과 맞추기 위한 것이다.
- 현재 단계에서는 queue 처리 구조와 CSV 로그만 만들었고, 실제 broker fill/position mutation은 최소 골격 상태다.

## Debug condition only status

- 현재 `mnq_v4` 구현은 debug condition only 상태다.
- `raw_long_breakout`, `raw_short_breakout`, `long_trend_filter_pass`, `short_trend_filter_pass`, `long_channel_width_exception`, `blocked_by_entry_hour`, `long_entry`, `short_entry`, `long_exit`, `short_exit` 는 metadata에만 기록된다.
- 아직 실제 LONG/SHORT signal emission, position open/close, fill scheduling은 하지 않는다.

## Recommended migration order

1. Extract indicator helper module inside `mnq_v4`
2. Add next-bar-open execution queue semantics to paper runtime
3. Port V4 entry condition evaluation exactly
4. Port ATR stop and opposite_10 exit exactly
5. Build replay validator against known `mnq_research` trade samples

## StrategySignal activation

- `TurtleV4Adapter` 는 이제 debug conditions를 기반으로 실제 `StrategySignal` 을 반환한다.
- 진입 우선순위는 `no position + no pending signal` 상태에서만 평가한다.
- 청산 우선순위는 현재 포지션이 있을 때 진입보다 먼저 평가한다.
- signal reason은 아래 문자열로 정규화했다.
  - `long_breakout_v4`
  - `short_breakout_v4`
  - `long_exit_opposite_10`
  - `short_exit_opposite_10`

## Pending signal and on_execution linkage

- adapter 내부에는 `pending_signal_type`, `pending_signal_reason` 상태를 추가했다.
- signal이 발생하면 즉시 position state를 바꾸지 않고 pending signal만 기록한다.
- pending queue는 다음 봉 open에서 order를 처리하고 execution payload를 strategy에 다시 전달한다.
- `SignalPipeline` 는 execution engine 결과를 받아 strategy의 `on_execution()` 으로 전달한다.

## Position state updates happen after execution

- legacy V4와 정렬하기 위해 signal 판단과 체결 시점을 분리했다.
- `position_side`, `entry_price`, `entry_time` 등은 signal 발생 시가 아니라 execution 완료 시 업데이트된다.
- 따라서 현재 bar close에서 신호가 생겨도 실제 보유 상태 전환은 다음 bar open 이후에만 반영된다.
- 이 구조는 replay와 future live execution이 동일한 next-bar-open semantics를 유지하는 데 중요하다.
