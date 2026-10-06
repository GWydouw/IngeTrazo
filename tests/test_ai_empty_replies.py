"""Regression coverage adapted from Brian Russell's PR #190."""
import json
from core import ai

def test_anthropic_retry_omits_empty_text_but_keeps_image_only_turns():
    messages = [{"role": "user", "text": "Draw a model"},
                {"role": "assistant", "text": "  \n"},
                {"role": "user", "text": "Please send the recipe"},
                {"role": "user", "text": "", "image_png_b64": "QUJD"}]
    _, _, raw = ai.build_request("anthropic", "test", "test", "SYS", messages)
    sent = json.loads(raw)["messages"]
    assert len(sent) == 3
    assert sent[-1]["content"][0]["type"] == "image"
    assert len(sent[-1]["content"]) == 1
    assert all(b["text"].strip() for m in sent for b in m["content"]
               if b["type"] == "text")
    assert len(messages) == 4  # existing histories are not mutated


def test_empty_assistant_reply_can_retry_without_poisoning_history(monkeypatch):
    from plugins.ai_assistant import AsistenteDialog
    from views.main_window import MainWindow
    win = MainWindow()
    try:
        dlg = AsistenteDialog(win.viewport, parent=win)
        dlg._last_prompt = "draw a drone"
        dlg._round = 0
        dlg._nudged = False
        dlg._convo = [{"role": "user", "text": "draw a drone"}]
        retries = []
        monkeypatch.setattr(dlg, "_next_turn", lambda: retries.append(True))
        dlg._on_reply({"ok": True, "text": "<thinking>planning</thinking>"})
        assert retries == [True]
        assert all(m["text"].strip() for m in dlg._convo)
        assert all(m["role"] != "assistant" for m in dlg._convo)
        assert "IA: " not in dlg._chat.toPlainText()
    finally:
        win._saved_version = win.viewport.scene.version
        win.close()
