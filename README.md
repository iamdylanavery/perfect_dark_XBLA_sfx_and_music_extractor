# Perfect Dark XBLA Audio Extractor

A lightweight, dependency-free Python script to extract high-quality,
uncompressed audio assets (both Sound Effects and Musical Instruments) from the
Perfect Dark Xbox Live Arcade (XBLA) remaster files (pd_sfx_360 and pd_seq_360).

These extracted .wav files match the internal N64 sound IDs, making them
suitable for use with custom PC port audio wrappers (such as external audio
replacement systems).

## The Reverse-Engineering Journey

When 4J Studios ported Perfect Dark to the Xbox 360, they wrapped and emulated
much of the original N64 codebase. To minimize structural modifications to the
audio engine, they preserved the legacy SGI libaudio pointer layouts and file
extensions (.ctl and .tbl).

However, extracting these assets presented several highly specific structural
anomalies that we had to systematically debug:

## 1. The Codec Illusion

Standard N64 audio uses Nintendo's proprietary VADPCM compression (Type 0). The
XBLA .ctl files still declared all wave types as Type 0, leading initial
extraction attempts down the path of VADPCM decompression. This resulted in pure
digital static.

Upon analyzing the raw hexadecimal bytes of the .tbl file, we discovered that
the audio had actually been flattened into raw, uncompressed, Big-Endian 16-bit
PCM. The engine simply bypassed the legacy N64 VADPCM decoding step, but left
the structural headers intact so the memory manager wouldn't panic.

## 2. The 50% Truncation Bug (Samples vs. Bytes)

Our early PCM extraction runs successfully produced clean audio, but every
single file was cut off exactly halfway through its duration (e.g., a 1.6-second
rocket launch was cut off at exactly 0.8 seconds).

We discovered that in the N64 .ctl file, wave_len represented the compressed
ADPCM byte count. For the XBLA version, 4J Studios modified wave_len to
represent the total sample count. Because uncompressed 16-bit PCM requires 2
bytes per sample, we were only reading half of the file. Multiplying wave_len
by 2 restored the full, untruncated duration of every sound.

## 3. Structural Shifts & Silent Offsets

During early sequence bank extraction, the script crashed with buffer alignment
errors. The N64 ALInstrument struct header is exactly 16 bytes of metadata
before the soundArray pointers begin.

An incorrect offset assumption had the script reading pointers from offset 20
instead of 16. In the SFX bank (which is one giant instrument of 1,545 sounds),
this caused a silent index shift where Sound 0 was skipped and all sound IDs
were misaligned by 1. In the Music Sequence bank (where instruments are small
and usually contain only 1 sound), reading from offset 20 caused the script to
read the next instrument's volume/pan header (0x7f400500) as a pointer, causing
an immediate crash. Correcting this offset to 16 resolved the crashes and
aligned all sound IDs perfectly with the native engine.

## 4. Sample Rate Hijacking

On the N64, individual sample rates are not stored directly. Instead, the engine
dynamically calculates pitch based on a universal Bank Rate and individual MIDI
tuning keys (KeyBase and Detune).

In the XBLA version, the order field of the ALADPCMBook (which is always 2 on
the N64) was hijacked. 4J Studios utilized this 32-bit field to embed the
original master sample rate of the WAV asset (e.g., 0x00002b11 = 11025 Hz). Our
script extracts this value directly to write accurate WAV headers, defaulting
back to N64-style Bank math if the field is unpopulated.

## Prerequisites

To run this extractor, you will need:

1.  Python 3 installed on your system.
2.  The asset files from a legitimate copy of the Xbox Live Arcade version of
    Perfect Dark:
      - pd_sfx_360.ctl
      - pd_sfx_360.tbl
      - pd_seq_360.ctl
      - pd_seq_360.tbl

## Usage

1.  Copy the Python script (extract.py) into a folder.

2.  Place your four .ctl and .tbl files into the same folder.

3.  Open a terminal or command prompt in that directory and run:

    python xbla_audio_extract.py

## Output

The script will automatically create two output directories:

  - output_xbla_sfx/: Contains 1,545 sound effects named sequentially (e.g.,
    sfx_0000.wav to sfx_1544.wav). These align directly with the global SFX IDs
    utilized by the game engine.
  - output_xbla_seq/: Contains the sequence/music bank instruments mapped by
    instrument index and sound sub-index (e.g., seq_inst002_snd00.wav).

Credits

Special thanks to the reverse-engineering efforts and joint debugging steps that
mapped the alignment of the SGI libaudio structures and decoded the proprietary
modifications made for the Xbox 360 remaster.
