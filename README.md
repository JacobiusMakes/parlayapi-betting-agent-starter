# parlayapi-betting-agent-starter

The shortest path from "how do I start?" to a running betting model scaffold.

One small Python file pulls live NFL moneylines from the [ParlayAPI](https://parlay-api.com)
sports odds API (30+ sportsbooks), strips each book's vig, prints the consensus fair line next
to the best available price, and leaves exactly one clearly marked hole where your model goes.
No API key needed to run it.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JacobiusMakes/parlayapi-betting-agent-starter/blob/main/starter.ipynb)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/JacobiusMakes/parlayapi-betting-agent-starter?quickstart=1)

## 90-second quickstart

Pick any of the three. All of them run keyless by default.

**1. Colab, zero install.** Click the badge above. Run all cells. The notebook is a cell-by-cell
mirror of `main.py`.

**2. Codespaces, zero local setup.** Click the badge above. The dev container installs the
dependency and runs `python main.py` for you the moment the editor attaches.

**3. Clone and run.** Python 3.10+.

```bash
git clone https://github.com/JacobiusMakes/parlayapi-betting-agent-starter
cd parlayapi-betting-agent-starter
pip install -r requirements.txt
python main.py
```

Different sport: `STARTER_SPORT=baseball_mlb python main.py` (demo mode covers NFL, MLB, NBA,
NHL, MMA, and EPL).

## What it prints

Real output from a real run (2026-09-04, demo mode):

```text
parlayapi-betting-agent-starter | sport=americanfootball_nfl | mode=keyless demo

[demo] Keyless sample: first 5 events, moneyline only, 58 requests left this hour.
[demo] Set PARLAY_API_KEY for every event and market: https://parlay-api.com/signup

MATCHUP                                     SIDE                  FAIR  BEST PRICE (BOOK)  MODEL P    EDGE
------------------------------------------  --------------------  ----  -----------------  -------  ------
New England Patriots at Seattle Seahawks    Seattle Seahawks      -172  -172 (prophetx)    63.2%     +0.0%
New England Patriots at Seattle Seahawks    New England Patriots  +172  +170 (novig)       36.8%     -0.3%
San Francisco 49ers at Los Angeles Rams     Los Angeles Rams      -176  -155 (hardrock)    63.8%     +3.0%
San Francisco 49ers at Los Angeles Rams     San Francisco 49ers   +176  +186 (novig)       36.2%     +1.2%
Chicago Bears at Carolina Panthers          Chicago Bears         -138  -140 (hardrock)    57.9%     -0.4%
Chicago Bears at Carolina Panthers          Carolina Panthers     +138  +141 (novig)       42.1%     +0.6%
Tampa Bay Buccaneers at Cincinnati Bengals  Cincinnati Bengals    -182  -190 (hardrock)    64.5%     -1.0%
Tampa Bay Buccaneers at Cincinnati Bengals  Tampa Bay Buccaneers  +182  +181 (pinnacle)    35.5%     -0.1%
New Orleans Saints at Detroit Lions         Detroit Lions         -278  -292 (novig)       73.5%     -0.9%
New Orleans Saints at Detroit Lions         New Orleans Saints    +278  +280 (betmgm)      26.5%     +0.1%

FAIR is the no-vig consensus across books. EDGE compares MODEL P
to the best price's implied probability. Plug a real model into
your_model() in main.py, and it flows straight into this table.
```

FAIR de-vigs each bookmaker separately (normalize that book's implied probabilities to sum
to 1) and averages across books. EDGE is model probability minus the best price's implied
probability, so with the default model it is pure line-shopping edge.

## The extension point

`your_model()` in `main.py` is the only function meant to be replaced:

```python
def your_model(event: Event, market_fair: dict[str, float]) -> dict[str, float]:
    return market_fair
```

It receives one event with every book's prices attached, plus the market's no-vig consensus,
and returns your probability per side. The default hands the consensus straight back. Swap in
an Elo rating, a Poisson model, or an LLM agent: the client underneath this repo is
[parlayapi-agent-tools](https://github.com/JacobiusMakes/parlayapi-agent-tools), which also
ships the same odds endpoints as ready-made LangChain, LlamaIndex, and raw OpenAI/Anthropic
function-calling tools.

## Full API mode

```bash
export PARLAY_API_KEY=your-key   # free tier: 1,000 credits/month, no card
python main.py
```

Same code path, but now every event, plus spreads, totals, props, and historical closing
lines through the same client. Get a key at [parlay-api.com/signup](https://parlay-api.com/signup);
paid tiers are on [/pricing](https://parlay-api.com/pricing).

## Honest limits

- Demo mode is a keyless sample: the first 5 events per sport, moneyline only, capped at
  60 requests/hour per IP, and it can lag the keyed feed. It is for evaluating, not betting.
- The default "model" is the market consensus, so the table measures line shopping, not alpha.
  The alpha part is your job; that is the point of the marked hole.
- No-vig-by-normalization is the simplest de-vig method. For alternatives (Shin, power),
  see the [notebooks](https://github.com/JacobiusMakes/parlayapi-notebooks).
- Nothing here is betting advice.

## Links

- [parlay-api.com](https://parlay-api.com) and the [API docs](https://parlay-api.com/docs)
- [Hosted MCP server](https://parlay-api.com/mcp) for Claude, Cursor, and other MCP clients
- [parlayapi-agent-tools](https://github.com/JacobiusMakes/parlayapi-agent-tools): the client this starter installs
- [parlayapi-notebooks](https://github.com/JacobiusMakes/parlayapi-notebooks): worked notebooks on no-vig, EV, line movement, CLV, parlay pricing

MIT licensed. Built by the ParlayAPI team.
