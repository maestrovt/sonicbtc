from data import MidiTask
from note import Note
from utilities import log

Full_STR_Pizzicato = Note()

def send_note_via_mido(task: MidiTask) -> None:
    """
    Use your existing Note.play() to send via 'Logic Pro Virtual In'.
    Adjust channel/CC as you like.
    """
    note = Full_STR_Pizzicato  # or Note() if you prefer a fresh wrapper each time
    note.play(
        pitch=task.pitch,
        duration=task.duration_ms / 1000.0,  # convert ms -> seconds
        channel=task.channel,
        velocity=task.velocity,
        cc=task.controller,
        cc_value=task.controller_value,
    )
def metronome(duration, meter, bars):
    pizz_duration = duration
    pizz_channel = 0
    pizz_cc = 10
    pizz_cc_value = 64

    for h in range(0, bars):
        if (h % meter) == 0:
                pizz_vel = 120
                pizz_pitch = 36
        else:
                pizz_vel = 40
                pizz_pitch = 24
        log(f"Pizz Velocity: {pizz_vel}, Pizz. Pitch: {pizz_pitch}, Bar: {h}")
        Full_STR_Pizzicato.play(pizz_pitch, pizz_duration, pizz_channel, pizz_vel, pizz_cc, pizz_cc_value)
