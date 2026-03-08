"""Entry point: parse CLI args, launch QApplication + MainWindow."""
import argparse
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QFileDialog

from src.main_window import MainWindow


def main() -> None:
    parser = argparse.ArgumentParser(description="Folder Size Viewer")
    parser.add_argument("path", nargs="?", type=Path, help="Folder to scan")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Folder Size Viewer")

    start_path: Path | None = args.path

    if start_path and not start_path.is_dir():
        print(f"Error: '{start_path}' is not a directory", file=sys.stderr)
        sys.exit(1)

    window = MainWindow(start_path=start_path)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
