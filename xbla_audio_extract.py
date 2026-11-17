import struct
import os
import wave

def get_sound_info(data, sound_offset):
    # ALSound Struct
    env_off, key_off, wave_off, pan, vol, flags, _ = struct.unpack_from(">IIIBBBB", data, sound_offset)
    wave_base, wave_len, wave_type, wave_flags = struct.unpack_from(">IIBB", data, wave_off)
    
    # Get the hijacked sample rate from the book offset
    loop_off, book_off = struct.unpack_from(">II", data, wave_off + 12)
    sample_rate, _ = struct.unpack_from(">ii", data, book_off)
    
    return {
        "wave_base": wave_base,
        "wave_len": wave_len,
        "sample_rate": sample_rate if sample_rate > 2 else 44100
    }

def process_bank(ctl_file, tbl_file, output_dir, prefix):
    print(f"\n--- Extracting {ctl_file} -> {output_dir} ---")
    os.makedirs(output_dir, exist_ok=True)
    
    with open(ctl_file, 'rb') as f:
        ctl_data = f.read()
    with open(tbl_file, 'rb') as f:
        tbl_data = f.read()
        
    _, _, bank_offset = struct.unpack_from(">HHI", ctl_data, 0)
    inst_count, _, _, _, perc_offset = struct.unpack_from(">HBBII", ctl_data, bank_offset)
    inst_array_offset = bank_offset + 12
    
    inst_offsets = [struct.unpack_from(">I", ctl_data, inst_array_offset + i*4)[0] for i in range(inst_count)]
    if perc_offset != 0: inst_offsets.append(perc_offset)
        
    exported_count = 0

    # --- STEP 1: CREATE DUMMY sfx_0000.wav FOR SFX BANK ---
    # The XBLA soundbank starts at s=0 with the Rocket, but the N64 engine enum reserves slot 0
    # for the null entry (SFX_0000). We write a silent sfx_0000.wav so the numbering aligns!
    if inst_count == 1:
        dummy_filename = f"{output_dir}/{prefix}_0000.wav"
        with wave.open(dummy_filename, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(22050)
            w.writeframes(b'\x00\x00' * 16)
        exported_count += 1
        print(f"Created {dummy_filename} (SFX_0000 null spacer)")

    # --- STEP 2: EXTRACT ALL SOUNDS ---
    for inst_idx, inst_off in enumerate(inst_offsets):
        if inst_off == 0: continue
        sound_count = struct.unpack_from(">H", ctl_data, inst_off + 14)[0]
        
        for s in range(sound_count):
            snd_off = struct.unpack_from(">I", ctl_data, inst_off + 16 + s*4)[0]
            if snd_off == 0: continue
            
            info = get_sound_info(ctl_data, snd_off)
            if info["wave_len"] == 0: continue
            
            byte_len = info["wave_len"] * 2
            raw_data = tbl_data[info["wave_base"] : info["wave_base"] + byte_len]
            pcm = bytearray()
            
            for i in range(0, len(raw_data), 2):
                pcm.extend(struct.pack("<h", struct.unpack_from(">h", raw_data, i)[0]))
                
            # Formatting filenames:
            # For SFX (inst_count == 1), offset by +1 so s=0 (Rocket) becomes sfx_0001.wav,
            # s=1 (Scanner) becomes sfx_0002.wav, matching sfx_names[] in the engine!
            if inst_count == 1:
                filename = f"{output_dir}/{prefix}_{s + 1:04d}.wav"
            else:
                filename = f"{output_dir}/{prefix}_inst{inst_idx:03d}_snd{s:02d}.wav"
                
            with wave.open(filename, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(info["sample_rate"])
                w.writeframes(pcm)
            
            exported_count += 1
            if s % 100 == 0:
                print(f"Exported {filename} at {info['sample_rate']} Hz...")
            
    print(f"SUCCESS: Exported {exported_count} sounds to {output_dir}")

# Process SFX and Music
process_bank("pd_sfx_360.ctl", "pd_sfx_360.tbl", "output_xbla_sfx", "sfx")
process_bank("pd_seq_360.ctl", "pd_seq_360.tbl", "output_xbla_seq", "seq")
