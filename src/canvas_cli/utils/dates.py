"""Date parsing for Canvas due/lock dates.

Canvas stores dates as ISO-8601 UTC. Callers pass local time strings and are
responsible for their own timezone offset. This module just handles the parsing.
"""

import sys
from datetime import datetime


def parse_due(dt_str: str) -> str:
    """Parse 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD' → ISO-8601 string.

    No timezone conversion is applied. The caller must pass the date already
    adjusted to UTC if Canvas requires it (Canvas accepts UTC+00:00 strings).
    """
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(dt_str, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"
        except ValueError:
            continue
    sys.exit(f"Cannot parse date '{dt_str}'. Use 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'.")
