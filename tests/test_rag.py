import requests

from app import rag
from app.rag import Retriever

CHUNKS = [
    {"source": "a.md", "text": "Salary is a monthly gross amount in Indian rupees."},
    {"source": "a.md", "text": "Employees who joined before 2019 are considered senior staff."},
    {"source": "a.md", "text": "Departments are IT, HR, Finance, Sales and Marketing."},
]


def test_keyword_search_finds_the_right_chunk():
    top = Retriever(CHUNKS).search("what currency is salary paid in rupees", k=1)[0]
    assert "rupees" in top["text"]
    assert "senior" in Retriever(CHUNKS).search("who counts as senior", k=1)[0]["text"]


def test_irrelevant_query_returns_nothing():
    assert Retriever(CHUNKS).search("quantum chromodynamics lagrangian") == []


def test_embedding_mode_uses_vectors():
    vectors = {CHUNKS[0]["text"]: [1, 0], CHUNKS[1]["text"]: [0, 1], CHUNKS[2]["text"]: [0.5, 0.5], "pay?": [0, 1]}
    r = Retriever(CHUNKS, mode="embeddings", embed=lambda t: vectors[t])
    assert "senior" in r.search("pay?", k=1)[0]["text"]  # picked by vector, not by words


def test_embedding_failure_falls_back_to_keywords():
    def broken(_):
        raise requests.ConnectionError("no ollama")
    r = Retriever(CHUNKS, mode="embeddings", embed=broken)
    assert "rupees" in r.search("salary rupees", k=1)[0]["text"]


def test_load_chunks_from_folder(tmp_path):
    (tmp_path / "x.md").write_text("# Title\nsome intro text that is long enough\n\n## Part\nanother section with enough text")
    chunks = rag.load_chunks(tmp_path)
    assert len(chunks) == 2 and chunks[0]["source"] == "x.md"
    assert rag.load_chunks(tmp_path / "missing") == []
