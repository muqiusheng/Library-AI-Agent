from pydantic import BaseModel


class CourseOptionRead(BaseModel):
    code: str
    name: str
    category: str
    source: str
