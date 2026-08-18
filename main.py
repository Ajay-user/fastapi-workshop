from typing import Annotated

from fastapi import FastAPI, status, Depends
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException


from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from schemas import PostCreate, PostResponse, UserCreate, UserResponse
from models import User , Post

Base.metadata.create_all(bind=engine)
 
app = FastAPI()
# static file serving
app.mount(path='/static', app=StaticFiles(directory='static'), name='static')
# user uploaded media
app.mount(path='/media', app=StaticFiles(directory='media'), name='media')
templates = Jinja2Templates(directory='templates')





@app.get('/', include_in_schema=False)
@app.get('/post', include_in_schema=False)
def home(request:Request, db:Annotated[Session, Depends(get_db)]):
    posts = db.execute(select(Post)).scalars().all()
    return templates.TemplateResponse(request=request, name='home.html', context={'posts':posts, 'title':"Home"})


@app.get('/post/{post_id}', name='post_page', include_in_schema=False)
def post_page(request:Request, post_id:int, db:Annotated[Session, Depends(get_db)]):
    
    if post:= db.execute(select(Post).where(Post.id == post_id)).scalars().first():
        return templates.TemplateResponse(
            request=request, name='post.html', 
            context={'post':post, 'title': post['title']}
        )
    
    return templates.TemplateResponse(
        request=request, name='error.html',
        context={'title':'404', 'status_code':404, 'message':'Post Not Found'}
    )

@app.get('/user/{user_id}/post', name='user_post_page', include_in_schema=False)
def user_post_page(request:Request, user_id:int, db:Annotated[Session, Depends(get_db)]):

    # check if user exist
    if existing_user:= db.execute(select(User).where(User.id == user_id)).scalars().first():
        posts = db.execute(select(Post).where(Post.user_id == user_id)).scalars().all()

        return templates.TemplateResponse(
            request=request, name='user_posts.html', 
            context={'posts':posts, 'user':existing_user, 'title': f"{existing_user.username}'s posts"}
        )
    
    return templates.TemplateResponse(
        request=request, name='error.html',
        context={'title':'404', 'status_code':404, 'message':'User ID Not Found'}
    )




#  -- API

# Create a new user
@app.post('/api/user', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user:UserCreate, db:Annotated[Session, Depends(get_db)]):

    # check if username already exists in db
    if existing_username:= db.execute(select(User).where(User.username == user.username)).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Username alread exists')
    # check if email already exists in db
    if existing_email:= db.execute(select(User).where(User.email == user.email)).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email alread exists')

    new_user = User(**user.model_dump())

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# Get a user
@app.get('/api/user/{user_id}', response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(user_id:int, db:Annotated[Session, Depends(get_db)]):

    if existing_user:= db.execute(select(User).where(User.id == user_id)).scalars().first():
        return existing_user
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


# Get user posts
@app.get('/api/user/{user_id}/post', response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def get_user_post(user_id:int, db:Annotated[Session,  Depends(get_db)]):
    # check if user exist
    if existing_user:= db.execute(select(User).where(User.id == user_id)).scalars().first():
        posts = db.execute(select(Post).where(Post.user_id == user_id)).scalars().all()
        return posts

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")





# GET all post
@app.get('/api/post', response_model=list[PostResponse])
def get_all_post(db:Annotated[Session, Depends(get_db)]):
    if posts:= db.execute(select(Post)).scalars().all():
        return posts
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
# GET a post
@app.get('/api/post/{post_id}', response_model=PostResponse)
def get_post(post_id:int, db:Annotated[Session, Depends(get_db)]):
    if post:= db.execute(select(Post).where(Post.id == post_id)).scalars().first():
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post ID not found')

# Create new POST
@app.post('/api/post', response_model=PostResponse)
def create_post(post:PostCreate, db:Annotated[Session, Depends(get_db)]):

    # check if user exist
    if existing_user:= db.execute(select(User).where(User.id == post.user_id)).scalars().first():

        post = Post(**post.model_dump())
        db.add(post)
        db.commit()
        db.refresh(post)
        return post
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User details not found, check ID')


# --- 

# EXCEPTION HANDLER 
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request:Request, exception:StarletteHTTPException):
    message = exception.detail if exception.detail else "An error occurred. Please check your request and try again."

    if request.url.path.startswith('/api'):
        return JSONResponse(status_code=exception.status_code, content=message)
    
    return templates.TemplateResponse(
        request=request,
        name='error.html',
        context={
            'title': exception.status_code,
            'message': message,
            'status_code': exception.status_code
        },
        status_code=exception.status_code
    )




# for validation errors we dont get a message , we get a list of validation errors
# eg: request url : http://127.0.0.1:8000/api/post/hello
# {
# "detail":[
#   {
#       "type":"int_parsing",
#       "loc":["path","post_id"],
#       "msg":"Input should be a valid integer, unable to parse string as an integer",
#       "input":"hello"
#    }
#           ]
# }

@app.exception_handler(RequestValidationError)
def request_validation_exception_handler(request:Request, exception:RequestValidationError):

    if request.url.path.startswith('/api'):
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=exception.errors())
    
    return templates.TemplateResponse(
        request=request,
        name='error.html',
        context={
            'title': status.HTTP_422_UNPROCESSABLE_CONTENT,
            'message': "Invalid request",
            'status_code': status.HTTP_422_UNPROCESSABLE_CONTENT
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )