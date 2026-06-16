from app.research.csv_bar_feed import CsvBarFeed


def test_csv_bar_feed_reads_rows_and_converts_numeric_fields(tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "datetime,open,high,low,close,volume\n"
        "2024-01-02 09:30:00,16800,16805,16798,16803,120\n"
        "2024-01-02 09:45:00,16803,16808,16801,16806,135\n",
        encoding="utf-8",
    )

    bars = list(CsvBarFeed(str(csv_path), symbol="MNQ"))

    assert len(bars) == 2
    assert bars[0]["symbol"] == "MNQ"
    assert isinstance(bars[0]["open"], float)
    assert isinstance(bars[0]["high"], float)
    assert isinstance(bars[0]["low"], float)
    assert isinstance(bars[0]["close"], float)
    assert isinstance(bars[0]["volume"], float)
    assert bars[0]["open"] == 16800.0
    assert bars[1]["close"] == 16806.0


def test_csv_bar_feed_handles_missing_volume_column(tmp_path):
    csv_path = tmp_path / "sample_no_volume.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close\n"
        "2024-01-02 09:30:00,16800,16805,16798,16803\n",
        encoding="utf-8",
    )

    bars = list(CsvBarFeed(str(csv_path), symbol="MNQ"))

    assert len(bars) == 1
    assert bars[0]["volume"] == 0.0
    assert bars[0]["timestamp"] == "2024-01-02 09:30:00"
