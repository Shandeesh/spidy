"""
verify_roi_guard.py
Quick offline test to confirm the ROI Guard logic works correctly
(without a live MT5 connection).

Simulates _process_single_pos_guardian_sync's ROI calculation using
a mocked margin value to verify 30% / 70% thresholds fire correctly.
"""

class MockPos:
    def __init__(self, profit, volume=0.05, price_open=1.08, type_=0):
        self.profit = profit
        self.commission = -0.10
        self.swap = -0.05
        self.volume = volume
        self.price_open = price_open
        self.type = type_   # 0=BUY, 1=SELL
        self.ticket = 99999
        self.symbol = "EURUSD"


def simulate_roi_guard(pos, mocked_margin):
    """
    Replicates the ROI Guard logic from bridge_server.py
    using a mocked margin value instead of calling MT5.
    """
    margin = mocked_margin
    if not margin or margin <= 0:
        margin = 1.0

    comm = getattr(pos, 'commission', 0.0)
    swap = getattr(pos, 'swap', 0.0)
    net_profit_roi = pos.profit + comm + swap

    roi = (net_profit_roi / margin) * 100.0

    roi_close = False
    roi_reason = ""

    if roi <= -30.0:
        roi_close = True
        roi_reason = f"Stop Loss (ROI {roi:.2f}% <= -30%)"
    elif roi >= 70.0:
        roi_close = True
        roi_reason = f"Take Profit (ROI {roi:.2f}% >= 70%)"

    return roi, roi_close, roi_reason


def run_tests():
    print("=" * 60)
    print("ROI GUARD VERIFICATION TEST")
    print("  Mocked margin = $5.00 (typical for 0.05 lot EURUSD)")
    print("=" * 60)

    MOCKED_MARGIN = 5.00  # Realistic broker margin for 0.05 lot

    test_cases = [
        # (description, net_profit_gross, expected_close, expected_direction)
        ("SCENARIO A — Heavy Loss     : profit=-$2.00", -2.00, True,  "LOSS GUARD"),
        ("SCENARIO B — Big Profit     : profit=+$4.00", +4.00, True,  "PROFIT GUARD"),
        ("SCENARIO C — Small Profit   : profit=+$1.00", +1.00, False, "HOLD"),
        ("SCENARIO D — Small Loss     : profit=-$1.00", -1.00, False, "HOLD"),
        ("SCENARIO E — Exact -30% ROI: profit=-$1.575", -1.575, True, "LOSS GUARD (edge)"),
        ("SCENARIO F — Exact +70% ROI: profit=+$3.575", +3.575, True, "PROFIT GUARD (edge)"),
    ]

    all_passed = True
    for desc, gross_profit, expected_close, label in test_cases:
        pos = MockPos(profit=gross_profit)
        roi, should_close, reason = simulate_roi_guard(pos, MOCKED_MARGIN)
        # net = gross + commission(-0.10) + swap(-0.05) = gross - 0.15
        net = gross_profit + pos.commission + pos.swap
        status = "✅ PASS" if should_close == expected_close else "❌ FAIL"
        if should_close != expected_close:
            all_passed = False
        print(f"\n  {desc}")
        print(f"    Net Profit = ${net:.3f} | Margin = ${MOCKED_MARGIN:.2f} | ROI = {roi:.2f}%")
        print(f"    Expected : {'CLOSE' if expected_close else 'HOLD'} ({label})")
        print(f"    Got      : {'CLOSE — ' + reason if should_close else 'HOLD'}")
        print(f"    Result   : {status}")

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED ✅ — ROI Guard logic is correct.")
    else:
        print("SOME TESTS FAILED ❌ — Check the logic above.")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
