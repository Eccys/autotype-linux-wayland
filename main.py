import math
import random
import subprocess
import threading
import time

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import GLib, Gtk
except ImportError:
    gi = None
    Gtk = None
    GLib = None

# Global variable to control the stopping of typing simulation
stop_typing = False

# This dictionary defines possible 'nearby' keys for human-like typos on the keyboard
KEYBOARD_NEARBY_CHARS = {
    'a': ['q', 'w', 's', 'z', 'x'],
    'b': ['v', 'g', 'h', 'n'],
    'c': ['x', 'd', 'f', 'v'],
    'd': ['s', 'f', 'g', 'e', 'r'],
    'e': ['w', 'r', 'd', 'f', 't'],
    'f': ['d', 'g', 'r', 't', 'v'],
    'g': ['f', 'h', 't', 'y', 'b'],
    'h': ['g', 'j', 'y', 'u', 'b'],
    'i': ['u', 'o', 'k', 'j'],
    'j': ['h', 'k', 'u', 'i'],
    'k': ['j', 'l', 'o', 'p'],
    'l': ['k', 'p'],
    'm': ['n', 'j'],
    'n': ['b', 'm', 'h'],
    'o': ['i', 'p', 'l'],
    'p': ['o', 'l'],
    'q': ['a', 'w'],
    'r': ['e', 't', 'f', 'd'],
    's': ['a', 'w', 'e', 'd', 'z'],
    't': ['r', 'y', 'f', 'g'],
    'u': ['y', 'i', 'j', 'h'],
    'v': ['c', 'f', 'b', 'g'],
    'w': ['q', 'e', 's', 'a'],
    'x': ['z', 'c', 's', 'd'],
    'y': ['t', 'u', 'g', 'h'],
    'z': ['a', 'x', 's'],
}


def get_typo(char):
    """Generate a nearby-key typo while preserving character case."""
    lower = char.lower()
    if lower in KEYBOARD_NEARBY_CHARS:
        replacement = random.choice(KEYBOARD_NEARBY_CHARS[lower])
        return replacement.upper() if char.isupper() else replacement
    return char


def calculate_typo_chance(humanization_level):
    """Calculate typo probability from humanization level (0 disables typos)."""
    if humanization_level <= 0:
        return 0.0
    return max(0.005, humanization_level * 0.002)


def validate_delays(initial_delay, min_delay, max_delay, pause_delay_min, pause_delay_max):
    """Validate that delay values are finite, non-negative, and ordered."""
    values = (initial_delay, min_delay, max_delay, pause_delay_min, pause_delay_max)
    if not all(math.isfinite(v) and v >= 0 for v in values):
        raise ValueError("Delays must be non-negative numbers.")
    if min_delay > max_delay:
        raise ValueError("Min delay cannot exceed Max delay.")
    if pause_delay_min > pause_delay_max:
        raise ValueError("Pause Delay Min cannot exceed Pause Delay Max.")


def _ui_call(func, *args):
    if GLib is not None:
        GLib.idle_add(func, *args)
    else:
        func(*args)


def _interruptible_sleep(duration):
    """Sleep in small increments so stop_typing is respected promptly."""
    end_time = time.time() + max(0.0, duration)
    while not stop_typing:
        remaining = end_time - time.time()
        if remaining <= 0:
            break
        time.sleep(min(0.05, remaining))


# Start typing function, triggered when the "Start Typing" button is clicked
def start_typing(button):
    global stop_typing
    stop_typing = False  # Reset the stop typing flag

    # Retrieve values from the UI entries and sliders
    try:
        initial_delay = float(initial_delay_entry.get_text())
        min_delay = float(min_delay_entry.get_text())
        max_delay = float(max_delay_entry.get_text())
        pause_delay_min = float(pause_delay_min_entry.get_text())
        pause_delay_max = float(pause_delay_max_entry.get_text())
        humanization_level = int(humanization_scale.get_value())
        random_pause_frequency = int(random_pause_scale.get_value())
        validate_delays(initial_delay, min_delay, max_delay, pause_delay_min, pause_delay_max)
    except ValueError as exc:
        status_label.set_text(str(exc) if "delay" in str(exc).lower() else "Invalid delay. Please enter numbers.")
        return

    # Retrieve the text to type from the text box widget
    buffer = text_box.get_buffer()
    start_iter, end_iter = buffer.get_start_iter(), buffer.get_end_iter()
    text = buffer.get_text(start_iter, end_iter, True).strip()
    if not text:
        status_label.set_text("Please enter text to type.")
        return

    # Disable the start button and enable the stop button
    start_button.set_sensitive(False)
    stop_button.set_sensitive(True)
    status_label.set_text("Waiting for initial delay...")

    # Main typing simulation function
    def type_text():
        try:
            total_chars = 0
            total_words = 0

            _interruptible_sleep(initial_delay)
            if stop_typing:
                _ui_call(status_label.set_text, "Typing stopped.")
                return

            _ui_call(status_label.set_text, "Typing in progress...")

            typo_chance = calculate_typo_chance(humanization_level)
            pause_chance = random_pause_frequency / 100.0
            chars_until_pause = random.randint(40, 60)

            typing_start_time = time.time()
            total_pause_time = 0.0
            char_count = 0

            for i, char in enumerate(text):
                if stop_typing:
                    _ui_call(status_label.set_text, "Typing stopped.")
                    return

                typed_char = get_typo(char) if random.random() < typo_chance else char

                subprocess.run(['ydotool', 'type', '--', typed_char], check=True)

                char_count += 1
                total_chars += 1

                # When a space or the last character is reached, increment word count
                if char == ' ' or i == len(text) - 1:
                    if random.random() < pause_chance:
                        pause_duration = random.uniform(pause_delay_min, pause_delay_max)
                        _interruptible_sleep(pause_duration)
                        total_pause_time += pause_duration

                    total_words += 1

                # Add random delay between characters to simulate human typing
                _interruptible_sleep(random.uniform(min_delay, max_delay))

                # Introduce pause after a certain number of characters typed
                if char_count >= chars_until_pause:
                    char_count = 0
                    chars_until_pause = random.randint(40, 60)
                    if random.random() < pause_chance:
                        pause_duration = random.uniform(pause_delay_min, pause_delay_max)
                        _interruptible_sleep(pause_duration)
                        total_pause_time += pause_duration

                total_typing_time = time.time() - typing_start_time
                if total_typing_time > 0:
                    wpm = (total_words / total_typing_time) * 60
                    _ui_call(wpm_label.set_text, f"WPM: {int(wpm)}")

            total_typing_time = time.time() - typing_start_time
            if total_typing_time > 0:
                wpm = (total_words / total_typing_time) * 60
                _ui_call(wpm_label.set_text, f"WPM: {int(wpm)}")

            _ui_call(status_label.set_text, "Typing stopped." if stop_typing else "Typing complete.")
        except FileNotFoundError:
            _ui_call(status_label.set_text, "Error: 'ydotool' not found in PATH.")
        except subprocess.SubprocessError as exc:
            _ui_call(status_label.set_text, f"Error running ydotool: {exc}")
        finally:
            _ui_call(start_button.set_sensitive, True)
            _ui_call(stop_button.set_sensitive, False)

    # Run the typing simulation in a separate thread to avoid blocking the UI
    threading.Thread(target=type_text, daemon=True).start()


# Stop typing function, triggered when the "Stop Typing" button is clicked
def stop_typing_action(button):
    global stop_typing
    stop_typing = True  # Set the flag to stop typing


# Function to update the labels showing the current values of sliders and entries
def update_slider_values(widget=None):
    initial_delay_label.set_text(f"Initial Delay (seconds): {initial_delay_entry.get_text()}")
    min_delay_label.set_text(f"Min Delay (seconds): {min_delay_entry.get_text()}")
    max_delay_label.set_text(f"Max Delay (seconds): {max_delay_entry.get_text()}")
    pause_delay_min_label.set_text(f"Pause Delay Min (seconds): {pause_delay_min_entry.get_text()}")
    pause_delay_max_label.set_text(f"Pause Delay Max (seconds): {pause_delay_max_entry.get_text()}")
    humanization_label.set_text(f"Humanization Level (0-10): {int(humanization_scale.get_value())}")
    random_pause_label.set_text(f"Random Pause Frequency (0-10): {int(random_pause_scale.get_value())}")


if __name__ == "__main__":
    # GTK Window setup
    window = Gtk.Window(title="Typing Simulator")
    window.set_default_size(600, 500)
    window.connect("destroy", Gtk.main_quit)

    # Main vertical box layout
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    window.add(main_box)

    # Grid layout for controls
    grid = Gtk.Grid()
    main_box.pack_start(grid, True, True, 0)

    # UI elements for configuration: labels, entries, scales for delays, humanization, etc.
    initial_delay_label = Gtk.Label(label="Initial Delay (seconds):")
    grid.attach(initial_delay_label, 0, 0, 1, 1)
    initial_delay_entry = Gtk.Entry()
    initial_delay_entry.set_text("3")
    grid.attach(initial_delay_entry, 1, 0, 1, 1)

    min_delay_label = Gtk.Label(label="Min Delay (seconds):")
    grid.attach(min_delay_label, 0, 1, 1, 1)
    min_delay_entry = Gtk.Entry()
    min_delay_entry.set_text("0.05")
    grid.attach(min_delay_entry, 1, 1, 1, 1)

    max_delay_label = Gtk.Label(label="Max Delay (seconds):")
    grid.attach(max_delay_label, 0, 2, 1, 1)
    max_delay_entry = Gtk.Entry()
    max_delay_entry.set_text("0.2")
    grid.attach(max_delay_entry, 1, 2, 1, 1)

    pause_delay_min_label = Gtk.Label(label="Pause Delay Min (seconds):")
    grid.attach(pause_delay_min_label, 0, 3, 1, 1)
    pause_delay_min_entry = Gtk.Entry()
    pause_delay_min_entry.set_text("3")
    grid.attach(pause_delay_min_entry, 1, 3, 1, 1)

    pause_delay_max_label = Gtk.Label(label="Pause Delay Max (seconds):")
    grid.attach(pause_delay_max_label, 0, 4, 1, 1)
    pause_delay_max_entry = Gtk.Entry()
    pause_delay_max_entry.set_text("7")
    grid.attach(pause_delay_max_entry, 1, 4, 1, 1)

    humanization_label = Gtk.Label(label="Humanization Level (0-10):")
    grid.attach(humanization_label, 0, 5, 1, 1)
    humanization_scale = Gtk.Scale()
    humanization_scale.set_range(0, 10)
    humanization_scale.set_value(5)
    grid.attach(humanization_scale, 1, 5, 1, 1)

    random_pause_label = Gtk.Label(label="Random Pause Frequency (0-10):")
    grid.attach(random_pause_label, 0, 6, 1, 1)
    random_pause_scale = Gtk.Scale()
    random_pause_scale.set_range(0, 10)
    random_pause_scale.set_value(3)
    grid.attach(random_pause_scale, 1, 6, 1, 1)

    # Text entry box to enter the text to be typed
    text_label = Gtk.Label(label="Text to Type:")
    grid.attach(text_label, 0, 7, 1, 1)
    text_box = Gtk.TextView()
    text_buffer = text_box.get_buffer()
    text_box.set_wrap_mode(Gtk.WrapMode.WORD)
    grid.attach(text_box, 1, 7, 1, 2)

    # Make the TextView resizable by setting hexpand and vexpand to True
    text_box.set_hexpand(True)
    text_box.set_vexpand(True)

    # WPM label to show the typing speed
    wpm_label = Gtk.Label(label="WPM: 0")
    main_box.pack_end(wpm_label, False, False, 10)

    # Status label to show the current typing status (e.g., "Ready to type!")
    status_label = Gtk.Label(label="Ready to type!")
    main_box.pack_end(status_label, False, False, 10)

    # Start and stop buttons for controlling the typing simulation
    start_button = Gtk.Button(label="Start Typing")
    start_button.connect("clicked", start_typing)
    grid.attach(start_button, 0, 9, 1, 1)

    stop_button = Gtk.Button(label="Stop Typing")
    stop_button.connect("clicked", stop_typing_action)
    stop_button.set_sensitive(False)
    grid.attach(stop_button, 1, 9, 1, 1)

    # Connect the value change events for the entries and sliders to update labels
    initial_delay_entry.connect("changed", update_slider_values)
    min_delay_entry.connect("changed", update_slider_values)
    max_delay_entry.connect("changed", update_slider_values)
    pause_delay_min_entry.connect("changed", update_slider_values)
    pause_delay_max_entry.connect("changed", update_slider_values)
    humanization_scale.connect("value-changed", update_slider_values)
    random_pause_scale.connect("value-changed", update_slider_values)

    # Initial label updates based on default settings
    update_slider_values()

    # Show all the UI elements
    window.show_all()

    # Start the GTK main loop
    Gtk.main()

