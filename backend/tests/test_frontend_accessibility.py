from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
JAVASCRIPT = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")


class ElementCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.elements.append((tag, dict(attrs)))


parser = ElementCollector()
parser.feed(HTML)
ELEMENTS = parser.elements


def elements_with_class(tag: str, class_name: str) -> list[dict[str, str | None]]:
    return [
        attrs
        for element_tag, attrs in ELEMENTS
        if element_tag == tag and class_name in (attrs.get("class") or "").split()
    ]


def element_by_id(element_id: str) -> dict[str, str | None]:
    matches = [
        attrs
        for _, attrs in ELEMENTS
        if attrs.get("id") == element_id
    ]
    assert len(matches) == 1
    return matches[0]


def test_navigation_exposes_names_and_active_state() -> None:
    navigation = elements_with_class("button", "nav-item")

    assert len(navigation) == 2
    assert {item["aria-label"] for item in navigation} == {
        "New analysis",
        "Case history",
    }
    assert [item["aria-pressed"] for item in navigation].count("true") == 1
    assert {item["aria-controls"] for item in navigation} == {
        "analysisView",
        "historyView",
    }


def test_skip_link_and_upload_instructions_are_connected() -> None:
    skip_links = elements_with_class("a", "skip-link")
    assert len(skip_links) == 1
    assert skip_links[0]["href"] == "#workspace"
    assert element_by_id("workspace")["tabindex"] == "-1"
    assert element_by_id("mediaFile")["aria-describedby"] == "uploadRequirements"


def test_tabs_have_complete_aria_relationships() -> None:
    tabs = elements_with_class("button", "tab")

    assert len(tabs) == 3
    assert [tab["aria-selected"] for tab in tabs].count("true") == 1
    assert [tab["tabindex"] for tab in tabs].count("0") == 1

    for tab in tabs:
        panel = element_by_id(str(tab["aria-controls"]))
        assert panel["role"] == "tabpanel"
        assert panel["aria-labelledby"] == tab["id"]
        assert panel["tabindex"] == "0"


def test_focus_targets_and_table_headers_are_defined() -> None:
    for heading_id in ("analysisHeading", "resultHeading", "historyHeading"):
        assert element_by_id(heading_id)["tabindex"] == "-1"

    headers = [attrs for tag, attrs in ELEMENTS if tag == "th"]
    assert headers
    assert all(header.get("scope") == "col" for header in headers)

    captions = [attrs for tag, attrs in ELEMENTS if tag == "caption"]
    assert len(captions) == 2


def test_progress_and_dynamic_regions_expose_state() -> None:
    progress = element_by_id("progressTrack")
    assert progress["role"] == "progressbar"
    assert progress["aria-valuemin"] == "0"
    assert progress["aria-valuemax"] == "100"
    assert progress["aria-valuenow"] == "0"
    assert element_by_id("jobProgress")["aria-atomic"] == "true"
    assert element_by_id("historyTable")["aria-live"] == "polite"


def test_keyboard_behavior_and_focus_updates_are_present() -> None:
    expected_javascript = (
        'event.key === "ArrowRight"',
        'event.key === "ArrowLeft"',
        'event.key === "Home"',
        'event.key === "End"',
        "panel.hidden = !active;",
        'byId("resultHeading").focus();',
        'item.setAttribute("aria-pressed", String(active));',
        "view.hidden = !active;",
        'activateTab(byId("overviewTab"));',
        'byId("reportActions").hidden = true;',
        'byId("progressTrack").setAttribute("aria-valuenow", String(percent));',
    )

    for expected in expected_javascript:
        assert expected in JAVASCRIPT


def test_visible_focus_styles_are_present() -> None:
    assert ":focus-visible" in CSS
    assert ".drop-zone:focus-within" in CSS
    assert ".skip-link:focus" in CSS
    assert "prefers-reduced-motion" in CSS


def test_client_validation_and_interpretation_boundaries_are_present() -> None:
    assert "SUPPORTED_MEDIA_TYPES" in JAVASCRIPT
    assert "MAX_UPLOAD_BYTES" in JAVASCRIPT
    assert "Unsupported format" in JAVASCRIPT
    assert "Strong AI-origin evidence" in JAVASCRIPT
    assert "No known watermark or provenance marker" in JAVASCRIPT
    assert "Face-manipulation model score" in HTML
    assert "Supported LSB payload" in HTML
    for signal_id in ("modelSignal", "originSignal", "elaSignal", "lsbSignal"):
        assert element_by_id(signal_id)
    assert "Neither measure is a fake probability" in JAVASCRIPT


def test_document_ids_are_unique() -> None:
    ids = [attrs["id"] for _, attrs in ELEMENTS if attrs.get("id")]
    assert len(ids) == len(set(ids))
