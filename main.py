"""Betting agent starter for the ParlayAPI sports odds API.

Pulls live moneylines, strips each bookmaker's vig, and prints the
consensus fair line next to the best available price, with one clearly
marked hole where your model goes.

Runs two ways, no code change between them:

  keyless demo (default)   no signup; first 5 events, moneyline only,
                           60 requests/hour per IP
  full API                 set PARLAY_API_KEY; free tier is 1,000
                           credits/month, no card

Docs: https://parlay-api.com/docs   Signup: https://parlay-api.com/signup
"""

from __future__ import annotations

import os
import sys

from parlayapi_tools.core import Event, ParlayAPIClient, ParlayAPIError

SPORT = os.environ.get("STARTER_SPORT", "americanfootball_nfl")
MIN_BOOKS = 3  # skip sides priced at fewer books than this: too thin to trust


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


def fetch_events(client: ParlayAPIClient) -> list[Event]:
    """Keyed feed when PARLAY_API_KEY is set, keyless demo sample otherwise."""
    if client.api_key:
        return client.get_odds(SPORT, markets="h2h", odds_format="american")
    demo = client.demo_odds(SPORT)
    print(f"[demo] Keyless sample: first 5 events, moneyline only, "
          f"{demo.demo_remaining_hour} requests left this hour.")
    print(f"[demo] Set PARLAY_API_KEY for every event and market: "
          f"{demo.demo_signup_url}\n")
    return list(demo.events)


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


def main() -> int:
    client = ParlayAPIClient()  # reads PARLAY_API_KEY if present
    mode = "full API" if client.api_key else "keyless demo"
    print(f"parlayapi-betting-agent-starter | sport={SPORT} | mode={mode}\n")
    try:
        events = fetch_events(client)
    except ParlayAPIError as exc:
        print(f"ParlayAPI error: {exc}", file=sys.stderr)
        return 1
    rows = build_rows(events)
    if not rows:
        print(f"No events with {MIN_BOOKS}+ books priced right now for "
              f"'{SPORT}'. Try STARTER_SPORT=baseball_mlb python main.py")
        return 0
    print_table(rows)
    print("\nFAIR is the no-vig consensus across books. EDGE compares MODEL P")
    print("to the best price's implied probability. Plug a real model into")
    print("your_model() in main.py, and it flows straight into this table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
