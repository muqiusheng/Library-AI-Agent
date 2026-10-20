from app.integrations.courses.base import CourseCatalogProvider, CourseOption

_COURSES = (
    ("CS101", "程序设计基础", "专业基础"),
    ("CS102", "计算机导论", "专业基础"),
    ("CS201", "数据结构", "专业核心"),
    ("CS202", "面向对象程序设计", "专业核心"),
    ("CS203", "数据库原理", "专业核心"),
    ("CS204", "计算机组成原理", "专业核心"),
    ("CS205", "操作系统", "专业核心"),
    ("CS206", "计算机网络", "专业核心"),
    ("CS301", "软件工程", "专业方向"),
    ("CS302", "Java Web 应用开发", "专业方向"),
    ("AI301", "人工智能导论", "专业方向"),
    ("AI302", "机器学习", "专业方向"),
    ("DS301", "数据分析与可视化", "专业方向"),
    ("MATH101", "高等数学", "公共基础"),
    ("MATH201", "线性代数", "公共基础"),
    ("MATH202", "概率论与数理统计", "公共基础"),
)


class LocalCourseCatalogProvider(CourseCatalogProvider):
    def list_courses(
        self,
        *,
        major: str | None = None,
        grade: str | None = None,
        query: str | None = None,
    ) -> list[CourseOption]:
        del major, grade  # Reserved for adapters backed by a teaching management system.
        normalized_query = (query or "").strip().casefold()
        return [
            CourseOption(code=code, name=name, category=category, source="local")
            for code, name, category in _COURSES
            if not normalized_query
            or normalized_query in name.casefold()
            or normalized_query in code.casefold()
        ]
