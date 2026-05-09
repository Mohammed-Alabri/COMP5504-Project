import datetime

from PyQt6.QtCore import pyqtSlot, Qt, QTimer, QRectF
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QSizePolicy, QStatusBar, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from .websocket_thread import WebSocketThread
from protocol import (
    MSG_AUCTION_CREATED, MSG_AUCTION_LIST, MSG_BID, MSG_CLOSED,
    MSG_CREATE_AUCTION, MSG_ERROR, MSG_JOIN, MSG_LIST_AUCTIONS,
    MSG_REJECTED, MSG_UPDATE,
)

SERVER_URL = "ws://localhost:8765"

APP_STYLE = """
QWidget {
    background-color: #f0f4f8;
    color: #0f172a;
    font-size: 13px;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QMainWindow { background-color: #e8edf3; }

QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    margin-top: 12px;
    padding: 6px 10px 6px 10px;
    font-weight: bold;
    font-size: 11px;
    color: #94a3b8;
    letter-spacing: 1px;
    text-transform: uppercase;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    background-color: #ffffff;
}

QLineEdit {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px 11px;
    color: #0f172a;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QLineEdit:focus { border: 1.5px solid #2563eb; }
QLineEdit:disabled { background-color: #f8fafc; color: #94a3b8; }

QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: bold;
    min-width: 80px;
}
QPushButton:hover   { background-color: #1d4ed8; }
QPushButton:pressed { background-color: #1e40af; }
QPushButton:disabled { background-color: #e2e8f0; color: #94a3b8; }

QPushButton#CreateBtn { background-color: #059669; }
QPushButton#CreateBtn:hover { background-color: #047857; }

QPushButton#JoinBtn {
    background-color: #0891b2;
    padding: 4px 12px;
    min-width: 55px;
    font-size: 12px;
}
QPushButton#JoinBtn:hover { background-color: #0e7490; }

QPushButton#BidBtn { background-color: #7c3aed; min-width: 110px; }
QPushButton#BidBtn:hover { background-color: #6d28d9; }
QPushButton#BidBtn:disabled { background-color: #e2e8f0; color: #94a3b8; }

QPushButton#QuickBtn {
    background-color: #f1f5f9;
    color: #1e40af;
    border: 1.5px solid #bfdbfe;
    border-radius: 6px;
    padding: 5px 10px;
    font-weight: bold;
    min-width: 50px;
    font-size: 12px;
}
QPushButton#QuickBtn:hover   { background-color: #dbeafe; border-color: #2563eb; }
QPushButton#QuickBtn:pressed { background-color: #bfdbfe; }
QPushButton#QuickBtn:disabled { background-color: #f8fafc; color: #94a3b8; border-color: #e2e8f0; }

QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
}
QTableWidget::item { padding: 6px 10px; border: none; }
QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    border: none;
    border-right: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
    padding: 8px 10px;
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 1px;
}

QTextEdit {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    color: #334155;
    padding: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}

QStatusBar {
    background-color: #e8edf3;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    font-size: 12px;
}

QDialog { background-color: #ffffff; }
QDialogButtonBox QPushButton { min-width: 75px; }

QScrollBar:vertical {
    background-color: #f1f5f9;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

QLabel#AuctionTitle {
    font-size: 16px;
    font-weight: bold;
    color: #1e293b;
}
QLabel#BidLabel {
    font-size: 13px;
    color: #059669;
    font-weight: bold;
}
"""


# ---------------------------------------------------------------------------
# Circular countdown timer widget
# ---------------------------------------------------------------------------

class CircularTimer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value   = 0
        self._maximum = 1
        self._text    = "--:--"
        self.setFixedSize(120, 120)

    def set_time(self, time_left: int, maximum: int) -> None:
        self._value   = max(time_left, 0)
        self._maximum = max(maximum, 1)
        mins, secs    = divmod(self._value, 60)
        self._text    = f"{mins:02d}:{secs:02d}"
        self.update()

    def reset(self) -> None:
        self._value   = 0
        self._maximum = 1
        self._text    = "--:--"
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen_w  = 10
        margin = pen_w // 2 + 3
        size   = min(self.width(), self.height()) - 2 * margin
        x      = (self.width()  - size) / 2
        y      = (self.height() - size) / 2
        rect   = QRectF(x, y, size, size)

        # Background ring
        painter.setPen(
            QPen(QColor("#e2e8f0"), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        painter.drawEllipse(rect)

        # Remaining-time arc (clockwise from 12 o'clock)
        ratio = self._value / self._maximum
        span  = int(ratio * 360 * 16)
        if ratio > 0.5:
            arc_color = QColor("#059669")   # green
        elif ratio > 0.2:
            arc_color = QColor("#d97706")   # amber
        else:
            arc_color = QColor("#dc2626")   # red

        painter.setPen(
            QPen(arc_color, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        painter.drawArc(rect, 90 * 16, -span)

        # Center label
        painter.setPen(QPen(QColor("#0f172a")))
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._text)

        painter.end()


# ---------------------------------------------------------------------------
# Create Auction dialog
# ---------------------------------------------------------------------------

class CreateAuctionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Auction")
        self.setMinimumWidth(340)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("New Auction")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e40af; padding-bottom: 2px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._item_input  = QLineEdit()
        self._item_input.setPlaceholderText("e.g. MacBook Pro 2023")
        self._price_input = QLineEdit()
        self._price_input.setPlaceholderText("e.g. 100.00")
        self._dur_input   = QLineEdit()
        self._dur_input.setPlaceholderText("e.g. 60")

        form.addRow("Item Name:", self._item_input)
        form.addRow("Start Price (OMR):", self._price_input)
        form.addRow("Duration (sec):", self._dur_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        """Returns (item_name, start_price, duration) or None if any input is invalid."""
        item_name = self._item_input.text().strip()
        if not item_name:
            return None
        try:
            start_price = float(self._price_input.text().strip())
            if start_price < 0:
                return None
        except ValueError:
            return None
        try:
            duration = int(self._dur_input.text().strip())
            if duration <= 0:
                return None
        except ValueError:
            return None
        return item_name, start_price, duration


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Distributed Auction Platform — COMP5504")
        self.setMinimumSize(780, 720)
        self.resize(860, 920)

        self._ws_thread: WebSocketThread    = None
        self._current_auction_id: int       = None
        self._current_auction_duration: int = 1
        self._last_shown_bid: float         = -1.0
        self._current_highest_bid: float    = 0.0

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(5000)
        self._refresh_timer.timeout.connect(self._auto_refresh)

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 10, 14, 6)
        root.setSpacing(8)

        root.addWidget(self._build_connection_bar())
        root.addWidget(self._build_auction_list_panel(), stretch=2)
        root.addWidget(self._build_detail_panel())
        root.addWidget(self._build_bid_panel())
        root.addWidget(self._build_history_panel(), stretch=1)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Not connected")

    def _build_connection_bar(self) -> QGroupBox:
        group = QGroupBox("Connection")
        layout = QHBoxLayout(group)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Username:"))
        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("Enter your name")
        self._username_input.setMaximumWidth(220)
        layout.addWidget(self._username_input)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setMinimumWidth(100)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self._connect_btn)
        layout.addStretch()
        return group

    def _build_auction_list_panel(self) -> QGroupBox:
        group = QGroupBox("Active Auctions")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.addStretch()
        self._create_btn = QPushButton("+ Create Auction")
        self._create_btn.setObjectName("CreateBtn")
        self._create_btn.setEnabled(False)
        self._create_btn.clicked.connect(self._on_create_clicked)
        top.addWidget(self._create_btn)
        layout.addLayout(top)

        self._auction_table = QTableWidget(0, 4)
        self._auction_table.setHorizontalHeaderLabels(["Item", "Highest Bid", "Time Left", ""])
        hh = self._auction_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._auction_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._auction_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._auction_table.verticalHeader().setVisible(False)
        self._auction_table.setAlternatingRowColors(True)
        self._auction_table.setMinimumHeight(140)
        self._auction_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._auction_table, stretch=1)
        return group

    def _build_detail_panel(self) -> QGroupBox:
        group = QGroupBox("Current Auction")
        outer = QHBoxLayout(group)
        outer.setSpacing(16)

        # Left: text info
        info = QVBoxLayout()
        info.setSpacing(6)

        self._auction_title_lbl = QLabel("No auction selected")
        self._auction_title_lbl.setObjectName("AuctionTitle")
        self._auction_title_lbl.setWordWrap(True)
        info.addWidget(self._auction_title_lbl)

        self._highest_bid_lbl = QLabel("Highest Bid: —")
        self._highest_bid_lbl.setObjectName("BidLabel")
        info.addWidget(self._highest_bid_lbl)
        info.addStretch()

        outer.addLayout(info, stretch=1)

        # Right: circular countdown
        self._circular_timer = CircularTimer()
        outer.addWidget(self._circular_timer, alignment=Qt.AlignmentFlag.AlignVCenter)
        return group

    def _build_bid_panel(self) -> QGroupBox:
        group = QGroupBox("Place a Bid")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Row 1: amount input + place bid button
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        input_row.addWidget(QLabel("Amount (OMR):"))
        self._bid_input = QLineEdit()
        self._bid_input.setPlaceholderText("Enter bid amount")
        self._bid_input.setMaximumWidth(180)
        self._bid_input.returnPressed.connect(self._on_bid_clicked)
        input_row.addWidget(self._bid_input)
        self._bid_btn = QPushButton("Place Bid")
        self._bid_btn.setObjectName("BidBtn")
        self._bid_btn.setEnabled(False)
        self._bid_btn.clicked.connect(self._on_bid_clicked)
        input_row.addWidget(self._bid_btn)
        input_row.addStretch()
        layout.addLayout(input_row)

        # Row 2: quick bid buttons
        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        lbl = QLabel("Quick bid:")
        lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        quick_row.addWidget(lbl)

        self._quick_btns: list = []
        for increment in [10, 50, 100, 500]:
            btn = QPushButton(f"+{increment} OMR")
            btn.setObjectName("QuickBtn")
            btn.setEnabled(False)
            btn.clicked.connect(lambda _, inc=increment: self._on_quick_bid(inc))
            quick_row.addWidget(btn)
            self._quick_btns.append(btn)

        quick_row.addStretch()
        layout.addLayout(quick_row)
        return group

    def _build_history_panel(self) -> QGroupBox:
        group = QGroupBox("Bid History")
        layout = QVBoxLayout(group)
        self._history = QTextEdit()
        self._history.setReadOnly(True)
        self._history.setMinimumHeight(80)
        layout.addWidget(self._history)
        return group

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _on_connect_clicked(self) -> None:
        username = self._username_input.text().strip()
        if not username:
            self._status_bar.showMessage("Enter a username before connecting.")
            return
        if self._ws_thread and self._ws_thread.isRunning():
            self._ws_thread.stop()
        self._ws_thread = WebSocketThread(SERVER_URL)
        self._ws_thread.message_received.connect(self._on_message_received)
        self._ws_thread.connection_status.connect(self._on_connection_status)
        self._ws_thread.start()

    def _on_disconnect_clicked(self) -> None:
        self._refresh_timer.stop()
        if self._ws_thread:
            self._ws_thread.stop()
            self._ws_thread = None

    @pyqtSlot(bool)
    def _on_connection_status(self, connected: bool) -> None:
        if connected:
            self._connect_btn.setText("Disconnect")
            self._connect_btn.clicked.disconnect()
            self._connect_btn.clicked.connect(self._on_disconnect_clicked)
            self._create_btn.setEnabled(True)
            self._username_input.setEnabled(False)
            self._status_bar.showMessage("Connected to ws://localhost:8765")
            self._refresh_timer.start()
            self._ws_thread.send_message({"type": MSG_LIST_AUCTIONS})
        else:
            self._connect_btn.setText("Connect")
            self._connect_btn.clicked.disconnect()
            self._connect_btn.clicked.connect(self._on_connect_clicked)
            self._create_btn.setEnabled(False)
            self._bid_btn.setEnabled(False)
            for btn in self._quick_btns:
                btn.setEnabled(False)
            self._username_input.setEnabled(True)
            self._refresh_timer.stop()
            self._current_auction_id = None
            self._status_bar.showMessage("Disconnected")

    def _auto_refresh(self) -> None:
        if self._ws_thread and self._ws_thread.isRunning():
            self._ws_thread.send_message({"type": MSG_LIST_AUCTIONS})

    # ------------------------------------------------------------------
    # Message dispatch
    # ------------------------------------------------------------------

    @pyqtSlot(dict)
    def _on_message_received(self, msg: dict) -> None:
        handlers = {
            MSG_AUCTION_LIST:    self._handle_auction_list,
            MSG_UPDATE:          self._handle_update,
            MSG_REJECTED:        self._handle_rejected,
            MSG_CLOSED:          self._handle_closed,
            MSG_ERROR:           self._handle_error,
            MSG_AUCTION_CREATED: self._handle_auction_created,
        }
        handler = handlers.get(msg.get("type"))
        if handler:
            handler(msg)

    def _handle_auction_list(self, msg: dict) -> None:
        self._auction_table.setRowCount(0)
        for auction in msg.get("auctions", []):
            row = self._auction_table.rowCount()
            self._auction_table.insertRow(row)

            item_cell = QTableWidgetItem(auction.get("item_name", ""))
            item_cell.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self._auction_table.setItem(row, 0, item_cell)

            bid_cell = QTableWidgetItem(f"OMR {auction.get('highest_bid', 0):.2f}")
            bid_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bid_cell.setForeground(QBrush(QColor("#059669")))
            self._auction_table.setItem(row, 1, bid_cell)

            status    = auction.get("status", "active")
            time_left = auction.get("time_left", 0)
            time_cell = QTableWidgetItem(f"{time_left}s" if status == "active" else "Closed")
            time_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if status != "active":
                time_cell.setForeground(QBrush(QColor("#94a3b8")))
            self._auction_table.setItem(row, 2, time_cell)

            aid      = auction.get("auction_id")
            duration = auction.get("duration", max(time_left, 1))
            if status == "active":
                join_btn = QPushButton("Join")
                join_btn.setObjectName("JoinBtn")
                join_btn.clicked.connect(lambda _, a=aid, d=duration: self._on_join_clicked(a, d))
                self._auction_table.setCellWidget(row, 3, join_btn)
            else:
                done_cell = QTableWidgetItem("Closed")
                done_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                done_cell.setForeground(QBrush(QColor("#94a3b8")))
                self._auction_table.setItem(row, 3, done_cell)

        self._auction_table.resizeRowsToContents()

    def _handle_update(self, msg: dict) -> None:
        if msg.get("auction_id") != self._current_auction_id:
            return

        highest_bid    = msg.get("highest_bid", 0)
        highest_bidder = msg.get("highest_bidder")
        time_left      = msg.get("time_left", 0)
        item           = msg.get("item", "")

        self._current_highest_bid = highest_bid

        self._auction_title_lbl.setText(item)
        self._highest_bid_lbl.setText(
            f"OMR {highest_bid:.2f}" + (f"  —  {highest_bidder}" if highest_bidder else "  (no bids yet)")
        )
        self._circular_timer.set_time(time_left, self._current_auction_duration)

        # Append to history only when the bid amount increases
        if highest_bid > self._last_shown_bid:
            self._last_shown_bid = highest_bid
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            if highest_bidder:
                entry = (
                    f'<font color="#94a3b8">[{ts}]</font> '
                    f'<font color="#1e40af">{highest_bidder}</font> '
                    f'<font color="#64748b">bid</font> '
                    f'<font color="#059669"><b>OMR {highest_bid:.2f}</b></font>'
                )
            else:
                entry = (
                    f'<font color="#94a3b8">[{ts}]</font> '
                    f'<font color="#64748b">Starting price: </font>'
                    f'<font color="#059669">OMR {highest_bid:.2f}</font>'
                )
            self._history.append(entry)

    def _handle_closed(self, msg: dict) -> None:
        aid         = msg.get("auction_id")
        winner      = msg.get("winner")
        final_price = msg.get("final_price", 0)
        item        = msg.get("item", "Auction")

        if self._ws_thread and self._ws_thread.isRunning():
            self._ws_thread.send_message({"type": MSG_LIST_AUCTIONS})

        if aid != self._current_auction_id:
            return

        self._auction_title_lbl.setText(f"{item}  [CLOSED]")
        self._circular_timer.set_time(0, 1)
        self._bid_btn.setEnabled(False)
        for btn in self._quick_btns:
            btn.setEnabled(False)

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        if winner:
            self._highest_bid_lbl.setText(f"Winner: {winner}  @  OMR {final_price:.2f}")
            close_html = (
                f'<font color="#94a3b8">[{ts}]</font> '
                f'<font color="#d97706"><b>Auction closed</b></font> '
                f'<font color="#64748b">— Winner: </font>'
                f'<font color="#1e40af"><b>{winner}</b></font> '
                f'<font color="#059669">@ OMR {final_price:.2f}</font>'
            )
        else:
            self._highest_bid_lbl.setText("No winner")
            close_html = (
                f'<font color="#94a3b8">[{ts}]</font> '
                f'<font color="#94a3b8">Auction closed — no winner</font>'
            )
        self._history.append(close_html)

        username = self._username_input.text().strip()
        if winner and winner == username:
            QMessageBox.information(
                self, "You Won!",
                f"Congratulations!\n\nYou won '{item}' for OMR {final_price:.2f}.",
            )
        elif winner:
            QMessageBox.information(
                self, "Auction Closed",
                f"'{item}' was won by {winner} for OMR {final_price:.2f}.",
            )
        else:
            QMessageBox.information(
                self, "Auction Closed",
                f"'{item}' ended with no winner.",
            )

    def _handle_rejected(self, msg: dict) -> None:
        self._status_bar.showMessage(f"Bid rejected: {msg.get('reason', 'amount too low')}")

    def _handle_error(self, msg: dict) -> None:
        self._status_bar.showMessage(f"Server error: {msg.get('message', '')}")

    def _handle_auction_created(self, msg: dict) -> None:
        self._status_bar.showMessage(
            f"Auction created: #{msg.get('auction_id')} — {msg.get('item_name')}"
        )
        if self._ws_thread and self._ws_thread.isRunning():
            self._ws_thread.send_message({"type": MSG_LIST_AUCTIONS})

    # ------------------------------------------------------------------
    # User actions
    # ------------------------------------------------------------------

    def _on_join_clicked(self, auction_id: int, duration: int) -> None:
        if not (self._ws_thread and self._ws_thread.isRunning()):
            return
        self._current_auction_id       = auction_id
        self._current_auction_duration = max(duration, 1)
        self._last_shown_bid           = -1.0
        self._current_highest_bid      = 0.0
        self._history.clear()
        self._circular_timer.reset()
        self._bid_btn.setEnabled(True)
        for btn in self._quick_btns:
            btn.setEnabled(True)
        username = self._username_input.text().strip()
        self._ws_thread.send_message({
            "type":       MSG_JOIN,
            "auction_id": auction_id,
            "user":       username,
        })
        self._status_bar.showMessage(f"Joined auction #{auction_id}")

    def _on_quick_bid(self, increment: float) -> None:
        new_amount = self._current_highest_bid + increment
        self._bid_input.setText(f"{new_amount:.2f}")
        self._bid_input.setFocus()

    def _on_bid_clicked(self) -> None:
        if not (self._ws_thread and self._ws_thread.isRunning()):
            return
        if self._current_auction_id is None:
            self._status_bar.showMessage("Join an auction first.")
            return
        bid_text = self._bid_input.text().strip()
        try:
            amount = float(bid_text)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self._status_bar.showMessage("Enter a valid positive bid amount.")
            return
        username = self._username_input.text().strip()
        self._ws_thread.send_message({
            "type":       MSG_BID,
            "auction_id": self._current_auction_id,
            "user":       username,
            "amount":     amount,
        })
        self._bid_input.clear()

    def _on_create_clicked(self) -> None:
        if not (self._ws_thread and self._ws_thread.isRunning()):
            return
        dlg = CreateAuctionDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        values = dlg.get_values()
        if values is None:
            self._status_bar.showMessage("Invalid auction details — check your inputs.")
            return
        item_name, start_price, duration = values
        username = self._username_input.text().strip()
        self._ws_thread.send_message({
            "type":        MSG_CREATE_AUCTION,
            "item_name":   item_name,
            "start_price": start_price,
            "duration":    duration,
            "user":        username,
        })

    def closeEvent(self, event) -> None:
        self._refresh_timer.stop()
        if self._ws_thread and self._ws_thread.isRunning():
            self._ws_thread.stop()
        event.accept()
