# backend/app/models/consultation.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class ConsultationCreate(BaseModel):
    firstName: str = Field(..., min_length=1)
    lastName: str = Field(..., min_length=1)
    age: int = Field(..., gt=0, lt=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    height: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)
    email: EmailStr
    mobile: str = Field(..., min_length=10)

    class Config:
        json_schema_extra = {
            "example": {
                "firstName": "John",
                "lastName": "Doe",
                "age": 30,
                "gender": "male",
                "height": 175.0,
                "weight": 70.0,
                "email": "john.doe@example.com",
                "mobile": "1234567890"
            }
        }

