from bson import ObjectId
from pydantic import BaseModel, ConfigDict


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(str(v))

    @classmethod
    def __get_pydantic_json_schema__(cls, schema):
        return {"type": "string"}


class MongoModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="ignore",
        json_encoders={ObjectId: str},
    )

