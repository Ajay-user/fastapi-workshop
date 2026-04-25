from fastapi import FastAPI


app = FastAPI()


POST = [
    {'id':1, 'name':'Ajay', 'post':'hello'},
    {'id':1, 'name':'Jay', 'post':'hello'},
    {'id':1, 'name':'Sal', 'post':'hello'},
    {'id':1, 'name':'Mira', 'post':'hello'},
    {'id':1, 'name':'Kumar', 'post':'hello'},
]


@app.get('/api/post')
def get_all_post():
    return POST