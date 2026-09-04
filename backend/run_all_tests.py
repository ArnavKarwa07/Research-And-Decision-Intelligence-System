import sys
import os
import pytest

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    test_dir = os.path.join(backend_dir, "tests")
    args = [test_dir] + sys.argv[1:]
    exit_code = pytest.main(args)
    sys.exit(exit_code)

