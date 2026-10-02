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

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # or: ant auth login
```

## Usage

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

## How it works

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
