import sys
import typing

from PyQt6 import QtGui
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QGridLayout, QFileDialog
from PyQt6.QtGui import QPixmap, QPainter, QPen
from PyQt6.QtCore import Qt, QPoint, QRect
from PIL.ImageQt import ImageQt
from PIL.PpmImagePlugin import PpmImageFile
from pdf2image import convert_from_path


class PdfToImage:
    """
    Класс преобразует PDF-файл в PNG-изображения и возвращает их в виде последовательности
    с реализованными методами __getitem__ для обращения к элементам по индексу
    и __len__ для получения длины последовательности.
    Каждая страница PDF-файла становится отдельным элементом последовательности (в виде изображения).
    """
    def __init__(self, path_to_pdf: str, dpi: int = 200):
        self.images = convert_from_path(path_to_pdf, dpi)

    def __getitem__(self, item):
        return self.images[item]

    def __len__(self):
        return len(self.images)


class Canvas(QLabel):
    """
    Этот класс отрисовывает холст, на котором будут отображаться элементы последовательности PdfToImage,
    а также обрабатывает нажатия левой клавиши мыши для отрисовки прямоугольника.
    """
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.parent = parent
        self.begin, self.destination = QPoint(), QPoint()
        self.pixmap = QPixmap('welcome.png')

    def reload(self, image: PpmImageFile):
        """
        Перезагружает отображаемое на холсте изображение.
        """
        self.pixmap = QPixmap.fromImage(ImageQt(image))

    def calculate_size_of_page(self,
                               width_page: int | float,
                               height_page: int | float) -> tuple[int, int]:
        """
        Рассчитывает размеры изображения, которые поместятся в текущие размеры окна,
        сохраняя оригинальное соотношение сторон.
        Возвращает кортеж, состоящий из двух целых чисел.
        """
        width_canvas = self.rect().width()
        height_canvas = self.rect().height()

        if width_page <= width_canvas and height_page <= height_canvas:
            return width_page, height_page

        if width_page > height_page:
            ratio = height_page / width_page
            return (
                int(width_canvas),
                int(width_canvas * ratio)
            )
        else:
            ratio = width_page / height_page
            return (
                int(height_canvas * ratio),
                int(height_canvas)
            )

    def calculate_zero_coordinates(self, width: int | float, height: int | float) -> tuple[int, int]:
        """
        Рассчитывает координаты левого верхнего угла для центрирования изображения.
        Если высота изображения больше ширины, то отодвигаем начало вправо.
        Если ширина больше высоты - отодвигаем вниз.
        """
        width_canvas = self.rect().width()
        height_canvas = self.rect().height()
        x, y = 0, 0

        if width <= width_canvas and height <= height_canvas:
            x = abs(int((self.width() / 2) - (width / 2)))
            y = abs(int((self.height() / 2) - (height / 2)))
        elif width < height:
            x = abs(int((self.width() / 2) - (width / 2)))
        else:
            y = abs(int((self.height() / 2) - (height / 2)))

        return x, y

    def paintEvent(self, event: typing.Optional[QtGui.QPaintEvent]) -> None:
        """
        Отрисовывает изображение по центру окна, уменьшая размер до размеров окна,
        сохраняя при этом оригинальное соотношение сторон,
        а также отрисовывает прямоугольник, который нарисовал на изображении пользователь.
        """
        painter = QPainter(self)
        painter.setPen(QPen(Qt.GlobalColor.red, 3, Qt.PenStyle.SolidLine))

        width_image, height_image = self.calculate_size_of_page(self.pixmap.width(), self.pixmap.height())
        x, y = self.calculate_zero_coordinates(width_image, height_image)

        painter.drawPixmap(x, y, width_image, height_image, self.pixmap)

        if not self.begin.isNull() and not self.destination.isNull():
            rect = QRect(self.begin, self.destination)
            painter.drawRect(rect.normalized())

    def mousePressEvent(self, event: QtGui.QMouseEvent | None) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.begin = event.pos()
            self.destination = self.begin
            self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent | None) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.destination = event.pos()
            self.update()

    def mouseRleaseEvent(self, event: QtGui.QMouseEvent | None) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            rect = QRect(self.begin, self.destination)
            painter = QPainter(self.pixmap)
            painter.drawRect(rect.normalized())

            self.begin, self.destination = QPoint(), QPoint()
            self.update()


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.pdf = None
        self.filename: str = ''
        self.current_page: int = 0
        self.begin, self.destination = QPoint(), QPoint()

        self.setWindowTitle('PDF reader from Egor Vavilov')
        self.setMinimumSize(700, 800)

        layout = QGridLayout()

        button_select_file = QPushButton('Выбрать файл')
        button_select_file.clicked.connect(self.select_file)
        layout.addWidget(button_select_file, 0, 0)

        self.label_pages = QLabel('0 / 0')
        self.label_pages.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.label_pages, 0, 1)

        self.button_prev_page = QPushButton('<- Назад')
        self.button_prev_page.setEnabled(False)
        self.button_prev_page.clicked.connect(self.display_prev_page)
        layout.addWidget(self.button_prev_page, 0, 2)

        self.button_next_page = QPushButton('Дальше ->')
        self.button_next_page.setEnabled(False)
        self.button_next_page.clicked.connect(self.display_next_page)
        layout.addWidget(self.button_next_page, 0, 3)

        self.canvas = Canvas(self)
        layout.addWidget(self.canvas, 1, 0, 1, 4)

        self.setLayout(layout)

    def select_file(self):
        filename, ok = QFileDialog.getOpenFileName(
            self,
            'Выберите PDF-файл',
            '~',
            '(*.pdf *.PDF)'
        )
        if filename:
            self.filename = filename
            self.current_page = 0
            self.read_pdf(self.filename)
            self.display_page(0)

    def display_next_page(self):
        self.current_page += 1
        self.display_page(self.current_page)

        self.button_prev_page.setEnabled(True)
        self.button_next_page.setEnabled(self.current_page != (len(self.pdf) - 1))

    def display_prev_page(self):
        self.current_page -= 1
        self.display_page(self.current_page)

        self.button_prev_page.setEnabled(self.current_page != 0)
        self.button_next_page.setEnabled(True)

    def read_pdf(self, path: str) -> None:
        """
        Читает PDF-файл и сохраняет его в аттрибуте класса self.pdf постранично.
        """
        self.pdf = PdfToImage(path)
        self.update()

    def display_page(self, page: int = 0) -> None:
        """
        Отображает страницу с номером `page` в окне приложения.
        """
        self.canvas.reload(self.pdf[page])

        self.button_next_page.setEnabled(True)
        self.label_pages.setText(f'{self.current_page + 1} / {len(self.pdf)}')
        self.update()


if __name__ == '__main__':
    app = QApplication([])
    window = Window()
    window.show()
    sys.exit(app.exec())
