"""Storage and retrieval utilities for Milestone 1."""
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv('BUG_DATA_DIR', str(BASE / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA / 'bugs.sqlite3'
VECTOR_PATH = DATA / 'chroma'
MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')


def connection():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connection() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, description TEXT NOT NULL,
            stack_trace TEXT NOT NULL DEFAULT '', error_logs TEXT NOT NULL DEFAULT '',
            filename TEXT, created_at TEXT NOT NULL)''')
        db.commit()


def save_submission(title, description, stack_trace='', error_logs='', filename=None):
    with connection() as db:
        cur = db.execute('''INSERT INTO submissions
            (title,description,stack_trace,error_logs,filename,created_at)
            VALUES (?,?,?,?,?,?)''', (title, description, stack_trace, error_logs,
            filename, datetime.now(timezone.utc).isoformat()))
        db.commit()
        return cur.lastrowid


def get_submission(bug_id):
    with connection() as db:
        row = db.execute('SELECT * FROM submissions WHERE id=?', (bug_id,)).fetchone()
    return dict(row) if row else None


def clean_text(value):
    value = str(value or '').replace('\x00', '')
    value = re.sub(r'\r\n?', '\n', value)
    return '\n'.join(re.sub(r'[ \t]+', ' ', line).strip() for line in value.split('\n')).strip()


def chunks(text, max_chars=900, overlap=120):
    """Character-based overlapping chunks. Keep stack traces separately from prose."""
    text = clean_text(text)
    if not text:
        return []
    output = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            boundary = text.rfind('\n', start + max_chars // 2, end)
            if boundary > start:
                end = boundary
        part = text[start:end].strip()
        if part:
            output.append(part)
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return output


class Retrieval:
    def __init__(self):
        import chromadb
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(MODEL)
        self.client = chromadb.PersistentClient(path=str(VECTOR_PATH))
        self.collection = self.client.get_or_create_collection(
            name='historical_defects_v1', metadata={'hnsw:space': 'cosine'})

    def embed(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def index(self, records):
        documents, metadata, ids = [], [], []
        for record in records:
            source = clean_text(record.get('source', 'unknown')) or 'unknown'
            bug_id = clean_text(record.get('bug_id', ''))
            if not bug_id:
                continue
            for section in ('title', 'description', 'stack_trace', 'comments', 'resolution'):
                for idx, piece in enumerate(chunks(record.get(section, ''))):
                    # unique stable ID scoped by origin, bug and section
                    ids.append(f'{source}:{bug_id}:{section}:{idx}')
                    documents.append(f'{section}: {piece}')
                    metadata.append({'source': source, 'bug_id': bug_id, 'section': section,
                        'title': clean_text(record.get('title', ''))[:500],
                        'status': clean_text(record.get('status', 'unknown'))[:100],
                        'resolution': clean_text(record.get('resolution', ''))[:500],
                        'url': clean_text(record.get('url', ''))[:500]})
        for start in range(0, len(documents), 64):
            stop = start + 64
            part = documents[start:stop]
            self.collection.upsert(ids=ids[start:stop], documents=part,
                metadatas=metadata[start:stop], embeddings=self.embed(part))
        return {'indexed_chunks': len(ids), 'collection_total': self.collection.count()}

    def search(self, query, top_k=5):
        if not query.strip() or self.collection.count() == 0:
            return []
        response = self.collection.query(query_embeddings=self.embed([query]),
            n_results=min(top_k * 4, self.collection.count()),
            include=['documents', 'metadatas', 'distances'])
        results = []
        seen = set()
        for doc, meta, dist in zip(response['documents'][0], response['metadatas'][0],
                                    response['distances'][0]):
            key = (meta['source'], meta['bug_id'])
            if key in seen:
                continue
            seen.add(key)
            results.append({'bug_id': meta['bug_id'], 'source': meta['source'],
                'title': meta['title'], 'section': meta['section'],
                'status': meta['status'], 'resolution': meta['resolution'],
                'url': meta['url'], 'excerpt': doc[:650],
                'similarity': round(max(0.0, min(1.0, 1.0 - float(dist))), 4)})
            if len(results) == top_k:
                break
        return results
