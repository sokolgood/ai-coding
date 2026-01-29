import argparse
import sys

from src.application.code import CodeWorker
from src.application.fix import FixWorker
from src.application.review import ReviewWorker
from src.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent", description="AI Coding Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    code_parser = subparsers.add_parser("code", help="Code Agent: create/update PR from issue")
    code_parser.add_argument("--issue", type=int, required=True, help="Issue number")
    code_parser.add_argument("--base", type=str, default="main", help="Base branch (default: main)")
    code_parser.add_argument("--max-iter", type=int, default=5, help="Max iterations (default: 5)")

    review_parser = subparsers.add_parser("review", help="Review Agent: review PR")
    review_parser.add_argument("--pr", type=int, required=True, help="Pull request number")

    fix_parser = subparsers.add_parser("fix", help="Fix Agent: fix PR based on review")
    fix_parser.add_argument("--pr", type=int, required=True, help="Pull request number")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    settings = get_settings()

    if not settings.gh_token:
        print("Error: GH_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    if not settings.repo:
        print("Error: REPO environment variable is required", file=sys.stderr)
        sys.exit(1)

    try:
        if args.command == "code":
            worker = CodeWorker(settings)
            worker.run(args.issue, args.base, args.max_iter)
            print(f"Successfully processed issue #{args.issue}")

        elif args.command == "review":
            worker = ReviewWorker(settings)
            worker.run(args.pr)
            print(f"Successfully reviewed PR #{args.pr}")

        elif args.command == "fix":
            worker = FixWorker(settings)
            worker.run(args.pr)
            print(f"Successfully fixed PR #{args.pr}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
