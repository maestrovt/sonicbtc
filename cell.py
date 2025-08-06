from window import Point, Line
class Cell:
    def __init__(self, win=None):
        self.has_left_wall = True
        self.has_right_wall = True
        self.has_top_wall = True
        self.has_bottom_wall = True
        self.visited = False # track which cells have had their walls broken

        self._x1 = None
        self._x2 = None
        self._y1 = None
        self._y2 = None

        self.__win = win

    def draw(self, x1, y1, x2, y2):
        if self.__win is None:
            return
        self._x1 = x1
        self._x2 = x2
        self._y1 = y1
        self._y2 = y2
        p1 = Point(x1, y1)
        p2 = Point(x1, y2)
        line = Line(p1, p2)
        if self.has_left_wall:
            self.__win.draw_line(line)
        if not self.has_left_wall:
            self.__win.draw_line(line, "white")
        p1 = Point(x2, y1)
        p2 = Point(x2, y2)
        line = Line(p1, p2)
        if self.has_right_wall:
            self.__win.draw_line(line)
        if not self.has_right_wall:
            self.__win.draw_line(line, "white")
        p1 = Point(x1, y1)
        p2 = Point(x2, y1)
        line = Line(p1, p2)
        if self.has_top_wall:
            self.__win.draw_line(line)
        if not self.has_top_wall:
            self.__win.draw_line(line, "white")
        p1 = Point(x1, y2)
        p2 = Point(x2, y2)
        line = Line(p1, p2)
        if self.has_bottom_wall:
            self.__win.draw_line(line)
        if not self.has_bottom_wall:
            self.__win.draw_line(line, "white")

    def draw_move(self, to_cell, undo=False):
        origin_x = self._x1 + int(0.5 * (self._x2 - self._x1))
        origin_y = self._y1 + int(0.5 * (self._y2 - self._y1))
        p1 = Point(origin_x, origin_y)
        destination_x = to_cell._x1 + int(0.5 * (to_cell._x2 - to_cell._x1))
        destination_y = to_cell._y1 + int(0.5 * (to_cell._y2 - to_cell._y1))
        p2 = Point(destination_x, destination_y)
        line = Line(p1, p2)
        if not undo:
            self.__win.draw_line(line, "red")
        else:
            self.__win.draw_line(line, "gray")
