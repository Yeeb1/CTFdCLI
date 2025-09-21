"""Helper utilities for CTFd CLI."""

import re
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    elif seconds < 86400:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"
    else:
        days = seconds // 86400
        remaining_hours = (seconds % 86400) // 3600
        return f"{days}d {remaining_hours}h"


def validate_url(url: str) -> bool:
    """Validate if a URL is properly formatted.

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe filesystem usage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)

    # Trim whitespace and dots
    sanitized = sanitized.strip(' .')

    # Ensure not empty
    if not sanitized:
        sanitized = "unnamed"

    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]

    return sanitized


def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate text to specified length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def get_difficulty_color(points: int) -> str:
    """Get color for difficulty based on points.

    Args:
        points: Challenge points

    Returns:
        Color name for Rich formatting
    """
    if points <= 100:
        return "green"
    elif points <= 300:
        return "yellow"
    elif points <= 500:
        return "orange"
    else:
        return "red"


def parse_flag_format(flag: str) -> tuple[str, str]:
    """Parse flag format and extract prefix and content.

    Args:
        flag: Flag string

    Returns:
        Tuple of (prefix, content)
    """
    # Common CTF flag formats
    patterns = [
        r'^(flag|FLAG)\{(.+)\}$',
        r'^([A-Z]+)\{(.+)\}$',
        r'^([a-zA-Z0-9_-]+)\{(.+)\}$'
    ]

    for pattern in patterns:
        match = re.match(pattern, flag)
        if match:
            return match.group(1), match.group(2)

    # If no pattern matches, return the whole flag as content
    return "", flag


def create_challenge_directory(base_path: Path, category: str, challenge_name: str) -> Path:
    """Create directory structure for a challenge.

    Args:
        base_path: Base directory path
        category: Challenge category
        challenge_name: Challenge name

    Returns:
        Created challenge directory path
    """
    # Sanitize names
    safe_category = sanitize_filename(category)
    safe_name = sanitize_filename(challenge_name)

    # Create directory structure
    challenge_dir = base_path / safe_category / safe_name
    challenge_dir.mkdir(parents=True, exist_ok=True)

    return challenge_dir


def format_score(score: int) -> str:
    """Format score with thousand separators.

    Args:
        score: Score value

    Returns:
        Formatted score string
    """
    return f"{score:,}"


def calculate_percentile(position: int, total: int) -> float:
    """Calculate percentile based on position.

    Args:
        position: Current position (1-indexed)
        total: Total participants

    Returns:
        Percentile (0-100)
    """
    if total <= 0:
        return 0.0

    return ((total - position + 1) / total) * 100


def time_since(timestamp: Optional[datetime]) -> str:
    """Calculate time since a timestamp.

    Args:
        timestamp: Datetime timestamp

    Returns:
        Human-readable time difference
    """
    if not timestamp:
        return "Unknown"

    now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
    diff = now - timestamp

    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hours ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minutes ago"
    else:
        return "Just now"


def validate_challenge_id(challenge_id_str: str) -> Optional[int]:
    """Validate and convert challenge ID string to integer.

    Args:
        challenge_id_str: Challenge ID as string

    Returns:
        Challenge ID as integer or None if invalid
    """
    try:
        challenge_id = int(challenge_id_str)
        if challenge_id > 0:
            return challenge_id
    except ValueError:
        pass

    return None