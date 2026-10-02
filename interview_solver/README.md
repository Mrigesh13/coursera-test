# Interview Solver Agent

A Claude-powered agent that takes a LeetCode-style or interview question and returns the solution
with the best time and space complexity it can find. It doesn't stop at a plausible answer. It runs
code to check it:

1. Restates the problem, its constraints and edge cases.
2. Writes a **brute-force** solution to use as a reference oracle.
3. Finds the **optimal pattern** (hashing, two pointers, sliding window, monotonic stack, DP with
   space compression, binary search on the answer, and so on), working from the constraints.
4. **Stress-tests** the optimized solution against the brute force on hundreds of random inputs
   and edge cases, and fixes any mismatch.
5. **Benchmarks** it at growing input sizes to confirm the claimed complexity.
6. Returns a structured write-up: summary, brute force, optimal approach, solution code,
   complexity, verification, and interview tips.

## Running it inside Claude Code (no API key)

The same agent is also a Claude Code subagent, defined in
[`.claude/agents/interview-solver.md`](../.claude/agents/interview-solver.md). Open this repo in
Claude Code and ask:

> Use the interview-solver agent to solve: *paste the problem here*

Claude Code runs the brute-force comparison and timing steps with its own tools, so it needs no
API key and costs nothing beyond your Claude Code plan. Add "in Java" (or another language) to
get the final solution in that language. Subagents load when a session starts, so after pulling
this file, start a new session (or run `/agents` to check that `interview-solver` is listed).

## Running it as a standalone script (Claude API)

### Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # or: ant auth login
```

### Usage

```bash
# Inline question
python agent.py "Given an integer array nums, return the length of the longest strictly increasing subsequence. 1 <= n <= 2500"

# From a file, with the final solution in Java
python agent.py -f problem.txt --language Java

# Paste from stdin, and show the model's reasoning summaries
python agent.py -v
```

Progress (each code run) goes to stderr and the final Markdown answer goes to stdout, so
`python agent.py -f q.txt > answer.md` saves a clean answer.

### How it works

- Model: `claude-opus-5-5` with adaptive thinking at `high` effort.
- The SDK's tool runner drives the agent loop with a single tool, `run_python`. It runs the
  model's script in a fresh subprocess (`python -I`, temp directory, 60 s maximum timeout,
  output capped at 20 KB).
- Server-side refusal fallbacks (`fallbacks="default"`) are enabled, so a rare safety-classifier
  decline is retried on a fallback model instead of failing.

> **Security note:** `run_python` runs model-written code on your machine with your user's
> permissions. It's isolated from your environment variables and working directory, but it is
> not a sandbox. For untrusted input, run the agent inside a container or VM.

## Tests

```bash
python -m unittest test_agent   # offline; no API key needed
```
