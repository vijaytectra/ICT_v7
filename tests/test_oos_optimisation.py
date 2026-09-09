import pandas as pd
import pytest


@pytest.fixture
def bars():
    return pd.DataFrame(
        {
            "o_b": [100.0, 100.0], "h_b": [101.0, 104.0],
            "l_b": [99.0, 96.0], "c_b": [100.0, 100.0],
            "o_a": [100.2, 100.2], "h_a": [101.2, 104.2],
            "l_a": [99.2, 96.2], "c_a": [100.2, 100.2],
        },
        index=pd.date_range("2025-01-01", periods=2, freq="min"),
    )


def test_long_limit_requires_ask_to_reach_entry(bars):
    from models.oos_optimisation import evaluate_trade_path

    # Bid trades through 99.1, but ask never does: a buy limit is not filled.
    result = evaluate_trade_path(bars.iloc[:1], side=1, entry=99.1,
                                 stop=98.0, target=102.0)

    assert result["status"] == "unfilled"


def test_long_exit_uses_bid_not_ask(bars):
    from models.oos_optimisation import evaluate_trade_path

    only_ask_reaches_target = bars.copy()
    only_ask_reaches_target.loc[only_ask_reaches_target.index[1], "h_b"] = 101.9
    only_ask_reaches_target.loc[only_ask_reaches_target.index[1], "h_a"] = 102.1

    result = evaluate_trade_path(only_ask_reaches_target, side=1, entry=100.0,
                                 stop=98.0, target=102.0)

    assert result["status"] == "expired"


def test_same_m1_bar_touching_stop_and_target_scores_stop_first(bars):
    from models.oos_optimisation import evaluate_trade_path

    result = evaluate_trade_path(bars, side=1, entry=100.0, stop=98.0,
                                 target=102.0)

    assert result["status"] == "stop"
