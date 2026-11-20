"""Explicit, opt-in live API smoke check; never discovered as an automated test."""

import os


if __name__ == "__main__":
    if os.getenv("DATAWEBOT_LIVE_TEST") != "1":
        raise SystemExit("Set DATAWEBOT_LIVE_TEST=1 to explicitly run the paid Datawebot API smoke check.")
    from src.api_handler import fetch_datawebot

    # This makes a real request and may use API credits. It is deliberately not part of pytest.
    response = fetch_datawebot("https://www.olx.co.id/mobil-bekas_c198/q-toyota-avanza", max_pages=1)
    print(f"Valid response. Raw listings: {len(response.get('raw', []))}; metadata available: {'meta' in response}.")
