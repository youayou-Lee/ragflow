import rag.app.subdoc_splitter as subdoc_splitter


def test_split_mixed_pdf_creates_boundaries(monkeypatch):
    pages = [
        "某某案件 起诉意见书\n经依法审查查明",
        "犯罪事实如下",
        "讯问笔录\n问：你叫什么名字？答：张三",
        "答：我于2020年...",
    ]
    monkeypatch.setattr(subdoc_splitter, "_extract_pdf_page_texts", lambda binary, max_pages=300: pages)

    result = subdoc_splitter.split_mixed_pdf(b"fake", "case.pdf")

    assert len(result) == 2
    assert result[0]["start_page"] == 1
    assert result[0]["end_page"] == 2
    assert result[0]["doc_type"] == "indictment"
    assert result[1]["start_page"] == 3
    assert result[1]["end_page"] == 4
    assert result[1]["doc_type"] == "interrogation"


def test_split_mixed_pdf_fallback_single_subdoc(monkeypatch):
    monkeypatch.setattr(subdoc_splitter, "_extract_pdf_page_texts", lambda binary, max_pages=300: ["", "", ""])

    result = subdoc_splitter.split_mixed_pdf(b"fake", "empty.pdf")

    assert len(result) == 1
    assert result[0]["start_page"] == 1
    assert result[0]["end_page"] == 3
    assert result[0]["doc_type"] == "unknown"
