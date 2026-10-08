"""Bootstrap Windows: espera la asignación a Job antes de crear descendientes."""
import subprocess
import sys


def main():
    if sys.stdin.buffer.readline()!=b'GO\n': return 125
    try:
        return subprocess.call(sys.argv[1:],stdin=subprocess.DEVNULL)
    except OSError as exc:
        print(f'process_host: {exc}',file=sys.stderr)
        return 125


if __name__=='__main__': raise SystemExit(main())
