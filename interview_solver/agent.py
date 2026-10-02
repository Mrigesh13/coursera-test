"""Interview problem solver agent.

Give it a LeetCode-style question and it works toward the optimal solution:
it brute-forces first, finds the better algorithm, then *runs code* to prove the
optimized version matches the brute force on random inputs and scales the way
its claimed time complexity says it should.
"""

import argparse
import os
import subprocess
import sys
import tempfile

import anthropic
from anthropic import beta_tool

MODEL = "claude-opus-5-5"
MAX_OUTPUT_CHARS = 20_000

SYSTEM_PROMPT = """\
You are an expert competitive programmer and technical interview coach. The user \
gives you an algorithms / data-structures problem (LeetCode, HackerRank, Codeforces, \
or a typical software engineering interview question). Your job is to deliver the \
solution with the best achievable time complexity, and among those the best space \
complexity, and to prove it is correct by running code.

Work through these steps, using the run_python tool to execute code:

1. Understand: restate the problem in one or two sentences, note the input \
constraints (state reasonable ones if none are given), and list the edge cases \
(empty input, single element, duplicates, negatives, overflow, etc.).
2. Brute force: describe the naive approach and its time/space complexity. \
Implement it; it becomes the reference oracle for testing.
3. Optimize: identify the bottleneck and the pattern that removes it (hashing, \
two pointers, sliding window, prefix sums, monotonic stack/queue, binary search \
on the answer, heaps, union-find, BFS/DFS, topological sort, DP with state \
compression, greedy with an exchange argument, bit tricks, math). Use the input \
constraints to infer the target complexity (e.g. n <= 1e5 means O(n log n) or \
better). Consider whether space can be reduced (in-place updates, rolling DP rows, \
O(1) pointers instead of auxiliary structures).
4. Verify correctness: in one run_python call, implement both the brute force and \
the optimized solution and stress-test them against each other on a few hundred \
small random inputs plus the hand-picked edge cases. If they disagree, print the \
failing input, fix the bug, and re-run until they agree.
5. Verify complexity: benchmark the optimized solution at a few growing input \
sizes (e.g. n = 1e3, 1e4, 1e5) and check that the timing growth matches the \
claimed complexity. Keep each run under about 20 seconds.
6. Answer.

Your final reply must use exactly this structure in Markdown:

## Problem summary
## Brute force
Approach in a sentence or two, with **Time:** and **Space:**.
## Optimal approach
The key insight, why it is correct, and a short walkthrough on a small example.
## Solution
The final, clean, commented code in {language}. It must be the code you verified \
(translated faithfully if {language} is not Python).
## Complexity
**Time:** O(...) and **Space:** O(...), each with a one-line justification. Say \
whether this is provably optimal (e.g. you must read every element) or the best \
known approach.
## Verification
What you tested (number of random cases, edge cases, benchmark timings).
## Interview tips
Two or three bullets: how to explain this in an interview, common pitfalls, and \
likely follow-up questions.
"""


def execute_python(code: str, timeout_s: int = 30) -> str:
    """Run a Python script in a fresh, isolated subprocess and return its output."""
    timeout_s = max(1, min(int(timeout_s), 60))
    with tempfile.TemporaryDirectory() as workdir:
        script = os.path.join(workdir, "main.py")
        with open(script, "w") as f:
            f.write(code)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", script],  # -I: ignore env vars and user site-packages
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return (
                f"TIMEOUT: the script ran for more than {timeout_s}s. "
                "Use smaller inputs, or the solution is slower than expected."
            )
    out = f"exit code: {proc.returncode}\n--- stdout ---\n{proc.stdout}"
    if proc.stderr:
        out += f"\n--- stderr ---\n{proc.stderr}"
    if len(out) > MAX_OUTPUT_CHARS:
        out = out[:MAX_OUTPUT_CHARS] + "\n... [output truncated, print less]"
    return out


@beta_tool
def run_python(code: str, timeout_s: int = 30) -> str:
    """Execute a self-contained Python 3 script and return its exit code, stdout, and stderr.

    Use it to run brute-force vs. optimized stress tests and timing benchmarks.
    Only the standard library is available. Print everything you need to see,
    but keep output short (summaries, not every test case).

    Args:
        code: The complete Python script to run.
        timeout_s: Seconds before the script is killed (1-60, default 30).
    """
    return execute_python(code, timeout_s)


def solve(question: str, language: str = "Java", verbose: bool = False) -> str:
    """Run the agent on one question and return its final Markdown answer."""
    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT.format(language=language),
        thinking={"type": "adaptive", "display": "summarized"},
        output_config={"effort": "high"},
        # If a safety classifier declines, retry on Anthropic's recommended fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        tools=[run_python],
        max_iterations=15,
        messages=[{"role": "user", "content": question}],
    )

    final = None
    for message in runner:
        final = message
        for block in message.content:
            if block.type == "thinking" and verbose and block.thinking:
                print(f"\n[thinking] {block.thinking}", file=sys.stderr)
            elif block.type == "tool_use":
                first_line = block.input.get("code", "").strip().splitlines()[:1]
                print(f"[run_python] {first_line[0] if first_line else ''} ...", file=sys.stderr)

    if final is None:
        raise RuntimeError("The agent returned no response.")
    if final.stop_reason == "refusal":
        raise RuntimeError("The model declined this request.")
    if final.stop_reason == "max_tokens":
        print("[warning] answer was cut off by max_tokens", file=sys.stderr)
    return "".join(b.text for b in final.content if b.type == "text")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Solve a coding interview question with optimal time and space complexity."
    )
    parser.add_argument("question", nargs="?", help="The problem text (omit to read from --file or stdin).")
    parser.add_argument("-f", "--file", help="Read the problem from a text file.")
    parser.add_argument("-l", "--language", default="Java",
                        help="Language for the final solution, e.g. Python, C++, Go (default: Java).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show the model's reasoning summaries.")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            question = f.read()
    elif args.question:
        question = args.question
    else:
        if sys.stdin.isatty():
            print("Paste the problem, then press Ctrl-D:", file=sys.stderr)
        question = sys.stdin.read()

    if not question.strip():
        parser.error("no question given")

    try:
        print(solve(question, language=args.language, verbose=args.verbose))
    except anthropic.AuthenticationError:
        sys.exit("Authentication failed: set ANTHROPIC_API_KEY (or run `ant auth login`).")
    except anthropic.RateLimitError:
        sys.exit("Rate limited by the API. Wait a moment and try again.")
    except anthropic.APIStatusError as e:
        sys.exit(f"API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        sys.exit("Could not reach the Anthropic API. Check your network connection.")
    except RuntimeError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
