from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


def _setup_ui(text="hi - there", initial="0", min_d="0", max_d="0", p_min="0", p_max="0", hum=0, pause_freq=0):
    main.initial_delay_entry = DummyEntry(initial)
    main.min_delay_entry = DummyEntry(min_d)
    main.max_delay_entry = DummyEntry(max_d)
    main.pause_delay_min_entry = DummyEntry(p_min)
    main.pause_delay_max_entry = DummyEntry(p_max)
    main.humanization_scale = DummyScale(hum)
    main.random_pause_scale = DummyScale(pause_freq)
    main.text_box = DummyTextView(text)
    main.status_label = DummyLabel()
    main.wpm_label = DummyLabel()
    main.start_button = DummyButton()
    main.stop_button = DummyButton()
    main.GLib = None


def test_typo_chance_zero_and_edge_humanization():
    assert main.calculate_typo_chance(0) == 0.0
    assert main.calculate_typo_chance(-1) == 0.0
    assert main.calculate_typo_chance(float("nan")) == 0.0
    assert main.calculate_typo_chance(float("inf")) == 0.0
    assert main.calculate_typo_chance(1) == 0.005
    assert main.calculate_typo_chance(5) == 0.01
    assert main.calculate_typo_chance(1000) == 1.0


def test_get_typo_preserves_case_and_non_alpha():
    for ch, neighbors in main.KEYBOARD_NEARBY_CHARS.items():
        typo_lower = main.get_typo(ch)
        assert typo_lower in neighbors
        assert typo_lower.islower()

        typo_upper = main.get_typo(ch.upper())
        assert typo_upper.lower() in neighbors
        assert typo_upper.isupper()

    assert main.get_typo("!") == "!"
    assert main.get_typo("9") == "9"


def test_validate_delays_edge_cases():
    main.validate_delays(0.0, 0.01, 0.02, 0.1, 0.2)
    with pytest.raises(ValueError, match="non-negative"):
        main.validate_delays(-1.0, 0.01, 0.02, 0.1, 0.2)
    with pytest.raises(ValueError, match="non-negative"):
        main.validate_delays(float("nan"), 0.01, 0.02, 0.1, 0.2)
    with pytest.raises(ValueError, match="non-negative"):
        main.validate_delays(float("inf"), 0.01, 0.02, 0.1, 0.2)
    with pytest.raises(ValueError, match="Min delay"):
        main.validate_delays(1.0, 0.5, 0.1, 0.1, 0.2)
    with pytest.raises(ValueError, match="Pause Delay"):
        main.validate_delays(1.0, 0.1, 0.5, 0.8, 0.2)


def test_start_typing_runs_and_stops_cleanly(monkeypatch):
    _setup_ui(text="hi - there")

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
    _setup_ui(text="hello")

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


def test_start_typing_validation_and_empty_text():
    _setup_ui(text="hello", initial="not-a-number")
    main.start_typing(None)
    assert main.status_label.text == "Invalid delay. Please enter numbers."

    _setup_ui(text="hello", min_d="0.5", max_d="0.1")
    main.start_typing(None)
    assert "Min delay cannot exceed Max delay" in main.status_label.text

    _setup_ui(text="   \n\t  ")
    main.start_typing(None)
    assert main.status_label.text == "Please enter text to type."


def test_start_typing_handles_missing_ydotool_and_subprocess_error(monkeypatch):
    class SyncThread:
        def __init__(self, target, daemon=False):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(main.threading, "Thread", SyncThread)

    _setup_ui(text="hi")

    def raise_fnf(cmd, check=False):
        raise FileNotFoundError("ydotool")

    monkeypatch.setattr(main.subprocess, "run", raise_fnf)
    main.start_typing(None)
    assert main.status_label.text == "Error: 'ydotool' not found in PATH."
    assert main.start_button.sensitive is True
    assert main.stop_button.sensitive is False

    _setup_ui(text="hi")

    def raise_subproc(cmd, check=False):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(main.subprocess, "run", raise_subproc)
    main.start_typing(None)
    assert "Error running ydotool:" in main.status_label.text
    assert main.start_button.sensitive is True
    assert main.stop_button.sensitive is False


def test_interruptible_sleep_and_slider_labels(monkeypatch):
    sleeps = []
    monkeypatch.setattr(main.time, "sleep", lambda d: sleeps.append(d))
    main.stop_typing = False
    main._interruptible_sleep(0.0)
    main._interruptible_sleep(-1.0)
    main._interruptible_sleep(float("nan"))
    assert sleeps == []

    main.initial_delay_label = DummyLabel()
    main.min_delay_label = DummyLabel()
    main.max_delay_label = DummyLabel()
    main.pause_delay_min_label = DummyLabel()
    main.pause_delay_max_label = DummyLabel()
    main.humanization_label = DummyLabel()
    main.random_pause_label = DummyLabel()
    _setup_ui(initial="2", min_d="0.05", max_d="0.2", p_min="1", p_max="3", hum=4.9999999, pause_freq=5.9999999)
    main.update_slider_values()
    assert main.initial_delay_label.text == "Initial Delay (seconds): 2"
    assert main.humanization_label.text == "Humanization Level (0-10): 5"
    assert main.random_pause_label.text == "Random Pause Frequency (0-10): 6"

    # Positive duration sleep and mid-sleep stop_typing interruption
    clock = [100.0]

    def fake_time():
        return clock[0]

    def fake_sleep(d):
        sleeps.append(round(d, 4))
        clock[0] += d
        if len(sleeps) >= 2:
            main.stop_typing = True

    monkeypatch.setattr(main.time, "time", fake_time)
    monkeypatch.setattr(main.time, "sleep", fake_sleep)
    main.stop_typing = False
    main._interruptible_sleep(0.25)
    assert sleeps == [0.05, 0.05]


def test_start_typing_typos_word_pauses_and_char_interval_pauses(monkeypatch):
    # 45+ chars with multiple whitespace boundaries to trigger word and char-interval pauses
    text = ("word1   word2\n\tword3 " * 3).strip()
    _setup_ui(text=text, initial="0", min_d="0.01", max_d="0.01", p_min="0.02", p_max="0.02", hum=10, pause_freq=100)

    clock = [1000.0]
    monkeypatch.setattr(main.time, "time", lambda: clock[0])

    typed_chars = []
    monkeypatch.setattr(
        main.subprocess,
        "run",
        lambda cmd, check=False: typed_chars.append(cmd[3]),
    )
    monkeypatch.setattr(main, "_interruptible_sleep", lambda d: clock.__setitem__(0, clock[0] + max(d, 0.01)))
    monkeypatch.setattr(main.random, "randint", lambda _a, _b: 40)

    class SyncThread:
        def __init__(self, target, daemon=False):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(main.threading, "Thread", SyncThread)

    main.start_typing(None)
    assert main.status_label.text == "Typing complete."
    assert len(typed_chars) == len(text)
    assert main.wpm_label.text.startswith("WPM: ")


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


