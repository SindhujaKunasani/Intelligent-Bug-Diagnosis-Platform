from app.core import clean_text, chunks
from scripts.ingest import normalize


def test_clean_text():
    assert clean_text(' a  b\r\n c ') == 'a b\nc'


def test_chunks_overlap():
    parts = chunks('A' * 1200, max_chars=500, overlap=100)
    assert len(parts) >= 3
    assert parts[0][-100:] == parts[1][:100]


def test_normalize_bugzilla_aliases():
    bug = normalize({'bugid': 42, 'summary': 'Crash', 'status': 'NEW'}, 'Mozilla')
    assert bug['bug_id'] == '42'
    assert bug['title'] == 'Crash'
    assert bug['source'] == 'Mozilla'
