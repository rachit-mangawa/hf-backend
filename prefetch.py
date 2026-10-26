"""Build-time model prefetch script.

Reads project routes from registry.py and invokes warmup() on each
top-level package to bake weights into the Docker image filesystem.
"""

import importlib
import logging
import sys

from registry import PROJECT_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("prefetch")


def main():
    logger.info("Starting model prefetch during build...")
    for prefix, target in PROJECT_REGISTRY.items():
        module_name = target.split(":")[0]
        top_pkg_name = module_name.split(".")[0]
        logger.info(f"[{prefix}] Checking warmup for package '{top_pkg_name}'...")
        try:
            pkg = importlib.import_module(top_pkg_name)
            warmup_fn = getattr(pkg, "warmup", None)
            if warmup_fn and callable(warmup_fn):
                logger.info(f"[{prefix}] Running warmup() for '{top_pkg_name}'...")
                warmup_fn()
                logger.info(f"[{prefix}] Prefetch complete for '{top_pkg_name}'")
            else:
                logger.info(f"[{prefix}] No callable warmup() found for '{top_pkg_name}'")
        except Exception as e:
            logger.error(f"[{prefix}] Prefetch failed: {e}", exc_info=True)
            sys.exit(1)

    logger.info("All project models prefetched successfully.")


if __name__ == "__main__":
    main()
