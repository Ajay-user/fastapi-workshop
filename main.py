from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

 
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


@app.get('/api/post')
def get_all_post():
    return POST