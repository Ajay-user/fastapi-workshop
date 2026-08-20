from typing import Annotated

from fastapi import FastAPI, status, Depends
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException


from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from database import Base, engine, get_db
# from schemas import PostCreate, PostResponse, UserCreate, UserResponse
# from models import User , Post
import models
import schemas

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
    posts = db.execute(select(models.Post)).scalars().all()
    return templates.TemplateResponse(request=request, name='home.html', context={'posts':posts, 'title':"Home"})


@app.get('/post/{post_id}', name='post_page', include_in_schema=False)
def post_page(request:Request, post_id:int, db:Annotated[Session, Depends(get_db)]):
    
    if post:= db.execute(select(models.Post).where(models.Post.id == post_id)).scalars().first():
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
    if existing_user:= db.execute(select(models.User).where(models.User.id == user_id)).scalars().first():
        posts = db.execute(select(models.Post).where(models.Post.user_id == user_id)).scalars().all()

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
@app.post('/api/user', response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user:schemas.UserCreate, db:Annotated[Session, Depends(get_db)]):

    # check if username already exists in db
    if existing_username:= db.execute(select(models.User).where(models.User.username == user.username)).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Username alread exists')
    # check if email already exists in db
    if existing_email:= db.execute(select(models.User).where(models.User.email == user.email)).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email alread exists')

    new_user = models.User(**user.model_dump())

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# Get a user
@app.get('/api/user/{user_id}', response_model=schemas.UserResponse, status_code=status.HTTP_200_OK)
def get_user(user_id:int, db:Annotated[Session, Depends(get_db)]):

    if existing_user:= db.execute(select(models.User).where(models.User.id == user_id)).scalars().first():
        return existing_user
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found, check ID")


# Get user posts
@app.get('/api/user/{user_id}/post', response_model=schemas.PostResponse, status_code=status.HTTP_201_CREATED)
def get_user_post(user_id:int, db:Annotated[Session,  Depends(get_db)]):
    # check if user exist
    if existing_user:= db.execute(select(models.User).where(models.User.id == user_id)).scalars().first():
        posts = db.execute(select(models.Post).where(models.Post.user_id == user_id)).scalars().all()
        return posts

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found, check ID")

# UPDATE user
@app.patch('/api/user/{user_id}', response_model=schemas.UserResponse, status_code=status.HTTP_200_OK)
def update_user(user_id:int, user_data:schemas.UserUpdate, db:Annotated[Session, Depends(get_db)]):
    # 1. Primary key lookup using db.get() (faster & cleaner in SQLAlchemy 2.0)
    # Return an instance based on the given primary key identifier, or None if not found
    if user := db.get(entity=models.User, ident=user_id ):

        # 2. Extract explicitly provided fields from the schema.
        # 'exclude_unset=True' ensures omitted fields aren't updated or overwritten with None.
        update_data = user_data.model_dump(exclude_unset=True)

        # 3. Dynamic Uniqueness Check: Check both username and email in a single SQL query
        new_username = update_data.get("username")
        new_email = update_data.get("email")

        checks = []
        if new_username and new_username != user.username:
            checks.append(models.User.username == new_username)
        if new_email and new_email != user.email:
            checks.append(models.User.email == new_email)

        if checks:
            # Check if another record matches either condition
            if existing_user := db.scalar(select(models.User).where(or_(*checks))):
                # Determine which field caused the conflict
                if new_username and existing_user.username == new_username:
                    details = "Username already exists"
                else:
                    details = "Email already exists"
                # Use HTTP 409 CONFLICT for resource duplication errors
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=details)

        # 4. Apply partial updates dynamically using Python's setattr
        for key, value in update_data.items():
            setattr(user, key, value)

        # 5. Save changes to DB and refresh model instance state
        db.commit()
        db.refresh(user)
        return user


    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found, check ID')

# Delete user
@app.delete('/api/user/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id:int, db:Annotated[Session, Depends(get_db)]):
    # 1. Primary key lookup using db.get() (faster & cleaner in SQLAlchemy 2.0)
    if user:= db.get(models.User, user_id):
        # Mark an instance as deleted.
        db.delete(user)
        # Flush pending changes and commit the current transaction.
        db.commit()
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found, check ID")


# GET all post
@app.get('/api/post', response_model=list[schemas.PostResponse])
def get_all_post(db:Annotated[Session, Depends(get_db)]):
    if posts:= db.execute(select(models.Post)).scalars().all():
        return posts
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
# GET a post
@app.get('/api/post/{post_id}', response_model=schemas.PostResponse)
def get_post(post_id:int, db:Annotated[Session, Depends(get_db)]):
    if post:= db.execute(select(models.Post).where(models.Post.id == post_id)).scalars().first():
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found, check ID')

# Create new POST
@app.post('/api/post', response_model=schemas.PostResponse)
def create_post(post:schemas.PostCreate, db:Annotated[Session, Depends(get_db)]):

    # check if user exist
    if existing_user:= db.execute(select(models.User).where(models.User.id == post.user_id)).scalars().first():

        post = models.Post(**post.model_dump())
        db.add(post)
        db.commit()
        db.refresh(post)
        return post
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User details not found, check ID')

# Update post >> replace 
@app.put('/api/post/{post_id}', response_model=schemas.PostResponse, status_code=status.HTTP_200_OK)
def update_post_full(post_id:int, post:schemas.PostCreate, db:Annotated[Session, Depends(get_db)]):

    # check if post exists and user who send the request is the author
    if existing_post := db.scalar(select(models.Post).where(models.Post.id == post_id)):

        # check if user is the author
        if existing_user:= db.execute(select(models.User).where(models.User.id == existing_post.user_id)).scalars().first():

            for key, value in post.model_dump().items():
                setattr(existing_post, key, value)

            db.commit()
            db.refresh(existing_post)
            return existing_post
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found, check ID')


# Update post >> patch
@app.patch('/api/post/{post_id}', response_model=schemas.PostResponse, status_code=status.HTTP_200_OK)
def update_post_partial(post_id:int, post:schemas.PostUpdate, db:Annotated[Session, Depends(get_db)]):

    # check if post exists and user who send the request is the author
    if existing_post := db.scalar(select(models.Post).where(models.Post.id == post_id)):

        # check if user is the author
        if existing_user:= db.execute(select(models.User).where(models.User.id == existing_post.user_id)).scalars().first():
          
            for key, value in post.model_dump(exclude_unset=True).items():
                setattr(existing_post, key, value)
                
            db.commit()
            db.refresh(existing_post)
            return existing_post
            
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found, check ID')




# Delete post
@app.delete('/api/post/{post_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id:int, db:Annotated[Session, Depends(get_db)]):

    # check if post exists and user who send the request is the author
    if existing_post := db.scalar(select(models.Post).where(models.Post.id == post_id)):

        # check if user is the author
        if existing_user:= db.execute(select(models.User).where(models.User.id == existing_post.user_id)).scalars().first():

            db.delete(existing_post)
            db.commit()
            return existing_post
            
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found, check ID')




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