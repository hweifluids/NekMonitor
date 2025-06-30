import sys
import os
import re
import time
import matplotlib
# Increase overall font sizes
matplotlib.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10
})
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
)
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class NekMonitor(QWidget):
    """
    A PyQt5 GUI application that monitors a Nek5000 log file (./logfile) and plots five metrics.
    Two indicators at top: `Update` (green) for new data and `Jam` (red) for delayed updates.
    Each subplot's x-axis toggles between 'Step' and 'Solution Time' by clicking its x-axis label.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nek5000 Monitor")
        self.log_path = os.path.join(os.path.dirname(__file__), "logfile")
        self.poll_interval_ms = 1000

        try:
            self.last_file_mod = os.path.getmtime(self.log_path)
        except OSError:
            self.last_file_mod = 0
        self.last_update_time = time.time()

        self.steps = []
        self.times = []
        self.dts = []
        self.cfls = []
        self.total_times = []
        self.step_times = []
        self.x_modes = ['step'] * 5

        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(self.poll_interval_ms)

    def init_ui(self):
        main_layout = QVBoxLayout()
        # Indicator layout with minimal margins and spacing, left-aligned
        ind_layout = QHBoxLayout()
        ind_layout.setContentsMargins(0, 0, 0, 0)
        ind_layout.setSpacing(5)
        # Update indicator
        update_label = QLabel('Update')
        ind_layout.addWidget(update_label)
        self.update_led = QFrame()
        self.update_led.setFixedSize(16, 16)
        self.update_led.setStyleSheet('background-color: gray; border:1px solid black; border-radius:8px;')
        ind_layout.addWidget(self.update_led)
        # Jam indicator
        jam_label = QLabel('Jam')
        ind_layout.addWidget(jam_label)
        self.delay_led = QFrame()
        self.delay_led.setFixedSize(16, 16)
        self.delay_led.setStyleSheet('background-color: gray; border:1px solid black; border-radius:8px;')
        ind_layout.addWidget(self.delay_led)
        # Force left alignment
        ind_layout.addStretch()
        main_layout.addLayout(ind_layout)

        # Canvas setup
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)

        # Create 5 subplots
        self.axes = [
            self.figure.add_subplot(231),
            self.figure.add_subplot(232),
            self.figure.add_subplot(233),
            self.figure.add_subplot(234),
            self.figure.add_subplot(235)
        ]
        self.label_texts = []
        self.colors = ['#FF6F61', '#6B5B95', '#88B04B', '#F7CAC9', '#92A8D1']
        self.canvas.mpl_connect('pick_event', self.on_label_click)

        self.figure.tight_layout()
        self.setLayout(main_layout)

    def on_label_click(self, event):
        if event.artist in self.label_texts:
            idx = self.label_texts.index(event.artist)
            self.x_modes[idx] = 'time' if self.x_modes[idx]=='step' else 'step'
            self.update_plots()

    def parse_log(self):
        steps, times, dts, cfls, total_times, step_times = [],[],[],[],[],[]
        pattern = re.compile(r"Step\s+(\d+),\s*t=\s*([0-9E\+\-\.]+),\s*DT=\s*([0-9E\+\-\.]+),\s*C=\s*([0-9E\+\-\.]+)\s*([0-9E\+\-\.]+)\s*([0-9E\+\-\.]+)")
        try:
            with open(self.log_path) as f:
                for line in f:
                    m = pattern.search(line)
                    if m:
                        steps.append(int(m.group(1)))
                        times.append(float(m.group(2)))
                        dts.append(float(m.group(3)))
                        cfls.append(float(m.group(4)))
                        total_times.append(float(m.group(5)))
                        step_times.append(float(m.group(6)))
        except FileNotFoundError:
            pass
        return steps, times, dts, cfls, total_times, step_times

    def update_data(self):
        try:
            mod = os.path.getmtime(self.log_path)
        except OSError:
            mod = 0
        if mod > self.last_file_mod:
            self.flash_led(self.update_led, 'green')
            self.last_file_mod = mod
        now = time.time()
        elapsed = now - self.last_update_time
        if elapsed > (self.poll_interval_ms/1000.) * 1.1:
            self.flash_led(self.delay_led, 'red')
        self.last_update_time = now

        self.steps, self.times, self.dts, self.cfls, self.total_times, self.step_times = self.parse_log()
        self.update_plots()

    def flash_led(self, led, color):
        led.setStyleSheet(f'background-color: {color}; border:1px solid black; border-radius:8px;')
        QTimer.singleShot(50, lambda: led.setStyleSheet('background-color: gray; border:1px solid black; border-radius:8px;'))

    def update_plots(self):
        self.label_texts.clear()
        titles = ['Solution Time vs Step','Time Step (DT)','CFL','Total Wall Time','Step Wall Time']
        ylabels = ['Solution Time','DT','CFL','Total Wall Time','Step Wall Time']
        data_sets = [self.times, self.dts, self.cfls, self.total_times, self.step_times]

        for i, ax in enumerate(self.axes):
            ax.clear()
            mode = self.x_modes[i]
            if i==0:
                if mode=='step': x,y=self.steps,self.times; xl,yl='Step','Solution Time'
                else: x,y=self.times,self.steps; xl,yl='Solution Time','Step'
            else:
                ydata = data_sets[i]
                if mode=='step': x,y=self.steps,ydata; xl='Step'
                else: x,y=self.times,ydata; xl='Solution Time'
                yl=ylabels[i]
            ax.plot(x,y,linestyle='-',color=self.colors[i])
            ax.grid(True, linestyle='-', linewidth=0.5, alpha=0.3)
            ax.set_title(titles[i])
            lbl = ax.set_xlabel(xl, picker=True)
            ax.set_ylabel(yl)
            self.label_texts.append(lbl)
        self.figure.tight_layout()
        self.canvas.draw()

if __name__=='__main__':
    app=QApplication(sys.argv)
    monitor=NekMonitor()
    monitor.show()
    sys.exit(app.exec_())
