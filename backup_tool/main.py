import os
import shutil
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QTextEdit, QLabel, QHBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal, QObject

class BackupWorker(QObject):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, source_folder, target_folder1, target_folder2):
        super().__init__()
        self.source_folder = source_folder
        self.target_folder1 = target_folder1
        self.target_folder2 = target_folder2

    def run(self):
        total_files = sum(len(files) for _, _, files in os.walk(self.source_folder))
        files_copied1 = 0
        files_copied2 = 0

        for root, dirs, files in os.walk(self.source_folder):
            relative_path = os.path.relpath(root, self.source_folder)

            target_paths = [
                (self.target_folder1, files_copied1),
                (self.target_folder2, files_copied2)
            ]

            for target_path, files_copied in target_paths:
                target_dir = os.path.join(target_path, relative_path)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                for file in files:
                    source_file = os.path.join(root, file)
                    target_file = os.path.join(target_dir, file)

                    if not os.path.exists(target_file) or not self.files_are_equal(source_file, target_file):
                        shutil.copy2(source_file, target_file)
                        self.progress_signal.emit(f"Copied: {source_file} to {target_file}")
                        if target_path == self.target_folder1:
                            files_copied1 += 1
                        else:
                            files_copied2 += 1
                    else:
                        self.progress_signal.emit(f"Skipped (same content): {target_file}")

        self.log_backup(self.target_folder1, files_copied1, total_files)
        self.log_backup(self.target_folder2, files_copied2, total_files)

        self.progress_signal.emit("Backup completed.")
        self.finished_signal.emit()

    def files_are_equal(self, file1, file2):
        """Compare two files using their MD5 hash."""
        return self.get_file_hash(file1) == self.get_file_hash(file2)

    def get_file_hash(self, filename):
        """Compute the MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def log_backup(self, target_folder, files_copied, total_files):
        """Log the backup results to a file in the target folder."""
        log_message = (
            f"Backup completed - {files_copied}/{total_files} files copied from source folder - "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        log_file_path = os.path.join(target_folder, "backup_log.txt")
        with open(log_file_path, "a") as log_file:
            log_file.write(log_message)

class BackupTool(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()
        self.source_folder = ""
        self.target_folder1 = ""
        self.target_folder2 = ""

    def initUI(self):
        layout = QVBoxLayout()

        self.source_label = QLabel("Source Folder:")
        self.target_label1 = QLabel("Target Folder 1:")
        self.target_label2 = QLabel("Target Folder 2:")

        self.source_button = QPushButton("Select Source Folder")
        self.source_button.clicked.connect(self.select_source_folder)

        self.target_button1 = QPushButton("Select Target Folder 1")
        self.target_button1.clicked.connect(self.select_target_folder1)

        self.target_button2 = QPushButton("Select Target Folder 2")
        self.target_button2.clicked.connect(self.select_target_folder2)

        self.backup_button = QPushButton("Backup Now")
        self.backup_button.clicked.connect(self.start_backup)

        self.output_area1 = QTextEdit()
        self.output_area1.setReadOnly(True)
        self.output_area1.setPlaceholderText("Output for Target Folder 1")

        self.output_area2 = QTextEdit()
        self.output_area2.setReadOnly(True)
        self.output_area2.setPlaceholderText("Output for Target Folder 2")

        layout.addWidget(self.source_label)
        layout.addWidget(self.source_button)
        layout.addWidget(self.target_label1)
        layout.addWidget(self.target_button1)
        layout.addWidget(self.target_label2)
        layout.addWidget(self.target_button2)
        layout.addWidget(self.backup_button)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_area1)
        output_layout.addWidget(self.output_area2)

        layout.addLayout(output_layout)

        self.setLayout(layout)
        self.setWindowTitle("Backup Tool")

    def select_source_folder(self):
        self.source_folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        self.source_label.setText(f"Source Folder: {self.source_folder}")

    def select_target_folder1(self):
        self.target_folder1 = QFileDialog.getExistingDirectory(self, "Select Target Folder 1")
        self.target_label1.setText(f"Target Folder 1: {self.target_folder1}")

    def select_target_folder2(self):
        self.target_folder2 = QFileDialog.getExistingDirectory(self, "Select Target Folder 2")
        self.target_label2.setText(f"Target Folder 2: {self.target_folder2}")

    def start_backup(self):
        if not self.source_folder or not self.target_folder1 or not self.target_folder2:
            self.output_area1.append("Please select the source folder and both target folders.")
            self.output_area2.append("Please select the source folder and both target folders.")
            return

        self.executor = ThreadPoolExecutor(max_workers=1)
        self.worker = BackupWorker(self.source_folder, self.target_folder1, self.target_folder2)
        self.worker.progress_signal.connect(self.update_output)
        self.worker.finished_signal.connect(self.on_backup_finished)
        self.executor.submit(self.worker.run)

    def update_output(self, message):
        """Update output areas based on message content."""
        if "Target Folder 1" in message:
            self.output_area1.append(message)
        elif "Target Folder 2" in message:
            self.output_area2.append(message)
        else:
            self.output_area1.append(message)
            self.output_area2.append(message)

    def on_backup_finished(self):
        self.output_area1.append("Backup to Target Folder 1 completed.")
        self.output_area2.append("Backup to Target Folder 2 completed.")

if __name__ == '__main__':
    app = QApplication([])
    window = BackupTool()
    window.show()
    app.exec()
