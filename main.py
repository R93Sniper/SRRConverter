from pathlib import Path
import fbx
from ConvertSRM import convert_srm_to_fbx

INPUT_DIR = Path("Input/SRM")
OUTPUT_DIR = Path("Output")

def main():
    print("Scanning for SRM files...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # linux case sensitive
    srm_files = list(set(list(INPUT_DIR.glob("*.srm")) + list(INPUT_DIR.glob("*.SRM"))))
    if not srm_files:
        print("No SRM files found in 'Input/SRM/'. Please add SRM files and try again.")
        return
    else:
        print(f"Found {len(srm_files)} SRM file(s).")

    print("Initializing FBX SDK Manager...")
    manager = fbx.FbxManager.Create()
    if not manager:
        print("Failed to create FBX Manager. Exiting.")
        return
    print("FBX SDK initialized.")

    for srm_path in srm_files:
        print(f"\nProcessing '{srm_path.name}'...")

        scene = convert_srm_to_fbx(srm_path, manager)
        if not scene:
            print(f"Conversion failed for {srm_path.name}. Skipping.")
            continue

        output_path = OUTPUT_DIR / f"{srm_path.stem}.fbx"

        exporter = fbx.FbxExporter.Create(manager, "")
        if not exporter.Initialize(str(output_path)):
            print(f"FBX Exporter failed to initialize for {output_path}.")
            continue

        if exporter.Export(scene):
            print(f"Successfully exported: {output_path}")
        else:
            print(f"Export failed: {output_path}")
        exporter.Destroy()

    print("\nCleaning up FBX manager...")
    manager.Destroy()
    print("Done.")

if __name__ == "__main__":
    main()
