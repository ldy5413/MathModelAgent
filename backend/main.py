from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",  # 前端开发服务器
    "http://localhost:5173",  # Vite 开发服务器备选端口
    "https://mathmode.zeabur.app",  # 生产环境
]
# 跨域 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    return "hello world"


# @app.get("/items/{item_id}")
# async def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": item_id, "q": q}


# @app.get("/books")
# async def get_books(db: SessionDep,token:str=Depends(oauth2_scheme)) -> List[Book]:
#     user = await authenticate_token(db,token)
#     if not user:
#         raise HTTPException(status_code=401, detail="无效的token,请重新登录")
#     return db.exec(select(Book)).all()

# @app.post("/token",response_model=Token)
# async def login_for_access_token(db:SessionDep,form_data:OAuth2PasswordRequestForm=Depends()):
#     user = await authenticate_user(db,form_data.username,form_data.password)
#     if not user:
#         raise HTTPException(status_code=401,detail="用户名或密码错误")
#     access_token_expires = timedelta(minutes=30)
#     access_token = create_access_token(
#         data={"sub": user.account},
#         expires_delta=access_token_expires
#     )
#     return Token(
#         access_token=access_token,
#         token_type="bearer",
#         user_id=user.id
#     )
