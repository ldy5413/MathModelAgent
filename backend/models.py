from sqlmodel import Field, SQLModel

class Book(SQLModel, table=True):
    __tablename__ = "book"
    id: int | None = Field(default=None, primary_key=True)
    title: str
    author: str

class User(SQLModel, table=True):
    __tablename__ = "user"
    id: int | None = Field(default=None, primary_key=True)
    account: str
    password: str

class Token(SQLModel, table=True):
    __tablename__ = "token"
    id: int | None = Field(default=None, primary_key=True)
    access_token: str
    token_type: str
    user_id: int = Field(foreign_key="user.id")

class TokenData(SQLModel):
    username: str | None = None
