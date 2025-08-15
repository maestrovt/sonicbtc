# sonicbtc
sonification of bitcoin blockchain
This sonification is using a `signet` server with these entries into `bitcoin.conf`:
``` [signet]
signetchallenge=0014499f05f4ce7bb60222487cf331b91aad6952ef2b
addnode=165.227.230.64:38332
addnode=54.193.6.128:11312```
Bitcoin core is launched via `bitcoind -signet -daemon`.
In macOS, the default location for the bitcoin data files is `/Users/$Username/Library/Application Support/Bitcoin`
`signet` is a subfolder.
Preliminary step to sonification is to get a timeline of events happening and what sort of data is available.
1. Date and time (probably only elapsed time from launch of program). In one run, starts at 12:20:45, ends at 12:22:42.
2. Block number
3. Block hash
4. Finding of a matching witness program (coins we have received)
    a. transaction id
    b. output number
    c. balance update (increase)
5. Finding of a matching pubkey (coins we have spent)
    a. transaction id
    b. pubkey
    c. balance update (decrease)
I may revise this data set, but wanted to start with a pizzicato motif for the block count.
Using Full STR Pizzicato which ranges from C0 to D5
On my MacBook Pro, it takes ~2 minutes = 120 seconds to process 300 blocks = 0.4 sec per block. This would correspond to a temp of 60/0.4 = 150 BPM. To allow time for sound and graphics, let's say that we slow it down to quarter = 108 and have the duration set to an eighth note. Then the duration of the eighth note = 60 sec/1 min x 1 min/108 beats x 0.5 = 0.278 secs/beat.
That seems a bit slow, so I adjusted it to 0.2 secs/eighth note --> 60 secs/1 min x 1 quarter note/0.4 secs = 150.

Implemented a thread structure so the `metronome` class is no longer being used. A short string sound is used starting at C0 (MIDI pitch = 24), then moving up the standard overtone scale in increments of 20 blocks.

Now I want to use the Todi Thaat Indian classical music raga scale to sonify the `BalanceUpdated` data class. One approach would be to start the scale at a given fundamental of the overtone series for every 1 BTC threshold:
- 00 - 01 BTC Fundamental (1)
- 01 - 02 BTC 02
- 02 - 03 BTC 03
- 03 - 04 BTC 04
- 04 - 05 BTC 05
- 05 - 06 BTC 06
- 06 - 07 BTC 07
- 07 - 08 BTC 08
- 08 - 09 BTC 09
- 09 - 10 BTC 10
- 10 - 11 BTC 11
- 11 - 12 BTC 12
- 12 - 13 BTC 13
- 13 - 14 BTC 14
- 14 - 15 BTC 15

The Todi Thaat has unequal divisions: 1/12, 1/6, 1/4, 1/12, 1/12, 1/4, 1/12,


