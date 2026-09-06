# parlayapi-betting-agent-starter

A small Python scaffold for private sports-data research. Its existing analysis
normalizes each book's implied probabilities, averages those probabilities, and
leaves `your_model()` as the extension point. The calculations are examples and
assumptions, not profit forecasts.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JacobiusMakes/parlayapi-betting-agent-starter/blob/main/starter.ipynb)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/JacobiusMakes/parlayapi-betting-agent-starter?quickstart=1)

## First run

**Colab:** open the notebook and run all cells. The default `offline` mode runs
local illustrative math without installing packages, accessing the network, or
prompting for a key. Set `MODE` to `demo` only when you want the cloud runtime to
install the dependency and make one anonymous sample request. Google account and
runtime availability requirements still apply.

**Codespaces:** open the existing project. Creation installs the dependency;
attaching or reopening the editor does not run an API request. In the terminal:

```bash
python main.py
python main.py --demo
```

The first command is offline. The second makes one anonymous sample request and
ignores environment keys. Codespaces uses the reader's GitHub account and runtime
allowance. Creating a codespace is not a directory listing or a publication step.

**Local Python 3.10+:** the offline mode needs only Python. Install the dependency
before explicitly choosing a live mode:

```bash
git clone https://github.com/JacobiusMakes/parlayapi-betting-agent-starter
cd parlayapi-betting-agent-starter
python main.py
python -m pip install -r requirements.txt
python main.py --demo --sport baseball_mlb
```

The demo is at most five US moneyline events with a shared limit of 60 requests
per hour per IP. Availability varies by sport, event and source. Supported sports
are NFL, MLB, NBA, NHL, EPL and MMA; `python main.py --help` lists the exact keys.

## Your own account, explicit private use

Create your own [ParlayAPI account](https://parlay-api.com/signup), then choose:

```bash
python main.py --account --sport baseball_mlb
```

A hidden runtime prompt asks for your key. Never paste it into source, a command
argument, a notebook cell, or a shared file. The request uses your account allowance.
The program does not read keys from the environment to decide its mode. This is a
change from the earlier starter, which switched to account mode whenever a key
was present.

In Colab, first use a private notebook copy, set `MODE = "account"`, and run it.
The same hidden prompt and explicit account request apply. Clear outputs before
sharing code, and restart the runtime when finished. No key is persisted by the
starter. Other notebook hosts can save outputs differently; the configured Colab
output-omission flag is an extra precaution, not a privacy guarantee.

Requests use the fixed `https://parlay-api.com` origin, put the key only in a header,
reject redirects, bound response size and time, and do not retry automatically.
Errors do not print response bodies or remote error text.

## The existing model extension

```python
def your_model(event: Event, market_fair: dict[str, float]) -> dict[str, float]:
    return market_fair
```

The default returns the same consensus probabilities. `FAIR` is that calculated
baseline; `EDGE` compares the selected model probability with the chosen price's
implied probability. These existing methods have not been changed by the privacy
repair and do not establish freshness, execution availability, or model accuracy.
The typed event models come from
[parlayapi-agent-tools](https://github.com/JacobiusMakes/parlayapi-agent-tools).

## Sharing and license

Share the code, not keys, saved API outputs, account notebooks, or data files.
Each person supplies their own account for personal or internal research. MIT
licenses software; it does not license API data for public redisplay or
redistribution. The [applicable terms](https://parlay-api.com/terms) and written
agreements govern data. These tool defaults do not change existing contracts.

Current [API docs](https://parlay-api.com/docs), [plans](https://parlay-api.com/pricing),
[Python SDK](https://github.com/JacobiusMakes/parlay-api-python), and
[worked notebooks](https://github.com/JacobiusMakes/parlayapi-notebooks).

## Offline verification

```bash
python -m unittest -v test_privacy.py
```

Tests run the default program and notebook with network and prompts blocked.
Explicit demo/account tests use mocked transport and fake keys. No real API
request or native Colab/Codespaces execution is claimed by these local tests.
