"""CrossERP test package.

Keeping the test tree as an explicit package makes imports such as
``tests.fixtures`` deterministic on Python installations that already expose
an unrelated top-level package named ``tests``.
"""
