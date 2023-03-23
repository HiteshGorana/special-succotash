from pydantic import BaseModel


class Report(BaseModel):
    report_id: str
