from pydantic import BaseModel, Field, ConfigDict, EmailStr

from datetime import datetime


# POST

class PostBase(BaseModel):
    title:str = Field(min_length=3, max_length=100)
    content:str = Field(min_length=3, max_length=500)

class PostCreate(PostBase):
    user_id : int # TEMP

# For PATCH
class PostUpdate(PostBase):
    title:str|None = None
    content:str|None = None

class PostResponse(PostBase):

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date_posted: datetime
    author: UserResponse

#  USER

class UserBase(BaseModel):
    username:str
    email:EmailStr

class UserCreate(UserBase):
    pass

# For PATCH
class UserUpdate(UserBase):
    username:str|None = None
    email:EmailStr|None = None
    image_file:str|None = None

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id:int
    image_file:str|None
    image_path:str