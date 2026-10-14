# ui/bench_dialog.py
"""
llama-bench sweep dialog.

llama-bench measures raw prompt processing (pp) and generation (tg) throughput without the
HTTP server, and accepts several values per option (comma lists, 'first-last+step' ranges),
running the full cartesian product. This dialog pre-fills those options from the selected
model, runs the sweep, shows a sortable result table and can push the fastest settings back
into the editor.
"""

import json
import os

from PyQt6.QtCore import QProcess, pyqtSignal, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QTextEdit, QComboBox, QSpinBox, QSplitter,
                             QHeaderView, QMessageBox)

from Llamacpp_Model_launcher.core import benchmark_history
from .styles import PARAMETER_BROWSER_STYLES

# (llama-bench flag, label, server flag aliases used to pre-fill, tooltip)
BENCH_FIELDS = [
    ('-p', 'Prompt tokens (-p)', (), 'Prompt length for the pp test. Comma list, e.g. 512,2048'),
    ('-n', 'Generated tokens (-n)', (), 'Tokens generated for the tg test, e.g. 128'),
    ('-d', 'Context depth (-d)', (), 'Run the tests after this many tokens are already in the KV cache.\n'
                                     'e.g. 0,16384,65536 shows how speed drops with long contexts.'),
    ('-ngl', 'GPU layers (-ngl)', ('-ngl', '--gpu-layers', '--n-gpu-layers'), 'e.g. 99, or a range 20-40+5'),
    ('-sm', 'Split mode (-sm)', ('-sm', '--split-mode'), 'layer,tensor,row,none - "layer,tensor" compares both'),
    ('-ts', 'Tensor split (-ts)', ('-ts', '--tensor-split'), 'Per-GPU proportions separated by "/", e.g. 1/1 or 3/2'),
    ('-dev', 'Devices (-dev)', ('-dev', '--device'), 'Devices separated by "/", e.g. CUDA0/CUDA1'),
    ('-mg', 'Main GPU (-mg)', ('-mg', '--main-gpu'), ''),
    ('-fa', 'Flash attention (-fa)', ('-fa', '--flash-attn'), 'on,off,auto'),
    ('-ctk', 'KV type K (-ctk)', ('-ctk', '--cache-type-k'), 'e.g. f16,q8_0'),
    ('-ctv', 'KV type V (-ctv)', ('-ctv', '--cache-type-v'), 'e.g. f16,q8_0'),
    ('-b', 'Batch (-b)', ('-b', '--batch-size'), 'e.g. 2048'),
    ('-ub', 'Micro-batch (-ub)', ('-ub', '--ubatch-size'), 'e.g. 256,512,1024,2048'),
    ('-t', 'Threads (-t)', ('-t', '--threads'), 'Only matters with CPU offload, e.g. 6,10'),
    ('-ncmoe', 'MoE layers on CPU (-ncmoe)', ('-ncmoe', '--n-cpu-moe'), 'e.g. 0-20+4'),
    ('-lm', 'Load mode (-lm)', ('-lm', '--load-mode'), 'auto, none, mmap, dio...'),
    ('-ot', 'Override tensor (-ot)', ('-ot', '--override-tensor'), 'Overrides separated by ";"'),
]

# llama-bench JSON field -> (server flag, converter)
_JSON_TO_SERVER = {
    'n_gpu_layers': ('-ngl', str),
    'split_mode': ('-sm', str),
    'n_batch': ('-b', str),
    'n_ubatch': ('-ub', str),
    'type_k': ('-ctk', str),
    'type_v': ('-ctv', str),
    'n_threads': ('-t', str),
    'n_cpu_moe': ('-ncmoe', str),
    'tensor_split': ('-ts', lambda v: str(v).replace('/', ',')),
    'flash_attn': ('-fa', lambda v: {1: 'on', 0: 'off', -1: 'auto', True: 'on', False: 'off'}.get(v, str(v))),
    'main_gpu': ('-mg', str),
}

_NON_CONFIG_FIELDS = {'build_commit', 'build_number', 'cpu_info', 'gpu_info', 'backends', 'model_filename',
                      'model_type', 'model_size', 'model_n_params', 'n_prompt', 'n_gen', 'n_depth', 'test_time',
                      'avg_ns', 'stddev_ns', 'avg_ts', 'stddev_ts', 'samples_ns', 'samples_ts'}


class BenchDialog(QDialog):
    """Runs llama-bench sweeps for the current model."""
    apply_params = pyqtSignal(dict)

    def __init__(self, bench_path, model_params, model_name, parent=None):
        super().__init__(parent)
        self.bench_path = bench_path
        self.model_params = model_params
        self.model_name = model_name
        self.process = None
        self.records = []
        self._stdout_buffer = ''
        self.setWindowTitle(f'llama-bench Sweep - {model_name}')
        self.resize(1250, 820)
        self._setup_ui()
        self._prefill()

    # ------------------------------------------------------------------ UI
    def _setup_ui(self):
        self.setStyleSheet(PARAMETER_BROWSER_STYLES["main_bg"])
        layout = QVBoxLayout(self)

        intro = QLabel(
            "Measures raw speed without the server. Every field accepts several values separated by commas "
            "(or ranges like <b>20-40+5</b>) and llama-bench tests every combination. "
            "<b>pp</b> = prompt processing t/s, <b>tg</b> = generation t/s. "
            "Speculative decoding (MTP/draft) is not measured here - use the Tuning Wizard sweep for that.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #C0C0C0;")
        layout.addWidget(intro)

        model_path = self.model_params.get('-m', self.model_params.get('--model', ''))
        path_label = QLabel(f"<b>Model:</b> {model_path}<br><b>llama-bench:</b> {self.bench_path}")
        path_label.setStyleSheet("color: #A0A0A0; font-size: 9pt;")
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(path_label)

        grid = QGridLayout()
        self.inputs = {}
        for idx, (flag, label, _, tooltip) in enumerate(BENCH_FIELDS):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #D1D1D1;")
            edit = QLineEdit()
            edit.setStyleSheet(PARAMETER_BROWSER_STYLES["line_edit"])
            edit.setFont(QFont('Menlo', 9))
            if tooltip:
                edit.setToolTip(tooltip)
                lbl.setToolTip(tooltip)
            row, col = divmod(idx, 3)
            grid.addWidget(lbl, row, col * 2)
            grid.addWidget(edit, row, col * 2 + 1)
            self.inputs[flag] = edit
        layout.addLayout(grid)

        controls = QHBoxLayout()
        reps_label = QLabel("Repetitions (-r):")
        reps_label.setStyleSheet("color: #D1D1D1;")
        self.reps_spin = QSpinBox()
        self.reps_spin.setRange(1, 20)
        self.reps_spin.setValue(3)
        self.best_combo = QComboBox()
        self.best_combo.addItem("Best by generation (tg)", 'tg')
        self.best_combo.addItem("Best by prompt processing (pp)", 'pp')
        self.best_combo.setStyleSheet(PARAMETER_BROWSER_STYLES["combo_box"])
        self.prefill_button = QPushButton("Reset from Model")
        self.prefill_button.clicked.connect(self._prefill)
        self.preset_button = QPushButton("Preset: Find Fastest GPU Settings")
        self.preset_button.setToolTip("Fills a sensible sweep: split mode, micro-batch and flash attention.")
        self.preset_button.clicked.connect(self._apply_speed_preset)
        self.run_button = QPushButton("Run Benchmark")
        self.run_button.setStyleSheet(PARAMETER_BROWSER_STYLES["add_button"])
        self.run_button.clicked.connect(self._run)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop)
        self.apply_button = QPushButton("Apply Best to Editor")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self._apply_best)
        for w in (reps_label, self.reps_spin, self.prefill_button, self.preset_button):
            controls.addWidget(w)
        controls.addStretch()
        for w in (self.best_combo, self.run_button, self.stop_button, self.apply_button):
            controls.addWidget(w)
        layout.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, 0)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("QTableWidget { background-color: #252930; color: #E0E0E0; gridline-color: #40454E; }"
                                 "QHeaderView::section { background-color: #3C424C; color: #E0E0E0; padding: 4px; }")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont('Menlo', 9))
        splitter.addWidget(self.table)
        splitter.addWidget(self.log_view)
        splitter.setSizes([480, 180])
        layout.addWidget(splitter, 1)

        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: #A0A0A0;")
        layout.addWidget(self.status_label)

    # ------------------------------------------------------------------ prefill
    def _model_value(self, aliases):
        for alias in aliases:
            if alias in self.model_params and self.model_params[alias] is not None:
                return str(self.model_params[alias])
        return ''

    def _prefill(self):
        defaults = {'-p': '512', '-n': '128', '-d': '0'}
        for flag, _, aliases, _ in BENCH_FIELDS:
            value = defaults.get(flag, self._model_value(aliases))
            if flag == '-ngl':
                value = {'all': '99', 'auto': ''}.get(value, value)
            elif flag in ('-ts', '-dev'):
                value = value.replace(',', '/')  # llama-bench separates per-GPU values with '/'
            elif flag == '-ot':
                value = value.replace(',', ';')
            self.inputs[flag].setText(value)

    def _apply_speed_preset(self):
        self._prefill()
        multi_gpu = '/' in self.inputs['-ts'].text() or '/' in self.inputs['-dev'].text()
        if multi_gpu:
            self.inputs['-sm'].setText('layer,tensor')
        self.inputs['-ub'].setText('512,1024,2048')
        self.inputs['-fa'].setText('on')
        self.inputs['-p'].setText('2048')
        self.inputs['-n'].setText('128')

    # ------------------------------------------------------------------ run
    def _build_args(self):
        model_path = self.model_params.get('-m', self.model_params.get('--model', ''))
        args = ['-m', model_path, '-o', 'jsonl', '-r', str(self.reps_spin.value()), '--progress']
        for flag, _, _, _ in BENCH_FIELDS:
            value = self.inputs[flag].text().strip()
            if value:
                args += [flag, value]
        return args

    def _run(self):
        if self.process is not None:
            return
        model_path = self.model_params.get('-m', self.model_params.get('--model', ''))
        if not model_path or not os.path.isfile(model_path):
            QMessageBox.warning(self, "llama-bench", f"Model file not found:\n{model_path}")
            return
        args = self._build_args()
        self.records = []
        self._stdout_buffer = ''
        self.table.setRowCount(0)
        self.log_view.clear()
        self.log_view.append(f"> {os.path.basename(self.bench_path)} " + ' '.join(
            f'"{a}"' if ' ' in a else a for a in args) + "\n")
        self.process = QProcess(self)
        self.process.setWorkingDirectory(os.path.dirname(self.bench_path))
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._finished)
        self.process.start(self.bench_path, args)
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.apply_button.setEnabled(False)
        self.status_label.setText("Running... (the model is reloaded for every combination of load-time options)")

    def _stop(self):
        if self.process is not None:
            self.process.kill()

    def _read_stderr(self):
        text = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
        for line in text.splitlines():
            if line.strip():
                self.log_view.append(line)

    def _read_stdout(self):
        self._stdout_buffer += self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
        while '\n' in self._stdout_buffer:
            line, self._stdout_buffer = self._stdout_buffer.split('\n', 1)
            line = line.strip()
            if not line.startswith('{'):
                if line:
                    self.log_view.append(line)
                continue
            try:
                record = json.loads(line)
            except ValueError:
                self.log_view.append(line)
                continue
            self.records.append(record)
            self._record_history(record)
            self._refresh_table()
            self.status_label.setText(f"{len(self.records)} result(s)...")

    def _finished(self, exit_code, _status):
        self._read_stdout()
        self.process = None
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.apply_button.setEnabled(bool(self.records))
        if self.records:
            best = self._best_record()
            self.status_label.setText(
                f"Done: {len(self.records)} result(s). Best: {self._config_text(best)} -> {best['avg_ts']:.2f} t/s"
                if best else f"Done: {len(self.records)} result(s).")
        else:
            self.status_label.setText(f"llama-bench exited with code {exit_code} and no results - see the log below.")

    # ------------------------------------------------------------------ results
    def _varying_fields(self):
        if not self.records:
            return []
        keys = [k for k in self.records[0] if k not in _NON_CONFIG_FIELDS]
        return [k for k in keys if len({json.dumps(r.get(k)) for r in self.records}) > 1]

    @staticmethod
    def _test_name(record):
        name = []
        if record.get('n_prompt'):
            name.append(f"pp{record['n_prompt']}")
        if record.get('n_gen'):
            name.append(f"tg{record['n_gen']}")
        text = '+'.join(name) or 'test'
        if record.get('n_depth'):
            text += f" @ d{record['n_depth']}"
        return text

    def _config_text(self, record):
        fields = self._varying_fields()
        return ', '.join(f"{k}={record.get(k)}" for k in fields) or 'single configuration'

    def _refresh_table(self):
        fields = self._varying_fields()
        headers = ['Test'] + fields + ['t/s', '± stddev']
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.records))
        for row, rec in enumerate(self.records):
            values = [self._test_name(rec)] + [str(rec.get(k)) for k in fields]
            for col, text in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(text))
            for col, number in ((len(values), rec.get('avg_ts', 0.0)), (len(values) + 1, rec.get('stddev_ts', 0.0))):
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, round(float(number), 2))
                self.table.setItem(row, col, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSortingEnabled(True)

    def _best_record(self):
        metric = self.best_combo.currentData()
        pool = [r for r in self.records if (r.get('n_gen') if metric == 'tg' else r.get('n_prompt'))
                and not (r.get('n_gen') and r.get('n_prompt'))]
        return max(pool, key=lambda r: r.get('avg_ts', 0.0)) if pool else None

    def _apply_best(self):
        best = self._best_record()
        if not best:
            QMessageBox.information(self, "llama-bench", "No result matches the selected metric.")
            return
        params = {}
        for field in self._varying_fields():
            if field in _JSON_TO_SERVER:
                flag, convert = _JSON_TO_SERVER[field]
                params[flag] = convert(best[field])
        if not params:
            QMessageBox.information(self, "llama-bench",
                                    "The best result does not change any server option that can be applied.")
            return
        self.apply_params.emit(params)
        QMessageBox.information(self, "llama-bench",
                                "Applied to the editor:\n" + '\n'.join(f"{k} {v}" for k, v in params.items()) +
                                "\n\nPress Save to keep them.")

    def _record_history(self, record):
        benchmark_history.append_record({
            'source': 'llama-bench',
            'label': self._test_name(record),
            'model': self.model_name,
            'build': f"build {record.get('build_number')} ({record.get('build_commit')})",
            'config': {k: record.get(k) for k in record if k not in _NON_CONFIG_FIELDS},
            'pp_tps' if record.get('n_prompt') and not record.get('n_gen') else 'tg_tps': round(record.get('avg_ts', 0.0), 2),
            'n_depth': record.get('n_depth', 0),
        })

    def closeEvent(self, event):
        if self.process is not None:
            self.process.kill()
            self.process.waitForFinished(3000)
        event.accept()
