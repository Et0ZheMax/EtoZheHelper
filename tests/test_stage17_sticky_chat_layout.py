from pathlib import Path


def test_chat_layout_keeps_composer_visible_in_viewport():
    css = Path("app/static/app.css").read_text(encoding="utf-8")

    assert "100vh" in css
    assert "overflow: hidden" in css
    assert "overflow-y: auto" in css
    assert "min-height: 0" in css
    assert "grid-template-rows" in css or "flex-direction: column" in css
    assert "@media" in css


def test_main_panels_use_internal_scroll_containers():
    css = Path("app/static/app.css").read_text(encoding="utf-8")

    assert ".layout" in css and "height: 100vh" in css
    assert ".sidebar, .sources" in css and "overflow-y: auto" in css
    assert ".messages" in css and "overflow-y: auto" in css
    assert "minmax(0, 1fr)" in css


def test_mobile_layout_releases_desktop_shell_scroll_lock():
    css = Path("app/static/app.css").read_text(encoding="utf-8")

    assert "@media (max-width" in css
    assert "body {\n        overflow: auto;" in css
    assert "height: auto" in css
    assert "max-height: 55vh" in css
