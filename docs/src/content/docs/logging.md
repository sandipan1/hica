---
title: Logging
---

HICA uses `structlog` for structured logs with per-thread log files.

## Defaults

- Log file per thread: `logs/thread_<id>.log`\n- Log level from `HICA_LOG_LEVEL` (default INFO)\n- Console logging is opt-in with `HICA_CONSOLE=1`\n\n## Best practices\n\n- Enable console in development; keep file handlers in production.\n- Bind useful metadata (thread_id, tool name) to logs.\n*** End Patch

