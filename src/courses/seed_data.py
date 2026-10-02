from src.courses.entities import CourseEntity, LessonEntity, ModuleEntity

PYTHON_VIDEO = "https://www.youtube.com/watch?v=rfscVS0vtbw"

# Demonstration outlines share a general Python guide, not lesson-specific recordings.
COURSES = (
    CourseEntity(
        slug="demo-python-foundations",
        title="Python foundations (demo)",
        description="Demonstration content for the course catalog and free module preview.",
        is_published=True,
        modules=(
            ModuleEntity(
                title="Getting started",
                description="Values, expressions, and functions.",
                position=1,
                lessons=(
                    LessonEntity(
                        title="Values and types",
                        position=1,
                        summary=(
                            "Python values have types such as int, str, and bool. "
                            "Use descriptive names and convert input before calculations."
                        ),
                        video_url=PYTHON_VIDEO,
                    ),
                    LessonEntity(
                        title="Functions",
                        position=2,
                        summary=(
                            "A function groups a reusable operation. Define clear parameters, "
                            "return a result, and test its behavior with representative inputs."
                        ),
                        video_url=PYTHON_VIDEO,
                    ),
                ),
            ),
            ModuleEntity(
                title="Working with collections",
                description="Lists and dictionaries.",
                position=2,
                lessons=(
                    LessonEntity(
                        title="Lists",
                        position=1,
                        summary=(
                            "Lists store ordered collections. Iterate over values directly "
                            "and avoid changing the list while iterating over it."
                        ),
                        video_url=PYTHON_VIDEO,
                    ),
                    LessonEntity(
                        title="Dictionaries",
                        position=2,
                        summary=(
                            "Dictionaries map unique keys to values. Use get for optional keys "
                            "and validate required keys at application boundaries."
                        ),
                        video_url=PYTHON_VIDEO,
                    ),
                ),
            ),
        ),
    ),
    CourseEntity(
        slug="demo-python-backend",
        title="Python backend concepts (demo)",
        description="An illustrative backend course with a free first module.",
        is_published=True,
        modules=(
            ModuleEntity(
                title="Request handling",
                description="Input and response boundaries.",
                position=1,
                lessons=(
                    LessonEntity(
                        title="Validation",
                        position=1,
                        summary=(
                            "Validate request data before using it. Keep transport DTOs distinct "
                            "from stored credentials and return consistent error responses."
                        ),
                        video_url=PYTHON_VIDEO,
                    ),
                ),
            ),
            ModuleEntity(
                title="Persistence",
                description="Transactional boundaries.",
                position=2,
                lessons=(
                    LessonEntity(
                        title="Transactions",
                        position=1,
                        summary=(
                            "A transaction groups related changes into one operation. Services own "
                            "the transaction; repositories flush changes without committing them."
                        ),
                        video_url=PYTHON_VIDEO,
                    ),
                ),
            ),
        ),
    ),
)
