from mido import Message
import mido
import time

class Note:
    def __init__(self):
        self._pitch = None
        self._duration = None
        self._channel = None
        self._velocity = None
        self._msg_on = None
        self._msg_off = None
        self._cc = None
        self._cc_value = None
        self._cc_msg = None


    def play(self, pitch, duration, channel, velocity, cc, cc_value):
        with mido.open_output('Logic Pro Virtual In') as outport:  
            self._pitch = pitch
            self._duration = duration
            self._channel = channel
            self._velocity = velocity
            self._cc = cc
            self._cc_value = cc_value
            self._cc_msg = Message('control_change', channel = self._channel, control = self._cc, value = self._cc_value)
            self._msg_on = Message('note_on', note = self._pitch, channel = self._channel, velocity = self._velocity)
            self._msg_off = Message('note_off', note = self._pitch, channel = self._channel)
            outport.send(self._cc_msg)
            outport.send(self._msg_on)
            time.sleep(self._duration)
            outport.send(self._msg_off)
            time.sleep(self._duration)
