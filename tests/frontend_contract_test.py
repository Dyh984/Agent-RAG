from pathlib import Path


def test_frontend_uses_real_ingestion_api():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    api = Path("frontend/api.js").read_text(encoding="utf-8")

    assert '<script src="/api.js"></script>' in html
    assert "Math.random() * 35" not in html
    upload_start = html.index("const handleDocUpload")
    upload_end = html.index("const deleteDoc")
    assert "setTimeout(() =>" not in html[upload_start:upload_end]
    assert "fetch(url, options)" in api
    assert 'request("/api/kbs"' in api
    assert "uploadDocument" in api
    assert "getDocument" in api
