from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout, QSizePolicy

class FlowLayout(QLayout):
    """
    A custom layout that arranges widgets horizontally and wraps them 
    to the next line when they run out of space, similar to web text rendering.
    """
    def __init__(self, parent=None, margin=0, hSpacing=5, vSpacing=5):
        super().__init__(parent)
        self._item_list = []
        self._h_spacing = hSpacing
        self._v_spacing = vSpacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self._h_spacing

        for item in self._item_list:
            style = item.widget().style() if item.widget() else None
            layout_spacing_x = spacing
            layout_spacing_y = self._v_spacing

            next_x = x + item.sizeHint().width() + layout_spacing_x
            if next_x - layout_spacing_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + layout_spacing_y
                next_x = x + item.sizeHint().width() + layout_spacing_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()
