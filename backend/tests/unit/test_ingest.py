from app.domain.retrieval.ingest import chunk_pages, chunk_text


def test_short_text_is_one_chunk():
    assert chunk_text("Bonjour   le monde") == ["Bonjour le monde"]


def test_long_text_is_split_with_overlap():
    text = " ".join(f"mot{i}" for i in range(1000))
    chunks = chunk_text(text, size=200, overlap=40)
    assert len(chunks) > 5 and all(len(c) <= 200 for c in chunks)
    assert chunks[0].split()[-1] in chunks[1]  # chevauchement


def test_empty_text():
    assert chunk_text("   ") == []


def test_scientific_sections_and_tables_get_separate_tags_across_pages():
    rows = chunk_pages([
        (1, """Abstract:
Results: awareness improved and stigmatizing attitudes remained common.
1. INTRODUCTION
Earlier research had limited data on the topic.
3. RESULTS
Table 2. Transmission knowledge
Blood exposure 92%
Needle sharing 86%"""),
        (2, """Pregnancy 60%
Table 3. Attitudes
Support for isolation 41%
The study reports that attitudes and knowledge were measured separately.
4. DISCUSSION
The authors discuss the limitations.
5. CONCLUSION
The study identifies awareness gaps and stigma."""),
    ])

    contents = [row["content"] for row in rows]

    assert any(content.startswith("[RAG section=abstract type=prose]") for content in contents)
    assert any(content.startswith("[RAG section=introduction type=prose]")
               and "Earlier research" in content for content in contents)
    assert any(content.startswith("[RAG section=results type=table table=2]")
               and "Pregnancy 60%" in content for content in contents)
    assert any(content.startswith("[RAG section=results type=table table=3]")
               and "Support for isolation" in content for content in contents)
    assert any(content.startswith("[RAG section=results type=prose]")
               and "measured separately" in content for content in contents)
    assert any(content.startswith("[RAG section=discussion type=prose]") for content in contents)
    assert any(content.startswith("[RAG section=conclusion type=prose]") for content in contents)


def test_out_of_order_table_continuation_does_not_change_active_table():
    rows = chunk_pages([
        (1, """3. RESULTS
Table 1. Demographics
Age 20 52%
Table 2. Transmission
Blood exposure 92%"""),
        (2, "(Table 1) contd.....\nNeedle sharing 86%"),
    ])

    transmission = "\n".join(row["content"] for row in rows if "table=2" in row["content"])

    assert "Needle sharing 86%" in transmission
    assert not any("table=1" in row["content"] and "Needle sharing" in row["content"]
                   for row in rows)
