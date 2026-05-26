import sys
from ins账号自动化.main import (
    generate_and_queue,
    post_from_queue,
    generate_and_post,
    run_scheduler,
)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py gen [count]     Generate and queue images")
        print("  python main.py post [count]    Post from queue")
        print("  python main.py go [count]      Generate and post immediately")
        print("  python main.py schedule        Run scheduled posting")
        sys.exit(0)

    cmd = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    if cmd == "gen":
        generate_and_queue(count)
    elif cmd == "post":
        post_from_queue(count)
    elif cmd == "go":
        generate_and_post(count)
    elif cmd == "schedule":
        run_scheduler()
    else:
        print(f"Unknown command: {cmd}")
