from pydantic import BaseModel


class ResourceClass(BaseModel):
    name: str

    class Config:
        orm_mode = True
