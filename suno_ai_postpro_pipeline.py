# ==============================================================================
# AI-Generated Music Post-Production Pipeline
# ==============================================================================
#
# This script implements the 7-step post-production workflow for AI-generated
# music as specified. It is designed to be run in a Google Colab environment.
#
# To use in Colab, paste each major section (e.g., Setup, Configuration,
# Pipeline Steps, etc.) into a separate cell.

# ==============================================================================
# CELL 1: Environment Setup
# ==============================================================================
#
# Run this cell first to install all necessary dependencies.

"""
# Remove comment markers and run this block in a Colab cell

# 1. Install system packages and build tools
!apt-get update
!apt-get install -y --no-install-recommends ffmpeg lv2file liblilv-dev rubberband-cli git build-essential
!apt-get install -y lsp-plugins-lv2

# 2. Clone and install Airwindows LV2 plugins
!git clone https://github.com/hannesbraun/airwindows-lv2.git
%cd airwindows-lv2
!make install
%cd ..
!rm -rf airwindows-lv2

# 3. Clone RVC-WebUI and install its dependencies
!git clone https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git
%cd RVC-WebUI
# The RVC requirements are extensive; we install them from its requirements file.
# We skip torch/torchaudio as we install specific versions for Colab below.
!sed -i '/torch/d' requirements.txt
!sed -i '/torchaudio/d' requirements.txt
!sed -i '/tensorboard/d' requirements.txt
!pip install -r requirements.txt --quiet
%cd ..

# 4. Install Python packages
!pip install --quiet \
    bs_roformer \
    pedalboard \
    pyloudnorm \
    matchering==2.0.6 \
    soundfile \
    librosa \
    ffmpeg-python

# 5. Set LV2_PATH environment variable for plugins to be found
import os
os.environ['LV2_PATH'] = '/root/.lv2:/usr/lib/lv2:/usr/local/lib/lv2'

print("✅ Environment setup complete.")

"""

# ==============================================================================
# CELL 2: Imports and Configuration
# ==============================================================================

import os
import subprocess
import soundfile as sf
import pyloudnorm as pyln
import numpy as np
from pedalboard import Pedalboard, Compressor, EQ, Gain, Limiter, load_plugin
from pedalboard.io import AudioFile
import matchering as mg
import ffmpeg
import requests
import shutil

# --- Main Configuration ---

# Input file: Upload your song to Colab and put the path here
INPUT_SONG = "input_song.wav"

# Output directory for all generated files
OUTPUT_DIR = "output"

# RVC Model: Upload your RVC model (.pth) and index (.index) files
# and specify their paths here.
RVC_MODEL_PATH = "/content/RVC-WebUI/models/my_voice.pth"  # <-- IMPORTANT: SET YOUR .pth FILE PATH
RVC_INDEX_PATH = "/content/RVC-WebUI/models/my_voice.index" # <-- IMPORTANT: SET YOUR .index FILE PATH
RVC_PITCH_SHIFT = 0  # Transposition in semitones

# Reference track for mastering
# This will be downloaded automatically.
# To use the alternative, change the URL and FILENAME.
REF_URL = "https://cdn.free-stock-music.com/mp3/teknoaxe-above-all-the-chaos.mp3"
REF_FILENAME_MP3 = "ref_teknoaxe.mp3"
REF_FILENAME_WAV = "ref_teknoaxe.wav"

# --- Directory Setup ---
STEMS_DIR = os.path.join(OUTPUT_DIR, "1_stems")
RVC_DIR = os.path.join(OUTPUT_DIR, "2_rvc_vocals")
PROCESSED_DIR = os.path.join(OUTPUT_DIR, "3_processed_stems")
MIX_DIR = os.path.join(OUTPUT_DIR, "4_mixdown")
MASTER_DIR = os.path.join(OUTPUT_DIR, "5_master")

# ==============================================================================
# CELL 3: Helper Functions
# ==============================================================================

def setup_directories():
    """Creates all necessary output directories."""
    print("Setting up output directories...")
    for path in [OUTPUT_DIR, STEMS_DIR, RVC_DIR, PROCESSED_DIR, MIX_DIR, MASTER_DIR]:
        os.makedirs(path, exist_ok=True)

def download_reference_track():
    """Downloads and converts the reference track for mastering."""
    print(f"Downloading reference track: {REF_URL}")
    if os.path.exists(REF_FILENAME_WAV):
        print("Reference WAV already exists. Skipping download.")
        return
    try:
        response = requests.get(REF_URL)
        response.raise_for_status()
        with open(REF_FILENAME_MP3, 'wb') as f:
            f.write(response.content)

        print("Converting reference track to WAV...")
        (
            ffmpeg
            .input(REF_FILENAME_MP3)
            .output(REF_FILENAME_WAV, acodec='pcm_s16le', ar=48000)
            .overwrite_output()
            .run(quiet=True)
        )
        os.remove(REF_FILENAME_MP3)
        print(f"Reference track ready: {REF_FILENAME_WAV}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading reference track: {e}")
        raise

# ==============================================================================
# CELL 4: Pipeline Step Implementations
# ==============================================================================

# --- STEP 1: 4-Track Separation ---
def separate_stems(input_file, output_dir):
    print("--- Step 1: Separating audio into 4 stems with BS-RoFormer ---")
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input song '{input_file}' not found. Please upload it.")

    cmd = [
        "bs_roformer",
        "--input", input_file,
        "--output_dir", output_dir,
        "--model_type", "bs_roformer_hq_ep_300"
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    print("✅ Stems separated successfully.")


# --- STEP 2: Vocal Replacement ---
def replace_vocals_rvc(stems_dir, output_dir):
    print("--- Step 2: Replacing vocals using RVC ---")
    vocals_in = os.path.join(stems_dir, "vocals.wav")
    vocals_out = os.path.join(output_dir, "vocals_rvc.wav")

    if not os.path.exists(RVC_MODEL_PATH) or not os.path.exists(RVC_INDEX_PATH):
        print("⚠️ RVC model or index file not found. Skipping vocal replacement.")
        print(f"Expected model at: {RVC_MODEL_PATH}")
        print(f"Expected index at: {RVC_INDEX_PATH}")
        print("Copying original vocals instead.")
        shutil.copy(vocals_in, vocals_out)
        return

    rvc_script = "/content/RVC-WebUI/tools/infer_cli.py"
    cmd = [
        "python", rvc_script,
        "--f0up_key", str(RVC_PITCH_SHIFT),
        "--input_path", vocals_in,
        "--index_path", RVC_INDEX_PATH,
        "--f0method", "rmvpe",
        "--model_path", RVC_MODEL_PATH,
        "--output_path", vocals_out,
        "--index_rate", "0.75",
        "--filter_radius", "3",
        "--resample_sr", "48000",
        "--rms_mix_rate", "0.25",
        "--protect", "0.33"
    ]
    print("Executing RVC inference...")
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
    print("✅ Vocal replacement successful.")


# --- STEP 3: Stem Cleaning & Processing ---
def _process_stem_ffmpeg_first(infile, filters):
    """Helper to apply initial FFmpeg filters and return a temporary file path."""
    temp_file = infile + ".temp.wav"
    (
        ffmpeg
        .input(infile)
        .filter_multi_output(filters)
        .output(temp_file, ar=48000) # Ensure 48kHz for pedalboard
        .overwrite_output()
        .run(quiet=True)
    )
    return temp_file

def _process_stem_pedalboard(temp_file, board, outfile):
    """Helper to apply a pedalboard chain to the temp file."""
    with AudioFile(temp_file) as f:
        audio = f.read(f.frames)
        samplerate = f.samplerate

    processed = board(audio, samplerate)

    with AudioFile(outfile, 'w', samplerate, processed.shape[0]) as f:
        f.write(processed)

    os.remove(temp_file)

def process_all_stems(rvc_dir, stems_dir, processed_dir):
    print("--- Step 3: Cleaning and processing all stems ---")

    # Vocals
    print("Processing vocals...")
    vocals_in = os.path.join(rvc_dir, "vocals_rvc.wav")
    vocals_out = os.path.join(processed_dir, "vocals.wav")
    temp_file = _process_stem_ffmpeg_first(vocals_in, [
        {'filter': 'firequalizer', 'args': {'gain_expr': 'if(lt(f,90),-18,if(gt(f,16000),-15,0))', 'zero_phase': 'true'}},
        {'filter': 'afftdn', 'args': {'nf': -25}}
    ])
    deesser = load_plugin("http://lsp-plug.in/plugins/deesser_stereo")
    deesser.detection = 4000.0 # Set sensible defaults
    deesser.ratio = 4.0
    limiter = load_plugin("http://lsp-plug.in/plugins/fast_limiter_stereo")
    limiter.limit = -0.5
    vocal_board = Pedalboard([
        deesser,
        EQ(center_frequency_hz=250, q=2, gain_db=-3),
        EQ(center_frequency_hz=3000, q=2, gain_db=+2),
        EQ(center_frequency_hz=12000, q=1.5, gain_db=+3),
        Compressor(threshold_db=-18, ratio=3, attack_ms=10, release_ms=120),
        limiter
    ])
    _process_stem_pedalboard(temp_file, vocal_board, vocals_out)

    # Drums
    print("Processing drums...")
    drums_in = os.path.join(stems_dir, "drums.wav")
    drums_out = os.path.join(processed_dir, "drums.wav")
    temp_file = _process_stem_ffmpeg_first(drums_in, [
        {'filter': 'highpass', 'args': {'f': 45}},
        {'filter': 'lowpass', 'args': {'f': 18000}}
    ])
    saturator = load_plugin("http://lsp-plug.in/plugins/saturator_stereo")
    saturator.drive = 2.0
    drum_board = Pedalboard([
        EQ(center_frequency_hz=400, q=3, gain_db=-3),
        Compressor(threshold_db=-12, ratio=2),
        saturator
    ])
    _process_stem_pedalboard(temp_file, drum_board, drums_out)

    # Bass
    print("Processing bass...")
    bass_in = os.path.join(stems_dir, "bass.wav")
    bass_out = os.path.join(processed_dir, "bass.wav")
    temp_file = _process_stem_ffmpeg_first(bass_in, [
        {'filter': 'highpass', 'args': {'f': 30}},
        {'filter': 'lowpass', 'args': {'f': 8000}}
    ])
    basskit = load_plugin("http://hannesbraun.de/plugins/airwindows/BassKit")
    basskit.Boost = 0.3 # Corresponds to boost=3
    bass_board = Pedalboard([
        Compressor(threshold_db=-15, ratio=4),
        basskit
    ])
    _process_stem_pedalboard(temp_file, bass_board, bass_out)

    # Other
    print("Processing 'other' stem...")
    other_in = os.path.join(stems_dir, "other.wav")
    other_out = os.path.join(processed_dir, "other.wav")
    temp_file = _process_stem_ffmpeg_first(other_in, [
        {'filter': 'highpass', 'args': {'f': 110}},
        {'filter': 'lowpass', 'args': {'f': 16000}}
    ])
    other_board = Pedalboard([
        EQ(center_frequency_hz=5000, q=2, gain_db=+2),
        Compressor(threshold_db=-14, ratio=2)
    ])
    _process_stem_pedalboard(temp_file, other_board, other_out)

    print("✅ Stems processed successfully.")


# --- STEP 4: Track Leveling ---
def level_stems(processed_dir):
    print("--- Step 4: Leveling stems to target LUFS & peak ---")
    stems_to_level = {
        "vocals": {"target_lufs": -18.0, "target_peak": -6.0},
        "drums":  {"target_lufs": -14.0, "target_peak": -3.0},
        "bass":   {"target_lufs": -17.0, "target_peak": -5.0},
        "other":  {"target_lufs": -20.0, "target_peak": -7.0},
    }

    meter = pyln.Meter(48000) # Assume 48kHz

    for name, targets in stems_to_level.items():
        filepath = os.path.join(processed_dir, f"{name}.wav")
        data, rate = sf.read(filepath)

        loudness = meter.integrated_loudness(data)
        gain_db = targets["target_lufs"] - loudness

        board = Pedalboard([Gain(gain_db=gain_db)])
        leveled_data = board(data, rate)

        peak_linear = np.max(np.abs(leveled_data))
        target_peak_linear = 10**(targets["target_peak"] / 20.0)

        if peak_linear > target_peak_linear:
            norm_gain = target_peak_linear / peak_linear
            leveled_data *= norm_gain

        sf.write(filepath, leveled_data.T, rate) # Pedalboard outputs (C, N), soundfile needs (N, C)

        final_lufs = pyln.Meter(rate).integrated_loudness(leveled_data.T)
        final_peak = 20 * np.log10(np.max(np.abs(leveled_data)))
        print(f"  Leveled '{name}': LUFS={final_lufs:.2f}, Peak={final_peak:.2f} dBFS")

    print("✅ Stems leveled successfully.")


# --- STEP 5: Mixing ---
def mix_stems(processed_dir, mix_dir):
    print("--- Step 5: Mixing all stems ---")
    stem_files = [os.path.join(processed_dir, f) for f in os.listdir(processed_dir) if f.endswith('.wav')]

    stems_audio = []
    max_len = 0
    samplerate = 48000
    for f in stem_files:
        with AudioFile(f) as af:
            stems_audio.append(af.read(af.frames))
            if af.frames > max_len:
                max_len = af.frames
            samplerate = af.samplerate

    # Pad shorter tracks
    for i, stem in enumerate(stems_audio):
        if stem.shape[1] < max_len:
            padding = np.zeros((stem.shape[0], max_len - stem.shape[1]))
            stems_audio[i] = np.concatenate([stem, padding], axis=1)

    # Sum them up
    mixdown = np.sum(np.array(stems_audio), axis=0)

    # Normalize mix to -4dB peak to leave headroom for mastering
    peak = np.max(np.abs(mixdown))
    target_peak = 10**(-4.0 / 20.0)
    if peak > target_peak:
        mixdown *= (target_peak / peak)

    mix_file = os.path.join(mix_dir, "mixdown.wav")
    with AudioFile(mix_file, 'w', samplerate, mixdown.shape[0]) as f:
        f.write(mixdown)

    print(f"✅ Mixdown saved to {mix_file}")
    return mix_file


# --- STEP 6 & 7: Mastering and Final Export ---
def master_and_export(mix_file, master_dir, ref_wav):
    print("--- Step 6 & 7: Mastering with Matchering and exporting final WAV ---")
    master_file = os.path.join(master_dir, "master_24bit_48kHz.wav")

    mg.process(
        target=mix_file,
        reference=ref_wav,
        results=[
            mg.pcm24(master_file)
        ],
        # Ensure output is 48kHz, though it should be by now
        sample_rate=48000
    )

    data, rate = sf.read(master_file)
    meter = pyln.Meter(rate)
    loudness = meter.integrated_loudness(data)
    peak = 20 * np.log10(np.max(np.abs(data)))

    print("✅ Mastering complete!")
    print(f"Final output: {master_file}")
    print(f"  - Format: 24-bit, {rate} Hz WAV")
    print(f"  - Integrated Loudness: {loudness:.2f} LUFS (Target: ~-13 LUFS)")
    print(f"  - Peak: {peak:.2f} dBFS (Target: -1 dBTP)")


# ==============================================================================
# CELL 5: Main Execution
# ==============================================================================

def main():
    """Run the entire post-production pipeline."""
    try:
        # Initial setup
        setup_directories()
        download_reference_track()

        # Run pipeline
        separate_stems(INPUT_SONG, STEMS_DIR)
        replace_vocals_rvc(STEMS_DIR, RVC_DIR)
        process_all_stems(RVC_DIR, STEMS_DIR, PROCESSED_DIR)
        level_stems(PROCESSED_DIR)
        mix_file = mix_stems(PROCESSED_DIR, MIX_DIR)
        master_and_export(mix_file, MASTER_DIR, REF_FILENAME_WAV)

        print("\n🎉🎉🎉 Pipeline finished successfully! 🎉🎉🎉")
        print(f"Find your final mastered track in the '{MASTER_DIR}' directory.")

    except Exception as e:
        print(f"\n❌ An error occurred during the pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # This block allows running the script directly, but in Colab you would
    # call main() in the final cell.

    # --- Instructions for Colab ---
    # 1. Upload your input song and rename it to "input_song.wav" or change the
    #    INPUT_SONG variable.
    # 2. Upload your RVC .pth and .index files and update the RVC_MODEL_PATH and
    #    RVC_INDEX_PATH variables.
    # 3. Run the cells in order.
    # 4. Call main() in the last cell to start the process.

    # Example of final Colab cell:
    # main()
    pass
