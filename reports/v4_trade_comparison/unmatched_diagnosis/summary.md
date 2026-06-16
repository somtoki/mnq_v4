# Unmatched V4 Trade Diagnosis

## Research Only Classification Counts

- `no_near_match`: 84
- `near_match_entry_shift`: 83
- `near_match_price_diff`: 28
- `possible_entry_hour_block`: 1
- `side_conflict`: 1

## Paper Only Classification Counts

- `near_match_entry_shift`: 83
- `near_match_price_diff`: 28
- `no_near_match`: 26
- `possible_entry_hour_block`: 1
- `side_conflict`: 1

## Top 10 Research Only Examples

- `2021-01-28T06:30:00` `short` -> `no_near_match` candidate `None` note `no_same_side_trade_within_5_bars`
- `2021-01-28T23:00:00` `long` -> `near_match_entry_shift` candidate `2021-01-28T23:15:00` note `same_side_trade_within_1_bar`
- `2021-01-29T22:45:00` `long` -> `no_near_match` candidate `None` note `no_same_side_trade_within_5_bars`
- `2021-02-17T23:00:00` `short` -> `near_match_entry_shift` candidate `2021-02-17T23:15:00` note `same_side_trade_within_1_bar`
- `2021-02-19T18:45:00` `long` -> `no_near_match` candidate `None` note `no_same_side_trade_within_5_bars`
- `2021-03-05T23:15:00` `long` -> `no_near_match` candidate `None` note `no_same_side_trade_within_5_bars`
- `2021-03-19T03:30:00` `short` -> `near_match_entry_shift` candidate `2021-03-19T03:45:00` note `same_side_trade_within_1_bar`
- `2021-03-26T19:45:00` `short` -> `near_match_entry_shift` candidate `2021-03-26T20:00:00` note `same_side_trade_within_1_bar`
- `2021-03-29T14:15:00` `short` -> `no_near_match` candidate `None` note `no_same_side_trade_within_5_bars`
- `2021-04-21T00:00:00` `short` -> `no_near_match` candidate `None` note `no_same_side_trade_within_5_bars`

## Top 10 Paper Only Examples

- `2021-01-28T23:15:00` `long` -> `near_match_entry_shift` candidate `2021-01-28T23:00:00` note `same_side_trade_within_1_bar`
- `2021-02-17T23:15:00` `short` -> `near_match_entry_shift` candidate `2021-02-17T23:00:00` note `same_side_trade_within_1_bar`
- `2021-02-18T00:30:00` `short` -> `no_near_match` candidate `None` note `no_same_side_trade_within_5_bars`
- `2021-02-19T21:30:00` `long` -> `no_near_match` candidate `None` note `no_same_side_trade_within_5_bars`
- `2021-03-19T03:45:00` `short` -> `near_match_entry_shift` candidate `2021-03-19T03:30:00` note `same_side_trade_within_1_bar`
- `2021-03-26T20:00:00` `short` -> `near_match_entry_shift` candidate `2021-03-26T19:45:00` note `same_side_trade_within_1_bar`
- `2021-04-23T03:00:00` `short` -> `near_match_entry_shift` candidate `2021-04-23T02:45:00` note `same_side_trade_within_1_bar`
- `2021-04-30T01:15:00` `short` -> `near_match_entry_shift` candidate `2021-04-30T01:00:00` note `same_side_trade_within_1_bar`
- `2021-06-02T00:00:00` `short` -> `near_match_price_diff` candidate `2021-06-01T23:15:00` note `same_side_trade_within_5_bars_but_price_diff`
- `2021-07-16T01:15:00` `short` -> `near_match_price_diff` candidate `2021-07-16T00:00:00` note `same_side_trade_within_5_bars_but_price_diff`

## Overall Assessment

- most remaining differences look closer to comparison matching issue
- Specific next fix recommendation: add tolerant matching that allows +/-1 bar entry alignment before classifying trades as unmatched

