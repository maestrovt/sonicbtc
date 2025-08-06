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
That seems a bit slow, so I adjusted it to 0.2 secs/eighth note --> 60 secs/1 min x 1 quarter note/0.4 secs = 150

