import multiprocessing

# Frozen Windows process-pool children re-enter this executable with
# --multiprocessing-fork. Dispatch them before importing/starting the GUI.
multiprocessing.freeze_support()

from motorsim.dino_desktop import main

if __name__ == "__main__":
    raise SystemExit(main())
