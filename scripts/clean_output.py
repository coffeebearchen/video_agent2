from pathlib import Path


output_dir = Path("output")
files = list(output_dir.glob("*.png"))

for file_path in files:
    file_path.unlink()

print(f"Deleted {len(files)} files")