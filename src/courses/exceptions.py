class ContentNotFound(Exception):
    """Published content does not exist within the requested hierarchy."""


class LessonAccessDenied(Exception):
    """Lesson content requires course access."""
