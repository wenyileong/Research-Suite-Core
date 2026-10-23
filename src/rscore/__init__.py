"""Shared core for the research software suite.

The core holds what the suite's tools share: one data model, one jurisdiction registry, provenance for
every value and snapshots that let any figure be regenerated. It uses the Python standard library only,
so that it adds nothing to the size of a tool's Windows executable.

See ``docs/data_model_v1.md`` for the model and ``docs/cleanroom/README.md`` for how open-source ideas
are used.
"""

__version__ = "0.4.0"

#: Generation of the store schema. Raised whenever a migration is added to ``rscore.store``.
SCHEMA_GENERATION = 1
