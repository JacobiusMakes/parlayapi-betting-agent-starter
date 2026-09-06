"""Personal research model scaffold. Default execution is offline.

python main.py             local illustrative math only
python main.py --demo      one anonymous sample; environment keys ignored
python main.py --account   one account request after a hidden runtime key prompt

MIT covers code, not API data. Keep account results and executed notebooks private.
"""
from __future__ import annotations

import argparse
import getpass
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

SPORT = "americanfootball_nfl"
SPORTS = ("americanfootball_nfl", "baseball_mlb", "basketball_nba", "icehockey_nhl",
          "mma_mixed_martial_arts", "soccer_epl")
MIN_BOOKS = 3  # existing analysis threshold

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def create_client(api_key):
    # Import only for an explicitly selected live mode; offline needs no install.
    from parlayapi_tools.core import ParlayAPIClient, ParlayAPIError

    class PrivateClient(ParlayAPIClient):
        def _request(self, path, params=None, *, needs_key):
            if needs_key and not self.api_key:
                raise ParlayAPIError("Enter your own key for account mode.")
            if not path.startswith("/") or path.startswith("//") or ".." in path or "\\" in path:
                raise ParlayAPIError("Use a fixed API path.")
            query = {key: value for key, value in (params or {}).items() if value is not None}
            url = "https://parlay-api.com" + path
            if query:
                url += "?" + urlencode(query)
            headers = {"Accept": "application/json"}
            if needs_key:
                headers["X-API-Key"] = self.api_key
            request = Request(url, headers=headers)
            try:
                with build_opener(NoRedirect()).open(request, timeout=30) as response:
                    body = response.read(10_000_001)
                    if response.status != 200 or len(body) > 10_000_000:
                        raise ParlayAPIError("Unexpected API response. No automatic retry.")
                    return json.loads(body)
            except HTTPError as error:
                error.close()
                raise ParlayAPIError(f"API returned HTTP {error.code}. No automatic retry.") from None
            except (URLError, OSError, ValueError):
                raise ParlayAPIError("Request or JSON response failed. No automatic retry.") from None

    return PrivateClient(api_key=api_key, base_url="https://parlay-api.com")


def fetch_events(mode, sport, api_key=""):
    if mode not in {"offline", "demo", "account"} or sport not in SPORTS:
        raise ValueError("Choose a listed mode and supported sport.")
    if mode == "offline":
        return []
    if mode == "account" and (not api_key or any(ord(c) < 33 or ord(c) > 126 for c in api_key)):
        raise ValueError("Enter a valid key without whitespace or control characters.")
    client = create_client(api_key if mode == "account" else "")
    if mode == "account":
        return client.get_odds(sport, markets="h2h", odds_format="american")
    demo = client.demo_odds(sport)
    print("Demo: at most five US moneyline events; shared limit 60 requests/hour per IP.")
    print("Availability varies. Your account allowance applies only in explicit account mode.")
    return list(demo.events)


def american_to_prob(price: float) -> float:
    """Implied win probability of an American price, vig still included."""
    if price >= 100:
        return 100.0 / (price + 100.0)
    return -price / (-price + 100.0)


def prob_to_american(prob: float) -> int:
    """Fair American price for a probability."""
    if prob >= 0.5:
        return round(-100.0 * prob / (1.0 - prob))
    return round(100.0 * (1.0 - prob) / prob)


def no_vig_consensus(event: Event) -> dict[str, float]:
    """Consensus fair probability per side of the moneyline.

    Each book's implied probabilities are normalized to sum to 1 (that
    removes the vig book by book), then averaged across books. Simple,
    standard, and a sane baseline for any model to beat.
    """
    per_side: dict[str, list[float]] = {}
    for book in event.bookmakers:
        market = book.market("h2h")
        if market is None:
            continue
        probs = {o.name: american_to_prob(o.price)
                 for o in market.outcomes if o.price is not None}
        overround = sum(probs.values())
        if len(probs) < 2 or overround <= 0:
            continue
        for side, p in probs.items():
            per_side.setdefault(side, []).append(p / overround)
    return {side: sum(ps) / len(ps)
            for side, ps in per_side.items() if len(ps) >= MIN_BOOKS}


# ---------------------------------------------------------------------------
# >>> YOUR MODEL GOES HERE <<<
#
# This is the extension point, and the only function meant to be replaced.
# It receives one event plus the market's no-vig consensus and returns your
# probability per side. The starter's default just hands the consensus
# back, so any edge you see below comes purely from line shopping (a best
# price that beats the de-vigged market average).
#
# Ideas: an Elo or power rating, a Poisson goals model, injury news, or an
# LLM agent built on these same tools (see the README's agent-tools link).
# ---------------------------------------------------------------------------
def your_model(event: Event, market_fair: dict[str, float]) -> dict[str, float]:
    return market_fair


def build_rows(events: list[Event]) -> list[tuple[str, str, str, str, str, float]]:
    rows = []
    for event in events:
        fair = no_vig_consensus(event)
        model = your_model(event, fair)
        for side in sorted(fair, key=fair.get, reverse=True):
            best = event.best_price("h2h", side)
            if best is None or side not in model:
                continue
            book, price = best
            edge = (model[side] - american_to_prob(price)) * 100.0
            rows.append((event.matchup, side, f"{prob_to_american(fair[side]):+d}",
                         f"{price:+.0f} ({book})", f"{model[side]:.1%}", edge))
    return rows


def print_table(rows: list[tuple[str, str, str, str, str, float]]) -> None:
    header = ("MATCHUP", "SIDE", "FAIR", "BEST PRICE (BOOK)", "MODEL P", "EDGE")
    widths = [max(len(str(r[i])) for r in rows + [header]) for i in range(5)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths) + "  {:>6}"
    print(fmt.format(*header))
    print(fmt.format(*("-" * w for w in widths), "-" * 6))
    for row in rows:
        print(fmt.format(*row[:5], f"{row[5]:+.1f}%"))

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="one anonymous API sample")
    mode.add_argument("--account", action="store_true", help="one private request; prompts for your key")
    parser.add_argument("--sport", choices=SPORTS, default=SPORT)
    args = parser.parse_args(argv)
    chosen_mode = "account" if args.account else "demo" if args.demo else "offline"
    print("parlayapi-betting-agent-starter | mode=" + chosen_mode)
    if chosen_mode == "offline":
        # Illustrative math, not an observation or forecast from a sportsbook.
        assert abs(american_to_prob(-110) - 110 / 210) < 1e-12
        assert prob_to_american(0.5) == -100
        print("Offline math checks passed. No key, network, or current market data used.")
        print("Choose --demo for one anonymous sample or --account for your own private request.")
        return 0
    key = ""
    try:
        if chosen_mode == "account":
            key = getpass.getpass("Your own ParlayAPI key (hidden; account credits apply): ")
        events = fetch_events(chosen_mode, args.sport, key)
    except ImportError:
        print("Install requirements.txt before choosing a live mode.", file=sys.stderr)
        return 1
    except (RuntimeError, ValueError, OSError, EOFError):
        print("Request failed. Check the selected mode, your allowance and current docs. No automatic retry.", file=sys.stderr)
        return 1
    finally:
        key = ""
    rows = build_rows(events)
    if not rows:
        print("No rows met this example's analysis requirements. This does not establish source coverage.")
        return 0
    print_table(rows)
    print("Keep these runtime results private. Clear notebook outputs before sharing code.")
    print("FAIR and EDGE use the existing model assumptions; they are not profit forecasts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
