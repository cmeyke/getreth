import subprocess
import sys
from pathlib import Path


def main():
    # Invoke the balance checker using the environment defaults (-e flag).
    script_path = Path(__file__).with_name("eth_balance.py")
    try:
        subprocess.run([sys.executable, str(script_path), "-e"], check=True)
    except subprocess.CalledProcessError as exc:
        print(
            f"Balance checker failed with exit code {exc.returncode}",
            file=sys.stderr,
        )
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
