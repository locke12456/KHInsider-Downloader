import sys
import os
import re
import locale
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'khinsider'))
import khinsider

import i18n

from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, pyqtSlot, QSize
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QCheckBox, QMessageBox, QGroupBox, QStatusBar, QAbstractItemView,
    QStyle
)
from PyQt6.QtGui import QIcon, QFont

# Patch requests.get to include a browser User-Agent.
_original_get = khinsider.requests.get
def _patched_get(*args, **kwargs):
    headers = kwargs.pop('headers', {}) or {}
    headers.setdefault('User-Agent',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36')
    kwargs['headers'] = headers
    return _original_get(*args, **kwargs)
khinsider.requests.get = _patched_get


# ─────────────────────────────────────────────
#  i18n Setup
# ─────────────────────────────────────────────

SUPPORTED_LOCALES = [
    ('en',    'English'),
    ('zh-TW', '繁體中文'),
    ('zh',    '简体中文'),
    ('ja',    '日本語'),
    ('ko',    '한국어'),
]

def setup_i18n():
    """Configure python-i18n to load YAML locale files."""
    locales_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locales')
    i18n.set('load_path', [locales_dir])
    i18n.set('file_format', 'yml')
    i18n.set('fallback', 'en')
    i18n.set('filename_format', '{locale}.{format}')
    i18n.set('enable_memoization', True)

    # Auto-detect system locale (Python 3.13+ compatible)
    try:
        sys_locale = locale.getlocale()[0] or locale.getdefaultlocale()[0] or 'en'
    except Exception:
        sys_locale = 'en'
    # Map system locale codes to our supported codes
    locale_map = {
        'zh_TW': 'zh-TW', 'zh_Hant': 'zh-TW',
        'zh_CN': 'zh', 'zh_Hans': 'zh', 'zh': 'zh',
        'ja': 'ja', 'ja_JP': 'ja',
        'ko': 'ko', 'ko_KR': 'ko',
    }
    detected = locale_map.get(sys_locale, None)
    if detected is None:
        # Try prefix match
        prefix = sys_locale.split('_')[0]
        detected = locale_map.get(prefix, 'en')
    i18n.set('locale', detected)
    return detected

def t(key, **kwargs):
    """Shortcut for i18n.t()."""
    return i18n.t(key, **kwargs)


# ─────────────────────────────────────────────
#  Worker Threads
# ─────────────────────────────────────────────

class LoadAlbumWorker(QThread):
    """Background thread: load album metadata."""
    finished = pyqtSignal(object, list)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, album_id: str):
        super().__init__()
        self.album_id = album_id

    def run(self):
        try:
            self.progress.emit(t('status.connecting'))
            ost = khinsider.Soundtrack(self.album_id)

            self.progress.emit(t('status.parsing'))
            _ = ost.name
            _ = ost.availableFormats
            _ = ost.songs

            self.progress.emit(t('status.extracting'))
            song_names = []
            table = ost._contentSoup.find('table', id='songlist')
            rows = [tr for tr in table('tr') if not tr.find('th')]
            for tr in rows:
                a = tr.find('a')
                song_names.append(a.get_text(strip=True) if a else '???')

            self.finished.emit(ost, song_names)
        except khinsider.NonexistentSoundtrackError:
            self.error.emit(t('status.load_failed',
                              msg=f'Album "{self.album_id}" not found.'))
        except Exception as e:
            self.error.emit(t('status.load_failed', msg=str(e)))


class DownloadWorker(QThread):
    """Background thread: download selected songs."""
    progress = pyqtSignal(int, int, str)
    songDone = pyqtSignal(int, bool)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, songs, format_order, out_dir):
        super().__init__()
        self.songs = songs
        self.format_order = format_order
        self.out_dir = out_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        import requests as req
        total = len(self.songs)
        succeeded = 0
        failed = 0

        os.makedirs(self.out_dir, exist_ok=True)

        for i, (row, song) in enumerate(self.songs, 1):
            if self._cancelled:
                break

            try:
                file = khinsider.getAppropriateFile(song, self.format_order)
            except khinsider.NonexistentSongError:
                self.songDone.emit(row, False)
                failed += 1
                continue

            if file is None:
                self.songDone.emit(row, False)
                failed += 1
                continue

            filename = khinsider.to_valid_filename(file.filename)
            self.progress.emit(i, total, filename)
            filepath = os.path.join(self.out_dir, filename)

            if os.path.exists(filepath):
                self.songDone.emit(row, True)
                succeeded += 1
                continue

            ok = False
            for attempt in range(3):
                if self._cancelled:
                    break
                try:
                    file.download(filepath)
                    ok = True
                    break
                except (req.ConnectionError, req.Timeout):
                    pass

            if ok:
                succeeded += 1
            else:
                failed += 1
            self.songDone.emit(row, ok)

        self.finished.emit(succeeded, failed)


# ─────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(QSize(720, 520))
        self.resize(820, 600)

        self._soundtrack = None
        self._load_worker = None
        self._dl_worker = None

        self._build_ui()
        self._apply_locale()

    # ── UI Construction ────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # --- Language selector row ---
        lay_lang = QHBoxLayout()
        lay_lang.addStretch()
        self.lbl_lang = QLabel()
        lay_lang.addWidget(self.lbl_lang)
        self.cmb_lang = QComboBox()
        self.cmb_lang.setFixedWidth(140)
        for code, name in SUPPORTED_LOCALES:
            self.cmb_lang.addItem(f'{name} ({code})', code)
        self.cmb_lang.currentIndexChanged.connect(self._on_lang_changed)
        lay_lang.addWidget(self.cmb_lang)
        root.addLayout(lay_lang)

        # --- Album input row ---
        self.grp_album = QGroupBox()
        lay_album = QHBoxLayout(self.grp_album)
        self.txt_url = QLineEdit()
        self.txt_url.returnPressed.connect(self._on_load)
        self.btn_load = QPushButton()
        self.btn_load.setFixedWidth(80)
        self.btn_load.clicked.connect(self._on_load)
        lay_album.addWidget(self.txt_url)
        lay_album.addWidget(self.btn_load)
        root.addWidget(self.grp_album)

        # --- Options row ---
        lay_opts = QHBoxLayout()
        self.lbl_format = QLabel()
        lay_opts.addWidget(self.lbl_format)
        self.cmb_format = QComboBox()
        self.cmb_format.setFixedWidth(100)
        lay_opts.addWidget(self.cmb_format)
        lay_opts.addSpacing(16)
        self.lbl_outdir = QLabel()
        lay_opts.addWidget(self.lbl_outdir)
        self.txt_dir = QLineEdit()
        lay_opts.addWidget(self.txt_dir)
        self.btn_browse = QPushButton()
        self.btn_browse.setFixedWidth(80)
        self.btn_browse.clicked.connect(self._on_browse)
        lay_opts.addWidget(self.btn_browse)
        root.addLayout(lay_opts)

        # --- Song table ---
        self.tbl = QTableWidget(0, 4)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setColumnWidth(0, 32)
        self.tbl.verticalHeader().setDefaultSectionSize(26)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        root.addWidget(self.tbl)

        # --- Select buttons ---
        lay_sel = QHBoxLayout()
        self.btn_sel_all = QPushButton()
        self.btn_sel_all.clicked.connect(lambda: self._set_all_checked(True))
        self.btn_sel_none = QPushButton()
        self.btn_sel_none.clicked.connect(lambda: self._set_all_checked(False))
        self.lbl_count = QLabel('')
        lay_sel.addWidget(self.btn_sel_all)
        lay_sel.addWidget(self.btn_sel_none)
        lay_sel.addStretch()
        lay_sel.addWidget(self.lbl_count)
        root.addLayout(lay_sel)

        # --- Progress ---
        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)

        # --- Download / Cancel ---
        lay_dl = QHBoxLayout()
        lay_dl.addStretch()
        self.btn_download = QPushButton()
        self.btn_download.setFixedWidth(120)
        self.btn_download.setEnabled(False)
        self.btn_download.clicked.connect(self._on_download)
        self.btn_cancel = QPushButton()
        self.btn_cancel.setFixedWidth(80)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel)
        lay_dl.addWidget(self.btn_download)
        lay_dl.addWidget(self.btn_cancel)
        root.addLayout(lay_dl)

        self.statusBar()

    # ── i18n ───────────────────────────────

    def _apply_locale(self):
        """Refresh all UI text from the current i18n locale."""
        # Sync combo box
        current_locale = i18n.get('locale')
        for idx in range(self.cmb_lang.count()):
            if self.cmb_lang.itemData(idx) == current_locale:
                self.cmb_lang.blockSignals(True)
                self.cmb_lang.setCurrentIndex(idx)
                self.cmb_lang.blockSignals(False)
                break

        self.setWindowTitle(t('app.title'))
        self.lbl_lang.setText(t('language.label'))
        self.grp_album.setTitle(t('album.group_title'))
        self.txt_url.setPlaceholderText(t('album.url_placeholder'))
        self.btn_load.setText(t('album.load'))
        self.lbl_format.setText(t('options.format'))
        self.lbl_outdir.setText(t('options.output_dir'))
        self.txt_dir.setPlaceholderText(t('options.output_placeholder'))
        self.btn_browse.setText(t('options.browse'))
        self.tbl.setHorizontalHeaderLabels(
            ['', t('table.track'), t('table.size'), t('table.status')])
        self.btn_sel_all.setText(t('selection.select_all'))
        self.btn_sel_none.setText(t('selection.deselect_all'))
        self.btn_download.setText(t('download.download_selected'))
        self.btn_cancel.setText(t('download.cancel'))
        self.statusBar().showMessage(t('status.ready'))

    def _on_lang_changed(self, index):
        code = self.cmb_lang.itemData(index)
        if code:
            i18n.set('locale', code)
            self._apply_locale()

    # ── Helpers ────────────────────────────

    @staticmethod
    def _parse_album_id(text: str) -> str:
        text = text.strip()
        m = re.match(
            r'https?://downloads\.khinsider\.com/game-soundtracks/album/([^/]+)/?',
            text, re.IGNORECASE
        )
        return m.group(1) if m else text

    def _set_all_checked(self, checked: bool):
        for row in range(self.tbl.rowCount()):
            cb = self.tbl.cellWidget(row, 0)
            if cb:
                cb.setChecked(checked)

    def _checked_rows(self):
        rows = []
        for row in range(self.tbl.rowCount()):
            cb = self.tbl.cellWidget(row, 0)
            if cb and cb.isChecked():
                rows.append(row)
        return rows

    def _set_ui_busy(self, busy: bool, downloading=False):
        self.btn_load.setEnabled(not busy)
        self.txt_url.setEnabled(not busy)
        self.cmb_lang.setEnabled(not busy)
        self.btn_download.setEnabled(not busy and self._soundtrack is not None)
        self.btn_cancel.setEnabled(busy and downloading)

    # ── Load Album ─────────────────────────

    def _on_load(self):
        album_id = self._parse_album_id(self.txt_url.text())
        if not album_id:
            return

        self._set_ui_busy(True)
        self.statusBar().showMessage(t('status.loading', album_id=album_id))
        self.tbl.setRowCount(0)
        self.cmb_format.clear()
        self.progress.setMaximum(0)
        self.progress.setValue(0)
        self._soundtrack = None

        self._load_worker = LoadAlbumWorker(album_id)
        self._load_worker.progress.connect(self._on_load_progress)
        self._load_worker.finished.connect(self._on_album_loaded)
        self._load_worker.error.connect(self._on_album_error)
        self._load_worker.start()

    @pyqtSlot(str)
    def _on_load_progress(self, msg):
        self.statusBar().showMessage(msg)

    @pyqtSlot(object, list)
    def _on_album_loaded(self, ost, song_names):
        self._soundtrack = ost
        self.progress.setMaximum(1)
        self.progress.setValue(0)

        for fmt in ost.availableFormats:
            self.cmb_format.addItem(fmt.upper(), fmt)

        songs = ost.songs
        self.tbl.setRowCount(len(songs))
        for i in range(len(songs)):
            cb = QCheckBox()
            cb.setChecked(True)
            self.tbl.setCellWidget(i, 0, cb)

            name = song_names[i] if i < len(song_names) else '???'
            self.tbl.setItem(i, 1, QTableWidgetItem(name))
            self.tbl.setItem(i, 2, QTableWidgetItem('\u2014'))
            self.tbl.setItem(i, 3, QTableWidgetItem(''))

        self.lbl_count.setText(t('selection.count', count=len(songs)))
        self.statusBar().showMessage(
            t('status.loaded',
              name=ost.name,
              count=len(songs),
              formats=', '.join(ost.availableFormats)))
        self._set_ui_busy(False)

    @pyqtSlot(str)
    def _on_album_error(self, msg):
        self.progress.setMaximum(1)
        self.progress.setValue(0)
        self.statusBar().showMessage(msg)
        QMessageBox.warning(self, t('dialog.load_failed_title'), msg)
        self._set_ui_busy(False)

    # ── Browse Directory ───────────────────

    def _on_browse(self):
        d = QFileDialog.getExistingDirectory(
            self, t('dialog.choose_output_dir'))
        if d:
            self.txt_dir.setText(d)

    # ── Download ───────────────────────────

    def _on_download(self):
        if not self._soundtrack:
            return

        rows = self._checked_rows()
        if not rows:
            QMessageBox.information(
                self, t('dialog.hint_title'),
                t('dialog.select_at_least_one'))
            return

        out_dir = self.txt_dir.text().strip()
        if not out_dir:
            out_dir = khinsider.to_valid_filename(self._soundtrack.name)

        fmt = self.cmb_format.currentData()
        format_order = [fmt] if fmt else None

        song_pairs = [(r, self._soundtrack.songs[r]) for r in rows]

        for r in rows:
            self.tbl.item(r, 3).setText(t('status.waiting'))

        self.progress.setMaximum(len(song_pairs))
        self.progress.setValue(0)

        self._set_ui_busy(True, downloading=True)
        self.statusBar().showMessage(t('status.downloading'))

        self._dl_worker = DownloadWorker(song_pairs, format_order, out_dir)
        self._dl_worker.progress.connect(self._on_dl_progress)
        self._dl_worker.songDone.connect(self._on_dl_song_done)
        self._dl_worker.finished.connect(self._on_dl_finished)
        self._dl_worker.start()

    @pyqtSlot(int, int, str)
    def _on_dl_progress(self, current, total, filename):
        self.progress.setValue(current - 1)
        self.statusBar().showMessage(
            t('status.dl_progress',
              current=current, total=total, filename=filename))

    @pyqtSlot(int, bool)
    def _on_dl_song_done(self, row, success):
        item = self.tbl.item(row, 3)
        if item:
            item.setText(t('status.done') if success else t('status.failed'))
        self.progress.setValue(self.progress.value() + 1)

    @pyqtSlot(int, int)
    def _on_dl_finished(self, succeeded, failed):
        if failed:
            msg = t('status.dl_done_with_fail',
                    succeeded=succeeded, failed=failed)
        else:
            msg = t('status.dl_done', succeeded=succeeded)
        self.statusBar().showMessage(msg)
        QMessageBox.information(self, t('dialog.complete_title'), msg)
        self._set_ui_busy(False)

    # ── Cancel ─────────────────────────────

    def _on_cancel(self):
        if self._dl_worker:
            self._dl_worker.cancel()
            self.statusBar().showMessage(t('status.cancelling'))


# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────

def main():
    setup_i18n()
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()