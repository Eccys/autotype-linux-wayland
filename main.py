import gi
import time
import random
import threading
import subprocess

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

# Global variable to control the stopping of typing simulation
stop_typing = False

# Start typing function, triggered when the "Start Typing" button is clicked
def start_typing(button):
    global stop_typing
    stop_typing = False  # Reset the stop typing flag

    # Retrieve values from the UI entries and sliders
    try:
        # Parse the user input for various delays and settings
        initial_delay = float(initial_delay_entry.get_text())
        min_delay = float(min_delay_entry.get_text())
        max_delay = float(max_delay_entry.get_text())
        pause_delay_min = float(pause_delay_min_entry.get_text())
        pause_delay_max = float(pause_delay_max_entry.get_text())
        humanization_level = int(humanization_scale.get_value())
        random_pause_frequency = int(random_pause_scale.get_value())
    except ValueError:
        # In case of invalid input, show error message and return
        status_label.set_text("Invalid delay. Please enter numbers.")
        return

    # Retrieve the text to type from the text box widget
    buffer = text_box.get_buffer()  
    start_iter, end_iter = buffer.get_start_iter(), buffer.get_end_iter()
    text = buffer.get_text(start_iter, end_iter, True).strip()  # Strip any extra spaces

    # Disable the start button and enable the stop button
    start_button.set_sensitive(False)
    stop_button.set_sensitive(True)
    status_label.set_text("Waiting for initial delay...")

    # This dictionary defines possible 'nearby' keys for human-like typos on the keyboard
    keyboard_nearby_chars = {
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

    # This function generates a typo for a given character based on its nearby keys
    def get_typo(char):
        if char in keyboard_nearby_chars:
            return random.choice(keyboard_nearby_chars[char])  # Randomly pick a nearby key
        else:
            return char  # Return the original character if no typo is needed

    # Main typing simulation function
    def type_text():
        start_time = time.time()  # Record the start time for typing session
        total_chars = 0
        total_words = 0
        last_wpm_update_time = start_time

        time.sleep(initial_delay)  # Wait for the initial delay before typing starts
        status_label.set_text("Typing in progress...")

        # Calculate typo probability based on humanization level
        typo_chance = max(0.005, (humanization_level * 0.002))  # Minimum typo chance of 0.005

        # Pause chance based on user setting
        pause_chance = (random_pause_frequency / 100.0)
        chars_until_pause = random.randint(40, 60)  # Random number of chars before pause

        typing_start_time = time.time()  # Record start time for typing
        total_typing_time = 0
        total_pause_time = 0
        words_typed_last_interval = 0

        char_count = 0  # Counter for word boundaries (spaces)
        for i, char in enumerate(text):
            if stop_typing:  # Check if typing should be stopped
                status_label.set_text("Typing stopped.")
                break

            # Introduce random typo based on the humanization level
            if random.random() < typo_chance:
                char = get_typo(char)

            # Use subprocess to simulate typing the character (external typing tool)
            subprocess.run(['ydotool', 'type', char])

            char_count += 1
            total_chars += 1

            # When a space or the last character is reached, increment word count
            if char == ' ' or i == len(text) - 1:
                if random.random() < pause_chance:  # Introduce a random pause
                    pause_duration = random.uniform(pause_delay_min, pause_delay_max)
                    time.sleep(pause_duration)
                    total_pause_time += pause_duration

                total_words += 1
                char_count = 0  # Reset the character count for next word

            # Add random delay between characters to simulate human typing
            time.sleep(random.uniform(min_delay, max_delay))

            # Introduce pause after a certain number of characters typed
            if char_count >= chars_until_pause:
                if random.random() < pause_chance:
                    pause_duration = random.uniform(pause_delay_min, pause_delay_max)
                    time.sleep(pause_duration)
                    total_pause_time += pause_duration
                    chars_until_pause = random.randint(40, 60)  # Reset the pause threshold

            # Calculate WPM (Words Per Minute) every second
            elapsed_time = time.time() - last_wpm_update_time
            if elapsed_time >= 1:
                words_typed_last_interval = total_words
                last_wpm_update_time = time.time()

            # Update WPM label every second
            total_typing_time = time.time() - typing_start_time
            if total_typing_time > 0:
                wpm = (total_words / total_typing_time) * 60
                wpm_label.set_text(f"WPM: {int(wpm)}")

        # Final WPM update when typing is complete
        total_typing_time = time.time() - typing_start_time
        if total_typing_time > 0:
            wpm = (total_words / total_typing_time) * 60
            wpm_label.set_text(f"WPM: {int(wpm)}")

        # Update the status label and re-enable the start button
        status_label.set_text("Typing complete.")
        start_button.set_sensitive(True)
        stop_button.set_sensitive(False)

    # Run the typing simulation in a separate thread to avoid blocking the UI
    threading.Thread(target=type_text, daemon=True).start()

# Stop typing function, triggered when the "Stop Typing" button is clicked
def stop_typing_action(button):
    global stop_typing
    stop_typing = True  # Set the flag to stop typing

# Function to update the labels showing the current values of sliders and entries
def update_slider_values(widget=None):
    # Update the UI labels with the current values from the entry widgets
    initial_delay_label.set_text(f"Initial Delay (seconds): {initial_delay_entry.get_text()}")
    min_delay_label.set_text(f"Min Delay (seconds): {min_delay_entry.get_text()}")
    max_delay_label.set_text(f"Max Delay (seconds): {max_delay_entry.get_text()}")
    pause_delay_min_label.set_text(f"Pause Delay Min (seconds): {pause_delay_min_entry.get_text()}")
    pause_delay_max_label.set_text(f"Pause Delay Max (seconds): {pause_delay_max_entry.get_text()}")
    humanization_label.set_text(f"Humanization Level (0-10): {int(humanization_scale.get_value())}")
    random_pause_label.set_text(f"Random Pause Frequency (0-10): {int(random_pause_scale.get_value())}")

# GTK Window setup
window = Gtk.Window(title="Typing Simulator")
window.set_default_size(600, 500)
window.connect("destroy", Gtk.main_quit)  # Connect the window close event to Gtk.main_quit

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
stop_button.set_sensitive(False)  # Initially, the stop button is disabled
grid.attach(stop_button, 1, 9, 1, 1)

# Connect the value change events for the entries and sliders to update labels
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
