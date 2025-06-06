import os
import re
import simplekml
from obspy.imaging.beachball import beachball
import sys
import matplotlib.pyplot as plt
from tqdm import tqdm

# Force UTF-8 encoding for all outputs
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def classify_and_color_by_rake(rake):
    """
    Classifies fault type and assigns a color based on the rake angle.
    - Normal: Red
    - Thrust: Blue
    - Strike-Slip: Green
    - Oblique: Yellow
    Returns a tuple: (fault_type_string, color_string)
    """
    if -120 <= rake <= -60:
        return 'Normal', 'green'
    elif 60 <= rake <= 120:
        return 'Thrust', 'red'
    elif -30 <= rake <= 30 or rake >= 150 or rake <= -150:
        return 'Strike-Slip', 'blue'
    else:
        return 'Oblique', 'yellow'

def create_kml_from_custom_ndk(filepath, output_kml_file):
    """
    Final Version 12.0: Organizes placemarks into toggleable folders by
    fault type within the KML file.
    """
    print(f"Reading and manually parsing file: {filepath}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"\nFATAL ERROR: Could not read the file. Details: {e}")
        return

    # --- Initialize KML and folders ---
    kml = simplekml.Kml(name=f"Focal Mechanisms from {os.path.basename(filepath)}")
    kml.document.description = (
        '<![CDATA['
        '<b>Beachball Color Legend (by Fault Type)</b><br>'
        '<br><font color="red">■</font> Normal'
        '<br><font color="blue">■</font> Thrust (Reverse)'
        '<br><font color="green">■</font> Strike-Slip'
        '<br><font color="yellow">■</font> Oblique'
        ']]>'
    )
    
    image_dir = "assets"
    os.makedirs(image_dir, exist_ok=True)
    print(f"Beachball images will be saved in the '{image_dir}' folder.")
    
    # --- THIS IS THE NEW FOLDER STRUCTURE ---
    # Create a parent folder for better organization
    fm_parent_folder = kml.newfolder(name="Events with Focal Mechanisms")
    # Create a sub-folder for each fault type that can be toggled
    folder_map = {
        'Normal': fm_parent_folder.newfolder(name="Normal"),
        'Thrust': fm_parent_folder.newfolder(name="Thrust (Reverse)"),
        'Strike-Slip': fm_parent_folder.newfolder(name="Strike-Slip"),
        'Oblique': fm_parent_folder.newfolder(name="Oblique")
    }
    # Folder for events without solutions
    events_without_fm_folder = kml.newfolder(name="Events without Focal Mechanisms")

    # --- Counters ---
    events_processed_with_fm = 0
    events_processed_without_fm = 0
    events_skipped = 0
    
    # --- Group lines into event chunks ---
    events = []
    current_event = []
    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue
        if clean_line.startswith(('PDEQ', 'PDEW', 'SWEQ')) and current_event:
            events.append(current_event)
            current_event = []
        current_event.append(clean_line)
    if current_event:
        events.append(current_event)

    print(f"Found {len(events)} potential event entries in the file.")
    
    print("\nProcessing events...")
    for i, event_lines in enumerate(tqdm(events, desc="Creating KML")):
        try:
            if len(event_lines) < 5:
                events_skipped += 1
                continue

            pde_line = event_lines[0]
            sdr_line = event_lines[4]

            pde_parts = pde_line.split()
            time_str = f"{pde_parts[1]} {pde_parts[2]}"
            lat = float(pde_parts[3])
            lon = float(pde_parts[4])
            depth = float(pde_parts[5])
            mag = float(pde_parts[7])
            location = " ".join(pde_parts[8:])
            
            sdr_parts = sdr_line.split()
            
            if len(sdr_parts) >= 6:
                strike = float(sdr_parts[-6])
                dip = float(sdr_parts[-5])
                rake = float(sdr_parts[-4])
                
                if strike == 0 and dip == 0:
                    raise ValueError("No focal mechanism data")

                fault_type, beachball_color = classify_and_color_by_rake(rake)

                beachball_filename = os.path.join(image_dir, f"event_{i+1}_fm.png")
                beachball([strike, dip, rake], size=200, outfile=beachball_filename, facecolor=beachball_color, edgecolor='black')
                plt.close('all')

                # --- SELECT THE CORRECT FOLDER BASED ON FAULT TYPE ---
                target_folder = folder_map[fault_type]
                pnt = target_folder.newpoint(name=f"M {mag}")
                
                pnt.style.iconstyle.icon.href = beachball_filename
                pnt.description = (f"<b>Fault Type:</b> {fault_type}<br/>"
                                   f"<b>Time:</b> {time_str} UTC<br/>"
                                   f"<b>Magnitude:</b> {mag}<br/>"
                                   f"<b>Depth:</b> {depth:.1f} km<br/>"
                                   f"<b>Location:</b> {lat:.3f}, {lon:.3f}<br/>"
                                   f"<b>Strike/Dip/Rake:</b> {strike}/{dip}/{rake}")
                pnt.coords = [(lon, lat, -depth * 1000)]
                events_processed_with_fm += 1
            else:
                raise ValueError("No focal mechanism data")

        except Exception:
            try:
                pnt = events_without_fm_folder.newpoint(name=f"M {mag}")
                pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'
                pnt.description = (f"<b>Time:</b> {time_str} UTC<br/>"
                                   f"<b>Magnitude:</b> {mag}<br/>"
                                   f"<b>Depth:</b> {depth:.1f} km<br/>"
                                   f"<b>Location:</b> {lat:.3f}, {lon:.3f}<br/>"
                                   f"<b>Focal Mechanism:</b> Not available")
                pnt.coords = [(lon, lat, -depth * 1000)]
                events_processed_without_fm += 1
            except:
                events_skipped += 1
                
    # --- Finalization ---
    kml.save(output_kml_file)
    print("\n--- All Done! ---")
    print(f"✅ Successfully processed {events_processed_with_fm} events with focal mechanisms.")
    print(f"✅ Successfully processed {events_processed_without_fm} events without focal mechanisms.")
    print(f"❌ Skipped {events_skipped} events due to parsing errors.")
    print(f"\nKML file created: {output_kml_file}")

# =============================================================================
if __name__ == "__main__":
    data_file_to_process = "SPUD_NDK_bundle_2025-06-06T16.47.05.txt"
    output_kml = "focal_mechanisms.kml"

    if os.path.exists(data_file_to_process):
        create_kml_from_custom_ndk(data_file_to_process, output_kml)
    else:
        print("-" * 60)
        print(f"ERROR: Input file not found -> '{data_file_to_process}'")
        print("Please make sure your data file is in the same folder as this Python script")
        print("and that the filename above matches your file exactly.")
        print("-" * 60)
