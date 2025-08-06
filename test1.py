# from mido import Message
from note import Note
# import mido
# import time

note = Note()
pitch = 28
duration = 0.125
channel = 1
velocity = 64
cc = 10
cc_value = 64
note.play(pitch, duration, channel, velocity, cc, cc_value)
# msg = Message('note_on', note = 60)
# print(msg)
# msg_2 = Message('note_off', note = 60)
# print(msg_2)

# with mido.open_output('Logic Pro Virtual In') as outport:
    # outport.send(msg)
    # time.sleep(0.5)
    # outport.send(msg_2)

# print(mido.get_output_names())