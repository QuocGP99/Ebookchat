from PySide6.QtWidgets import QAbstractButton
from PySide6.QtGui import QColor, QPainter, QBrush
from PySide6.QtCore import Qt, QPropertyAnimation, Property


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setCheckable(True)
        self.setFixedSize(52, 28)

        # vị trí circle
        self._circle_x = 3

        # animation
        self.anim = QPropertyAnimation(self, b"circleX", self)
        self.anim.setDuration(220)

    # ----------------------
    # property animation
    # ----------------------
    @Property(int)
    def circleX(self):
        return self._circle_x

    @circleX.setter
    def circleX(self, value):
        # tránh recursion
        self.__dict__["_circle_x"] = value
        self.update()

    # ----------------------
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        if self.isChecked():
            self.anim.setStartValue(3)
            self.anim.setEndValue(26)
        else:
            self.anim.setStartValue(26)
            self.anim.setEndValue(3)

        self.anim.start()
        self.toggled.emit(self.isChecked())

    # ----------------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # background
        bg_on = QColor("#2563eb")  # xanh iOS
        bg_off = QColor("#94a3b8")  # xám

        p.setBrush(QBrush(bg_on if self.isChecked() else bg_off))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), 14, 14)

        # circle
        p.setBrush(Qt.white)
        p.drawEllipse(self._circle_x, 3, 22, 22)
