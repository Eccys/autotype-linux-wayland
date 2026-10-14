import pytest

import main


class DummyEntry:
    def __init__(self, text):
        self._text = text

    def get_text(self):
        return self._text


class DummyScale:
    def __init__(self, value):
        self._value = value

    def get_value(self):
        return self._value


class DummyLabel:
    def __init__(self):
        self.text = ""

    def set_text(self, value):
        self.text = value


class DummyButton:
    def __init__(self):
        self.sensitive = True

    def set_sensitive(self, value):
        self.sensitive = value


class DummyBuffer:
    def __init__(self, text):
        self._text = text

    def get_start_iter(self):
        return 0

    def get_end_iter(self):
        return len(self._text)

    def get_text(self, _start, _end, _include_hidden):
        return self._text


class DummyTextView:
    def __init__(self, text):
        self._buf = DummyBuffer(text)

    def get_buffer(self):
        return self._buf


def test_typo_chance_zero_humanization():
    assert main.calculate_typo_chance(0) == 0.0
    assert main.calculate_typo_chance(-1) == 0.0
    assert main.calculate_typo_chance(5) == 0.01


def test_get_typo_preserves_case_and_non_alpha():
    typo_lower = main.get_typo("a")
    assert typo_lower in main.KEYBOARD_NEARBY_CHARS["a"]
    assert typo_lower.islower()

    typo_upper = main.get_typo("A")
    assert typo_upper.lower() in main.KEYBOARD_NEARBY_CHARS["a"]
    assert typo_upper.isupper()

    assert main.get_typo("!") == "!"


def test_validate_delays_edge_cases():
    main.validate_delays(0.0, 0.01, 0.02, 0.1, 0.2)
    with pytest.raises(ValueError, match="non-negative"):
        main.validate_delays(-1.0, 0.01, 0.02, 0.1, 0.2)
    with pytest.raises(ValueError, match="non-negative"):
        main.validate_delays(float("nan"), 0.01, 0.02, 0.1, 0.2)
    with pytest.raises(ValueError, match="Min delay"):
        main.validate_delays(1.0, 0.5, 0.1, 0.1, 0.2)
    with pytest.raises(ValueError, match="Pause Delay"):
        main.validate_delays(1.0, 0.1, 0.5, 0.8, 0.2)


def test_start_typing_runs_and_stops_cleanly(monkeypatch):
    main.initial_delay_entry = DummyEntry("0")
    main.min_delay_entry = DummyEntry("0")
    main.max_delay_entry = DummyEntry("0")
    main.pause_delay_min_entry = DummyEntry("0")
    main.pause_delay_max_entry = DummyEntry("0")
    main.humanization_scale = DummyScale(0)
    main.random_pause_scale = DummyScale(0)
    main.text_box = DummyTextView("hi - there")
    main.status_label = DummyLabel()
    main.wpm_label = DummyLabel()
    main.start_button = DummyButton()
    main.stop_button = DummyButton()
    main.GLib = None

    calls = []
    monkeypatch.setattr(
        main.subprocess,
        "run",
        lambda cmd, check=False: calls.append((cmd, check)),
    )

    class SyncThread:
        def __init__(self, target, daemon=False):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(main.threading, "Thread", SyncThread)

    main.start_typing(None)
    assert main.status_label.text == "Typing complete."
    assert main.start_button.sensitive is True
    assert main.stop_button.sensitive is False
    assert [c[0][3] for c in calls] == list("hi - there")
    assert all(c[0][:3] == ["ydotool", "type", "--"] for c in calls)


def test_stop_typing_keeps_stopped_status(monkeypatch):
    main.initial_delay_entry = DummyEntry("0")
    main.min_delay_entry = DummyEntry("0")
    main.max_delay_entry = DummyEntry("0")
    main.pause_delay_min_entry = DummyEntry("0")
    main.pause_delay_max_entry = DummyEntry("0")
    main.humanization_scale = DummyScale(0)
    main.random_pause_scale = DummyScale(0)
    main.text_box = DummyTextView("hello")
    main.status_label = DummyLabel()
    main.wpm_label = DummyLabel()
    main.start_button = DummyButton()
    main.stop_button = DummyButton()
    main.GLib = None

    def stop_on_first_char(cmd, check=False):
        main.stop_typing_action(None)

    monkeypatch.setattr(main.subprocess, "run", stop_on_first_char)

    class SyncThread:
        def __init__(self, target, daemon=False):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(main.threading, "Thread", SyncThread)

    main.start_typing(None)
    assert main.status_label.text == "Typing stopped."
    assert main.start_button.sensitive is True
    assert main.stop_button.sensitive is False


def test_ui_call_glib_idle_add_returns_false(monkeypatch):
    scheduled = []

    class DummyGLib:
        @staticmethod
        def idle_add(cb):
            scheduled.append(cb)

    monkeypatch.setattr(main, "GLib", DummyGLib)
    received = []
    main._ui_call(lambda x: (received.append(x), True)[1], "hello")
    assert len(scheduled) == 1
    # Even when the inner function returns True, the idle callback must return False (SOURCE_REMOVE)
    assert scheduled[0]() is False
    assert received == ["hello"]

