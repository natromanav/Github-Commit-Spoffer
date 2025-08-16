import os
import json
import random
import subprocess
import argparse
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

DATA = "data.json"


def run_git(args, *, env=None, check=True):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    result = subprocess.run(
        ["git", *args],
        env=full_env,
        check=check,
        capture_output=True,
        text=True,
    )
    return result


def check_repo():
    try:
        cp = run_git(["rev-parse", "--is-inside-work-tree"], check=True)
        if cp.stdout.strip() != "true":
            raise RuntimeError("Not inside a git repository")
    except subprocess.CalledProcessError as e:
        raise RuntimeError("Failed to check if inside a git repository") from e


def date_offset(tzname: str, weeks: int, days: int) -> str:
    tz = ZoneInfo(tzname) if (ZoneInfo and tzname) else timezone.utc
    now = datetime.now(tz)
    base = now - timedelta(days=365) + timedelta(days=1)
    target = base + timedelta(weeks=weeks, days=days)
    return target.isoformat(timespec="seconds")


def overwrite_data(iso_dt: str):
    payload = {"date": iso_dt}
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    run_git(["add", DATA])


def commit_data(iso_dt: str, message: str | None = None):
    message = message or iso_dt
    env = {
        "GIT_AUTHOR_NAME": iso_dt,
        "GIT_COMMITTER_NAME": iso_dt,
    }
    run_git(["commit", "-m", message, "--date", iso_dt], env=env)


def mark_commit(week: int, day: int, tzname: str):
    iso_dt = date_offset(tzname, week, day)
    overwrite_data(iso_dt)
    commit_data(iso_dt)


def generate_commits(n: int,
                     tzname: str,
                     *,
                     max_weeks: int = 54,
                     max_day: int = 6,
                     dry_run: bool = False,
                     seed: int | None = None):
    if seed is not None:
        random.seed(seed)
    for i in range(n):
        x = random.randint(0, max_weeks)
        y = random.randint(0, max_day)
        iso_dt = date_offset(tzname, x, y)
        print(f"[{i+1}/{n}] {iso_dt} (w={x}, d={y}  )")
        if dry_run:
            continue
        overwrite_data(iso_dt)
        commit_data(iso_dt)


def push():
    run_git(["push"])


def main():
    parser = argparse.ArgumentParser(
        description="Paint your GitHub contribution graph with backdated commits.")

    try:
        check_repo()
    except RuntimeError as e:
        print(f"Error: {e}")
        return

    parser.add_argument("-n", "--commits", type=int, default=100,
                        help="Number of commits to generate (default: 100)")
    parser.add_argument("--tz", "--timezone", dest="tz", default="Asia/Kolkata",
                        help="IANA timezone (default: Asia/Kolkata)")
    parser.add_argument("--seed", type=int,
                        help="Random seed for reproducible layout")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned dates but don't commit")
    parser.add_argument("--no-push", action="store_true",
                        help="Create commits but don't push at the end")
    args = parser.parse_args()

    check_repo()

    if args.commits <= 0:
        print("Nothing to do (commits <= 0).")
        return

    generate_commits(args.commits, tzname=args.tz,
                     seed=args.seed, dry_run=args.dry_run)

    if not args.no_push and not args.dry_run:
        print("Pushing commits...")
        push()
        print("Done.")


if __name__ == "__main__":
    main()
