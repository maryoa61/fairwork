# FairWork

**Milestone-based freelance escrow with AI dispute resolution, built as a GenLayer Intelligent Contract.**

FairWork lets a client and a freelancer agree on a job split into milestones,
lock payment in escrow, and release funds either by mutual approval or —
when they disagree — through decentralized AI arbitration powered by
GenLayer's Optimistic Democracy consensus.

## Why this needs GenLayer

A normal smart contract can hold escrow, but it cannot judge whether
"the homepage redesign is done" based on a written explanation and a link
to the delivered work. That judgment is subjective and requires natural
language understanding — exactly what GenLayer's validators (running
LLMs) are built for.

This contract is not a thin LLM wrapper: the arbitration step is wrapped in
`gl.eq_principle_prompt_comparative`, meaning multiple independent
validators must reach a genuinely equivalent verdict before the outcome is
accepted on-chain. If the freelancer provides a proof-of-work URL, the
contract also fetches that page live from inside consensus via
`gl.get_webpage`, with no external oracle involved.

## How it works

1. **`create_job`** — Client sends funds and defines milestones
   (description + amount each). Funds are locked in the contract.
2. **`submit_milestone`** — Freelancer marks a milestone as delivered, with
   a note and optional proof URL.
3. **Happy path — `approve_milestone`** — Client approves; funds for that
   milestone are released to the freelancer immediately. No AI involved.
4. **Unhappy path:**
   - **`raise_dispute`** — Client explains why the work doesn't meet the
     milestone definition.
   - **`reply_to_dispute`** — Freelancer defends their work. This call
     triggers AI arbitration: validators independently read the original
     milestone description, the freelancer's evidence (including the live
     fetched page, if any), the client's objection, and the freelancer's
     reply, then decide what percentage of the milestone amount is fair.
     Funds are split and released automatically based on the verdict.

## Project structure

```
contracts/
  fairwork.py        # the Intelligent Contract
tests/
  test_fairwork.py    # example test outline (pytest style, per GenLayer docs)
scripts/
  deploy.md           # manual deployment notes for GenLayer Studio
```

## Deploying in GenLayer Studio

1. Go to [studio.genlayer.com](https://studio.genlayer.com/contracts).
2. Create a new contract, paste in `contracts/fairwork.py`.
3. Deploy with no constructor arguments.
4. Use **Write Methods** to call `create_job` (sending value), then
   `submit_milestone`, then either `approve_milestone` or
   `raise_dispute` → `reply_to_dispute`.
5. Watch the **Node Logs** panel to see each validator's independent LLM
   verdict and how consensus is reached.

## Status

This is a first working version intended for the GenLayer testnet /
Studio sandbox. Known simplifications documented in `JOURNEY.md` ideas
for follow-up: per-milestone deadlines, multi-round disputes, a
reputation score per freelancer/client, and a small frontend.

## License

MIT
