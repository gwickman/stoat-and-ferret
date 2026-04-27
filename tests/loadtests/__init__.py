"""Load tests (BL-289).

This package is excluded from the default pytest run (see ``pyproject.toml``
``addopts``) and is executed on-demand via the ``locust`` CLI:

    locust -f tests/loadtests/locustfile.py -u 50 -r 10 -t 5m \\
        --headless --host http://localhost:8765

Run against a server started with ``STOAT_RENDER_MODE=noop`` and
``STOAT_TESTING_MODE=true`` so render and seed endpoints behave
synthetically.
"""
