from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .core import Retrieval, clean_text, get_submission, init_db, save_submission

app = FastAPI(title='Intelligent Bug Diagnosis — Milestone 1', version='0.1.0')
app.mount('/static', StaticFiles(directory=Path(__file__).parent / 'static'), name='static')
init_db()
_retrieval = None
ALLOWED = {'.txt', '.log', '.json', '.csv', '.md'}
MAX_FILE = 2 * 1024 * 1024
MAX_TEXT = 150_000


def retrieval():
    global _retrieval
    if _retrieval is None:
        _retrieval = Retrieval()
    return _retrieval


class SearchBody(BaseModel):
    query: str = Field(min_length=3, max_length=10000)
    top_k: int = Field(default=5, ge=1, le=20)


@app.get('/')
def home():
    return FileResponse(Path(__file__).parent / 'static' / 'index.html')


@app.get('/api/health')
def health():
    return {'status': 'ok', 'milestone': 1}


@app.post('/api/bugs', status_code=201)
async def create_bug(title: str = Form(...), description: str = Form(''),
                     stack_trace: str = Form(''), error_logs: str = Form(''),
                     file: UploadFile | None = File(None)):
    title, description = clean_text(title), clean_text(description)
    stack_trace, error_logs = clean_text(stack_trace), clean_text(error_logs)
    if not title or len(title) > 300:
        raise HTTPException(422, 'Title must be 1–300 characters')
    filename = None
    if file and file.filename:
        filename = Path(file.filename).name
        if Path(filename).suffix.lower() not in ALLOWED:
            raise HTTPException(415, 'Allowed file types: .txt, .log, .json, .csv, .md')
        raw = await file.read(MAX_FILE + 1)
        if len(raw) > MAX_FILE:
            raise HTTPException(413, 'Upload must be 2 MB or less')
        try:
            extracted = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise HTTPException(422, 'File must contain UTF-8 text')
        error_logs = (error_logs + '\n' + clean_text(extracted)).strip()
    if not (description or stack_trace or error_logs):
        raise HTTPException(422, 'Add a description, stack trace, error log, or file')
    if sum(map(len, (description, stack_trace, error_logs))) > MAX_TEXT:
        raise HTTPException(413, 'Combined text is too large (150,000 characters)')
    bug_id = save_submission(title, description, stack_trace, error_logs, filename)
    return {'id': bug_id, 'message': 'Bug submitted and stored successfully'}


@app.get('/api/bugs/{bug_id}')
def read_bug(bug_id: int):
    bug = get_submission(bug_id)
    if not bug:
        raise HTTPException(404, 'Bug not found')
    return bug


@app.post('/api/search')
def search(body: SearchBody):
    try:
        hits = retrieval().search(body.query, body.top_k)
    except Exception as exc:
        raise HTTPException(503, 'Retrieval unavailable. Check embedding model and vector store installation.') from exc
    return {'results': hits, 'count': len(hits),
            'notice': 'Similarity is evidence for review, not an automatic confirmed duplicate or fix.'}
