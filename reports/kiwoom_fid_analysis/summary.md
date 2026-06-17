# Kiwoom FID Analysis Summary

Input: `C:\Users\Cham\OneDrive\Desktop\mnq_v4\data\live\test_kiwoom_fid_discovery.csv`

## Overview

- Fields analyzed: `6`
- Time candidates: `1`
- Price candidates: `1`
- Volume candidates: `1`

## Inspect First

- `candidate_time_fields.csv`
- `candidate_price_fields.csv`
- `candidate_volume_fields.csv`
- `fid_summary.csv`

## Top Candidates

### Time

- `trade_time` non_empty=`5` changed=`4` samples=`093005 | 094459 | 094501 | 095959 | 100001` reason=`key contains time; sample values look like HHMMSS`

### Price

- `current_price` non_empty=`5` changed=`4` samples=`21010.25 | 21013.00 | 21015.50 | 21018.25 | 21017.75` reason=`numeric parse rate is high; values fall within broad MNQ-like price range; value changes across events; key contains price`

### Volume

- `volume` non_empty=`5` changed=`4` samples=`1 | 2 | 3` reason=`key name looks volume-like; numeric and non-negative`

