import hashlib, io, subprocess
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.config import Settings
from app.db.database import Database
from app.db.migrate import upgrade_database
from app.decisions.repository import DecisionRepository
from app.decisions.schemas import DecisionBrief
from app.evidence.extraction import extract_pages, chunks
from app.evidence.schemas import SearchRequest
from app.evidence.repository import EvidenceRepository
from app.core.errors import BackendError

TEXT = b"Only a library pilot is approved. Full deployment is not approved.\r\nReview after four weeks."


def session(client):
    r = client.post("/api/v1/sessions", json={"query": "Is full deployment approved?"})
    assert r.status_code == 201, r.text
    return "/api/v1/sessions/" + r.json()["session_id"]


def upload(client, path, raw=TEXT, name="policy.txt", mime="text/plain"):
    return client.post(
        path + "/documents",
        params={"filename": name, "expected_session_revision": 1},
        content=raw,
        headers={"Content-Type": mime},
    )


def search(client, path, **extra):
    return client.post(
        path + "/evidence/search",
        json={"query": "full deployment approved", "expected_session_revision": 1}
        | extra,
    )


def test_upload_hash_download_offsets_and_real_retrieval(client):
    p = session(client)
    r = upload(client, p)
    assert r.status_code == 201, r.text
    d = r.json()
    assert (
        d["sha256"] == hashlib.sha256(TEXT).hexdigest()
        and d["authenticity_verified"] is False
    )
    assert client.get(p + "/documents/" + d["document_id"] + "/content").content == TEXT
    page = client.get(p + "/documents/" + d["document_id"] + "/pages/1").json()["text"]
    result = search(client, p)
    assert result.status_code == 201, result.text
    s = result.json()
    assert (
        s["semantic_support_verified"] is False
        and s["retrieval_method"] == "lexical-bm25-v1"
    )
    hit = s["passages"][0]
    assert page[hit["start_char"] : hit["end_char"]] == hit["excerpt"]
    assert (
        hit["document_version_id"] == d["version_id"]
        and hit["document_sha256"] == d["sha256"]
    )
    assert client.get(p + "/evidence/snapshots/" + s["snapshot_id"]).json() == s
    assert (
        "attachment"
        in client.get(p + "/documents/" + d["document_id"] + "/content").headers[
            "content-disposition"
        ]
    )


def test_duplicate_upload_is_idempotent_within_session(client):
    p = session(client)
    first = upload(client, p).json()
    second = upload(client, p, name="renamed.txt").json()
    assert first == second and len(client.get(p + "/documents").json()) == 1


def test_cross_session_documents_and_snapshots_are_rejected(client):
    p, q = session(client), session(client)
    d = upload(client, p).json()
    s = search(client, p).json()
    assert search(client, q, document_ids=[d["document_id"]]).status_code == 404
    assert (
        client.get(q + "/documents/" + d["document_id"] + "/content").status_code == 404
    )
    assert client.get(q + "/evidence/snapshots/" + s["snapshot_id"]).status_code == 404
    assert upload(client, q).json()["document_id"] != d["document_id"]


@pytest.mark.parametrize(
    "raw,name,mime,code",
    [
        (b"", "x.txt", "text/plain", 413),
        (b"\xff", "x.txt", "text/plain", 422),
        (b"hello\x00world", "x.txt", "text/plain", 422),
        (b" " * 10, "x.txt", "text/plain", 422),
        (b"%PDF-garbage", "x.pdf", "application/pdf", 422),
        (b"not pdf", "x.pdf", "application/pdf", 422),
        (TEXT, "../x.txt", "text/plain", 422),
        (TEXT, "x.exe", "text/plain", 422),
        (TEXT, "x.pdf", "text/plain", 415),
        (TEXT, "x.txt", "application/json", 415),
        (b"x" * 1048577, "x.txt", "text/plain", 413),
        (b"x" * 100001, "x.txt", "text/plain", 422),
    ],
)
def test_bad_upload_never_saves_a_document(client, raw, name, mime, code):
    p = session(client)
    assert upload(client, p, raw, name, mime).status_code == code
    assert client.get(p + "/documents").json() == []


def test_empty_corpus_and_nonmatching_query_are_honest(client):
    p = session(client)
    assert search(client, p).json()["passages"] == []
    upload(client, p)
    assert search(client, p, query="unfindablexyz").json()["passages"] == []
    assert search(client, p, query="the and is").json()["passages"] == []


def test_retrieval_filters_stale_revision_and_limits(client):
    p = session(client)
    a = upload(client, p).json()
    b = upload(
        client, p, b"Pilot deployment requires testing.", "other.md", "text/markdown"
    ).json()
    s = search(client, p, document_ids=[a["document_id"]]).json()
    assert s["document_version_ids"] == [a["version_id"]]
    assert search(client, p, document_ids=[a["document_id"]] * 2).status_code == 422
    assert search(client, p, limit=6).status_code == 422
    assert search(client, p, posterior=0.9).status_code == 422
    assert search(client, p, expected_session_revision=2).status_code == 409
    assert upload(client, "/api/v1/sessions/" + str(uuid4())).status_code == 404
    assert len(client.get(p + "/documents").json()) == 2


def test_utf8_line_endings_and_multilingual_passages(client):
    p = session(client)
    raw = "ज्ञान ग्रंथ\r\nknowledge\rresearch".encode("utf-8")
    d = upload(client, p, raw, name="ज्ञान.txt").json()
    page = client.get(p + "/documents/" + d["document_id"] + "/pages/1").json()["text"]
    assert "\r" not in page and search(client, p, query="ज्ञान").json()["passages"]
    assert (
        client.get(p + "/documents/" + d["document_id"] + "/pages/0").status_code == 404
    )


def make_pdf(blank=False, encrypted=False, pages=1):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

    writer = PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        if not blank:
            font = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }
            )
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/Font"): DictionaryObject(
                        {NameObject("/F1"): writer._add_object(font)}
                    )
                }
            )
            stream = DecodedStreamObject()
            stream.set_data(
                b"BT /F1 12 Tf 72 720 Td (Full deployment is not approved.) Tj ET"
            )
            page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("secret")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_real_pdf_worker_preserves_page_references(client):
    p = session(client)
    r = upload(client, p, make_pdf(pages=2), "policy.pdf", "application/pdf")
    assert r.status_code == 201, r.text
    assert r.json()["page_count"] == 2
    hits = search(client, p).json()["passages"]
    assert {h["page"] for h in hits} == {1, 2}


@pytest.mark.parametrize(
    "options", [{"blank": True}, {"encrypted": True}, {"pages": 21}]
)
def test_scan_encryption_and_pdf_page_limits_fail_without_saving(client, options):
    p = session(client)
    r = upload(client, p, make_pdf(**options), "policy.pdf", "application/pdf")
    assert r.status_code == 422 and client.get(p + "/documents").json() == []


def test_timeout_is_explicit_and_extraction_lock_releases(monkeypatch):
    import app.evidence.extraction as module

    def fail(*a, **k):
        raise subprocess.TimeoutExpired("worker", 15)

    monkeypatch.setattr(module.subprocess, "run", fail)
    with pytest.raises(BackendError) as r:
        extract_pages("x.pdf", "application/pdf", b"%PDF-1.7")
    assert r.value.code == "extraction_timeout"
    assert extract_pages("x.txt", "text/plain", b"valid") == ["valid"]


def test_extraction_busy_does_not_start_another_worker():
    from app.evidence.extraction import _extraction_slot

    _extraction_slot.acquire()
    try:
        with pytest.raises(BackendError) as r:
            extract_pages("x.txt", "text/plain", TEXT)
        assert r.value.code == "extraction_busy"
    finally:
        _extraction_slot.release()


def test_large_json_still_rejected_but_uploads_get_their_own_limit(client):
    p = session(client)
    assert upload(client, p, b"policy " * 3000).status_code == 201
    assert (
        client.post(
            p + "/evidence/search",
            content=b"x" * 17000,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )


def test_document_cap_and_history_immutability(client, isolated_database):
    p = session(client)
    for i in range(10):
        assert upload(client, p, TEXT + str(i).encode()).status_code == 201
    assert upload(client, p, TEXT + b"eleven").status_code == 409
    search(client, p)
    db = Database(isolated_database)
    try:
        for table in ["documents", "passages", "retrieval_snapshots"]:
            with pytest.raises(IntegrityError):
                with db.engine.begin() as c:
                    c.execute(text("DELETE FROM " + table))
        with db.engine.connect() as c:
            assert c.execute(text("PRAGMA foreign_key_check")).all() == []
    finally:
        db.close()


def test_snapshot_persists_after_restart_and_does_not_expand_with_corpus(api_factory):
    app, calls = api_factory()
    with TestClient(app, base_url="http://localhost") as c:
        p = session(c)
        upload(c, p)
        s = search(c, p).json()
        upload(c, p, b"Additional deployment details.")
    app2, calls2 = api_factory()
    with TestClient(app2, base_url="http://localhost") as c:
        assert c.get(p + "/evidence/snapshots/" + s["snapshot_id"]).json() == s
    assert calls == calls2 == []


def test_old_briefs_and_hypotheses_survive_second_migration(tmp_path):
    from alembic import command
    from alembic.config import Config
    from pathlib import Path
    from app.db.database import make_engine
    from app.db.tables import sessions, briefs
    from sqlalchemy import insert

    path = tmp_path / "old.sqlite3"
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    engine = make_engine(path)
    with engine.connect() as c:
        cfg.attributes["connection"] = c
        command.upgrade(cfg, "0001_decisions")
    sid = str(uuid4())
    with engine.begin() as c:
        c.execute(
            insert(sessions).values(
                id=sid, revision=1, created_at="old", updated_at="old"
            )
        )
        c.execute(
            insert(briefs).values(
                session_id=sid,
                revision=1,
                brief=DecisionBrief(
                    query="Preserve the existing decision"
                ).model_dump(),
                reason="original",
                created_at="old",
            )
        )
    engine.dispose()
    upgrade_database(path)
    upgrade_database(path)
    db = Database(path)
    try:
        assert (
            DecisionRepository(db).get_session(sid).brief.query
            == "Preserve the existing decision"
        )
    finally:
        db.close()


def test_chunked_oversized_upload_is_rejected_before_extraction(client):
    p = session(client)
    r = client.post(
        p + "/documents?filename=policy.txt&expected_session_revision=1",
        content=iter([b"x" * 600000, b"y" * 600000]),
        headers={"Content-Type": "text/plain"},
    )
    assert r.status_code == 413 and client.get(p + "/documents").json() == []


def test_evidence_contents_do_not_enter_access_logs(client, caplog):
    import logging

    p = session(client)
    with caplog.at_level(logging.INFO, logger="chanakya.access"):
        upload(
            client,
            p,
            b"PrivateDocumentContents-999999",
            name="PrivateFilename-888888.txt",
        )
        search(client, p, query="PrivateSearchQuestion-777777")
    assert all(
        s not in caplog.text
        for s in ["PrivateDocumentContents", "PrivateFilename", "PrivateSearchQuestion"]
    )


def test_concurrent_ingestion_cannot_bypass_document_cap(isolated_database):
    db = Database(isolated_database)
    repo = EvidenceRepository(db)
    sid = (
        DecisionRepository(db)
        .create_session(DecisionBrief(query="Test concurrent document ingestion"))
        .session_id
    )

    def ingest(n):
        raw = ("Unique policy document " + str(n)).encode()
        try:
            repo.ingest(sid, 1, "policy.txt", "text/plain", raw, [raw.decode()])
            return "created"
        except BackendError as e:
            return e.code

    try:
        for i in range(9):
            assert ingest(i) == "created"
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(ingest, range(9, 13)))
        assert results.count("created") == 1 and results.count("document_limit") == 3
        assert len(repo.list_documents(sid)) == 10
    finally:
        db.close()
