from fastapi import FastAPI, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

 
app = FastAPI()
app.mount(path='/static', app=StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')



POST : list[dict] = [
    {
        "id": 1,
        "author": "Corey Schafer",
        "title": "FastAPI is Awesome",
        "content": "This framework is really easy to use and super fast.",
        "date_posted": "April 20, 2025",
    },
    {
        "id": 2,
        "author": "Jane Doe",
        "title": "Python is Great for Web Development",
        "content": "Python is a great language for web development, and FastAPI makes it even better.",
        "date_posted": "April 21, 2025",
    },
]

@app.get('/', include_in_schema=False)
@app.get('/post', include_in_schema=False)
def home(request:Request):
    return templates.TemplateResponse(request=request, name='home.html', context={'posts':POST, 'title':"Home"})


@app.get('/post/{post_id}', name='post_page')
def post_page(request:Request, post_id:int):
    for post in POST:
        if post.get('id') == post_id:
            return templates.TemplateResponse(
                request=request, name='post.html', 
                context={'post':post, 'title': post['title']}
            )
    return templates.TemplateResponse(
        request=request, name='error.html',
        context={'title':'404', 'status_code':404, 'message':'Post Not Found'}
    )

#  -- API


@app.get('/api/post')
def get_all_post():
    return POST

@app.get('/api/post/{post_id}')
def get_post(post_id:int):
    for post in POST:
        if post.get('id') == post_id:
            return {'status':200, 'content':post}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post ID not found')



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