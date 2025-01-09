import time
import numpy as np
import tifffile
import cv2
from tqdm import tqdm
import os


def tiff_to_video(
    tiff_path: str,
    output_path: str,
    fps: int = 30,
    output_format: str = "mp4",
    use_color: bool = False
):
    """
    Converts a multi-page TIFF stack to a video format.
    
    Parameters
    ----------
    tiff_path : str
        Path to the input TIFF file.
    output_path : str
        Path to the output video file.
    fps : int
        Frames per second for the output video.
    output_format : str
        Video format extension ('avi' or 'mp4'). 
        If 'mp4', choose an appropriate fourcc code for H.264 or similar.
    use_color : bool
        Set to True if your images are RGB. For a single-channel grayscale, use False.
    """
    # 1) Read TIFF file in memory-mapped mode
    print(f"Loading TIFF stack from: {tiff_path}")
    tiff_array = tifffile.memmap(tiff_path)  # shape -> (num_frames, height, width) or (num_frames, height, width, channels)

    # If your TIFF is shape: (num_frames, height, width), then "use_color=False"
    # If your TIFF is shape: (num_frames, height, width, 3), then "use_color=True"
    num_frames = tiff_array.shape[0]
    height = tiff_array.shape[1]
    width = tiff_array.shape[2] if not use_color else tiff_array.shape[2]
    
    if use_color:
        # If your TIFF is already RGB, shape might be (num_frames, height, width, 3)
        # Adjust accordingly:
        height = tiff_array.shape[1]
        width = tiff_array.shape[2]
    else:
        # For single-channel grayscale, OpenCV expects a 2D array, but we specify `isColor=False`
        pass

    # 2) Choose a FourCC codec depending on desired output format
    #    - For AVI with MJPEG: cv2.VideoWriter_fourcc(*'MJPG')
    #    - For MP4 (H.264), you could try: cv2.VideoWriter_fourcc(*'avc1') or cv2.VideoWriter_fourcc(*'H264')
    
    if output_format.lower() == 'avi':
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')  # or 'XVID'
    elif output_format.lower() == 'mp4':
        fourcc = cv2.VideoWriter_fourcc(*'H264')  # H.264 baseline
    else:
        raise ValueError(f"Unsupported output_format '{output_format}'. Use 'avi' or 'mp4'.")
    
    # 3) Create the VideoWriter
    print(f"Creating VideoWriter for {output_path} at {fps} FPS...")
    # Note: For grayscale, pass isColor=False. For color, pass isColor=True.
    out = cv2.VideoWriter(
        filename=output_path,
        fourcc=fourcc,
        fps=fps,
        frameSize=(width, height),
        isColor=use_color
    )
    
    # 4) Convert frames and write to video with a progress bar
    print("Converting frames and writing to video...")
    start_time = time.time()
    for i in tqdm(range(num_frames), desc="Processing frames"):
        # Read one frame (grayscale or color)
        frame = tiff_array[i]

        # If the TIFF is 16-bit or 32-bit, OpenCV expects 8-bit, so we might need to convert:
        if frame.dtype != np.uint8:
            # Scale down or do a suitable conversion
            frame = cv2.convertScaleAbs(frame)

        # If grayscale, shape = (height, width). If color, shape = (height, width, 3).
        out.write(frame)

    # 5) Release resources
    out.release()
    end_time = time.time()

    # 6) Performance reporting
    total_time = end_time - start_time
    avg_fps = num_frames / total_time if total_time > 0 else 0
    print(f"\nConversion complete.")
    print(f"Total frames processed: {num_frames}")
    print(f"Total processing time: {total_time:.2f} seconds")
    print(f"Approx. processing rate: {avg_fps:.2f} frames per second")


def parse_bids_files_and_convert(parent_directory, fps=30, output_format="mp4", use_color=False):
    found_files = []
    for root, dirs, files in os.walk(parent_directory):
        for file in files:
            if file.endswith("pupil.ome.tiff"):
                full_path = os.path.join(root, file)
                found_files.append(full_path)

    processed_dir = os.path.join(parent_directory, "data", "processed")

    print("Identified the following TIFF files:")
    for file_path in found_files:
        print(file_path)
    print(f"\nProcessed data will be saved to: {processed_dir}")

    user_input = input("\nContinue with conversion? (y/n): ")
    if user_input.lower().startswith('y'):
        os.makedirs(processed_dir, exist_ok=True)
        for file_path in found_files:
            base_filename = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(processed_dir, base_filename + f".{output_format}")
            tiff_to_video(
                tiff_path=file_path,
                output_path=output_path,
                fps=fps,
                output_format=output_format,nonlocal
                use_color=use_color
            )
    else:
        print("Conversion canceled.")


if __name__ == "__main__":
    tiff_path = r"C:\Users\SIPE_LAB\Desktop\habituation-sub-GS18_ses-01_task-widefield_pupil.ome.tiff"   # Replace with your TIFF file path
    output_path = r"C:/Users/SIPE_LAB/Desktop/output_video.mp4" # Could be "output_video.mp4"
    frames_per_second = 30

    parse_bids_files_and_convert(
        parent_directory=r"F:\jgronemeyer",
        fps=frames_per_second,
        output_format="mp4",
        use_color=False
    )