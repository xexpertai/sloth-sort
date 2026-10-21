import json, os, time
from pathlib import Path
import pytest
from sloth_sort import classify as C, config as cfgmod, mover, reader
from sloth_sort.config import Config, Folder


@pytest.fixture
def cfg():
    return Config([Folder("code", "source code", [".py"]), Folder("notes", "notes"), Folder("bills", "bills", [".pdf"])], 200, 0)


def fake_chat(folder, conf="high"):
    def f(messages, schema, **kw):
        return {"folder": folder, "confidence": conf, "reason": "x"}, 0.1
    return f


def test_config_rejects_bad_names(tmp_path):
    p = tmp_path / "c.toml"; p.write_text('[folders."../x"]\ndesc="a"\n[folders.b]\ndesc="b"\n')
    with pytest.raises(ValueError):
        cfgmod.load(p)


def test_baseline_is_extension_only(cfg, tmp_path):
    f = tmp_path / "a.py"; f.write_text("x")
    g = tmp_path / "b.txt"; g.write_text("x")
    assert C.baseline(cfg, f) == "code" and C.baseline(cfg, g) == "leave"


def test_schema_enum_includes_leave(cfg):
    assert C.schema(cfg)["properties"]["folder"]["enum"] == ["code", "notes", "bills", "leave"]


def test_low_confidence_is_left_alone(cfg, tmp_path, monkeypatch):
    f = tmp_path / "a.txt"; f.write_text("hello")
    monkeypatch.setattr(C.llm, "chat", fake_chat("notes", "low"))
    assert C.classify(cfg, f)["folder"] == "leave"


def test_unknown_folder_from_model_is_left(cfg, tmp_path, monkeypatch):
    f = tmp_path / "a.txt"; f.write_text("hello")
    monkeypatch.setattr(C.llm, "chat", fake_chat("../../etc"))
    assert C.classify(cfg, f)["folder"] == "leave"


def test_binary_needs_high_confidence(cfg, tmp_path, monkeypatch):
    f = tmp_path / "a.bin"; f.write_bytes(b"\x00\x01\x02")
    monkeypatch.setattr(C.llm, "chat", fake_chat("notes", "medium"))
    assert C.classify(cfg, f)["folder"] == "leave"


def test_model_down_falls_back_to_baseline(cfg, tmp_path, monkeypatch):
    f = tmp_path / "a.py"; f.write_text("x")
    def boom(*a, **k): raise C.llm.LLMUnavailable("down")
    monkeypatch.setattr(C.llm, "chat", boom)
    r = C.classify(cfg, f)
    assert r["folder"] == "code" and r["source"] == "baseline"


def _plan_and_apply(root, cfg, monkeypatch, folder="notes"):
    monkeypatch.setattr(C.llm, "chat", fake_chat(folder))
    mover.make_plan(root, cfg, log=lambda *_: None)
    return mover.apply_plan(root, cfg, log=lambda *_: None)


def test_apply_then_undo_restores_everything(cfg, tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("one"); (tmp_path / "b.txt").write_text("two")
    before = {p.name: p.read_text() for p in tmp_path.glob("*.txt")}
    r = _plan_and_apply(tmp_path, cfg, monkeypatch)
    assert r["moved"] == 2 and not (tmp_path / "a.txt").exists()
    u = mover.undo(tmp_path, log=lambda *_: None)
    assert u["restored"] == 2 and u["refused"] == 0
    assert {p.name: p.read_text() for p in tmp_path.glob("*.txt")} == before
    assert not (tmp_path / "notes").exists()


def test_never_overwrites_existing_file(cfg, tmp_path, monkeypatch):
    (tmp_path / "notes").mkdir(); (tmp_path / "notes" / "a.txt").write_text("OLD")
    (tmp_path / "a.txt").write_text("NEW")
    _plan_and_apply(tmp_path, cfg, monkeypatch)
    assert (tmp_path / "notes" / "a.txt").read_text() == "OLD"
    assert (tmp_path / "notes" / "a-1.txt").read_text() == "NEW"


def test_file_changed_after_plan_is_refused(cfg, tmp_path, monkeypatch):
    f = tmp_path / "a.txt"; f.write_text("one")
    monkeypatch.setattr(C.llm, "chat", fake_chat("notes"))
    mover.make_plan(tmp_path, cfg, log=lambda *_: None)
    f.write_text("one plus an edit made later")
    r = mover.apply_plan(tmp_path, cfg, log=lambda *_: None)
    assert r == {"moved": 0, "refused": 1} and f.exists()


def _age(path, days_modified, days_opened=None):
    """Set mtime/atime to N days ago (atime defaults to mtime)."""
    now = time.time(); m = now - days_modified * 86400
    a = m if days_opened is None else now - days_opened * 86400
    os.utime(path, (a, m))


def test_only_forgotten_files_are_taken(tmp_path):
    cfg = Config([Folder("a", "a"), Folder("b", "b")], 100, 7)
    old = tmp_path / "old.txt"; old.write_text("x"); _age(old, 30)
    week = tmp_path / "eight_days.txt"; week.write_text("x"); _age(week, 8)
    fresh = tmp_path / "fresh.txt"; fresh.write_text("x"); _age(fresh, 2)
    (tmp_path / ".hidden").write_text("x")
    (tmp_path / "link.txt").symlink_to(old)
    take, skip = mover.candidates(tmp_path, cfg)
    assert [p.name for p in take] == ["eight_days.txt", "old.txt"]
    assert {n for n, _ in skip} == {"fresh.txt", "link.txt"}
    assert "less than 7" in dict(skip)["fresh.txt"]


def test_opening_a_file_counts_as_touching_it(tmp_path):
    cfg = Config([Folder("a", "a"), Folder("b", "b")], 100, 7)
    f = tmp_path / "read_yesterday.pdf"; f.write_text("x"); _age(f, 60, days_opened=1)
    take, skip = mover.candidates(tmp_path, cfg)
    assert take == [] and skip[0][0] == "read_yesterday.pdf"


def test_zero_days_disables_the_rule(tmp_path):
    cfg = Config([Folder("a", "a"), Folder("b", "b")], 100, 0)
    (tmp_path / "new.txt").write_text("x")
    assert [p.name for p in mover.candidates(tmp_path, cfg)[0]] == ["new.txt"]


def test_planning_does_not_make_files_look_fresh(tmp_path, monkeypatch):
    """Regression: reading a file for the model used to bump its access time, so a second plan skipped everything."""
    cfg = Config([Folder("a", "a"), Folder("b", "b")], 100, 7)
    f = tmp_path / "old.txt"; f.write_text("hello"); _age(f, 30)
    monkeypatch.setattr(C.llm, "chat", fake_chat("a"))
    mover.make_plan(tmp_path, cfg, log=lambda *_: None)
    mover.sha(f)
    assert (time.time() - f.stat().st_atime) / 86400 > 29
    assert [p.name for p in mover.candidates(tmp_path, cfg)[0]] == ["old.txt"]


def test_parse_age():
    assert cfgmod.parse_age("7d") == 7 and cfgmod.parse_age("36h") == 1.5 and cfgmod.parse_age("90m") == 90 / 1440
    assert cfgmod.parse_age("0") == 0 and cfgmod.parse_age(3) == 3


def test_undo_refuses_if_content_changed(cfg, tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("one")
    _plan_and_apply(tmp_path, cfg, monkeypatch)
    (tmp_path / "notes" / "a.txt").write_text("edited after the move")
    u = mover.undo(tmp_path, log=lambda *_: None)
    assert u["refused"] == 1 and (tmp_path / "notes" / "a.txt").read_text() == "edited after the move"


def test_reader_limits_and_binary(tmp_path):
    big = tmp_path / "big.txt"; big.write_text("a" * 100000)
    assert len(reader.snippet(big, 300)[1]) == 300
    b = tmp_path / "x.dat"; b.write_bytes(b"\x00" * 10)
    assert reader.snippet(b)[0] == "binary"


def test_pdf_text_is_read(tmp_path):
    from fpdf import FPDF
    d = FPDF(); d.add_page(); d.set_font("Helvetica", size=12); d.cell(0, 10, "Invoice total due 500")
    p = tmp_path / "s.pdf"; d.output(str(p))
    kind, text = reader.snippet(p)
    assert kind == "pdf" and "Invoice" in text


def test_strict_folder_takes_its_extension_without_asking(tmp_path, monkeypatch):
    cfg = Config([Folder("data", "tool output", [".json"], True), Folder("notes", "notes")], 100, 0)
    f = tmp_path / "x.json"; f.write_text("{}")
    def boom(*a, **k): raise AssertionError("model must not be asked")
    monkeypatch.setattr(C.llm, "chat", boom)
    assert C.classify(cfg, f)["folder"] == "data"


def test_strict_folder_refuses_other_extensions(tmp_path, monkeypatch):
    cfg = Config([Folder("data", "tool output", [".json"], True), Folder("notes", "notes")], 100, 0)
    f = tmp_path / "x.md"; f.write_text("# hi")
    monkeypatch.setattr(C.llm, "chat", fake_chat("data", "high"))
    assert C.classify(cfg, f)["folder"] == "leave"


def test_ics_and_sql_are_read_as_text(tmp_path):
    for n in ("a.ics", "b.sql"):
        p = tmp_path / n; p.write_text("BEGIN:VCALENDAR")
        assert reader.snippet(p)[0] == "text"
