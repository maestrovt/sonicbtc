from cell import Cell
from note import Note
from constants import MAJOR_SCALES
import time
import random

class Maze:
    def __init__(
            self,
            x1,
            y1,
            num_rows,
            num_cols,
            cell_size_x,
            cell_size_y,
            win = None,
            seed = None # Allows for fixed seed to generate repeatable results for testing/debugging
            ):
        self._cells = []
        self._x1 = x1
        self._y1 = y1
        self._num_rows = num_rows
        self._num_cols = num_cols
        self._cell_size_x = cell_size_x
        self._cell_size_y = cell_size_y
        self._win = win
        self._seed = seed
        # Keep track of recursion level for sonification
        self._recursion_level = 0
        # Calculate MIDI pan value increment
        self._column_cc_increment = 128 // self._num_cols
        if seed is not None:
            random.seed(seed)

        self._create_cells()
        self._break_entrance_and_exit()
        self._break_walls_r(0, 0)
        self._reset_cells_visited()

    def _create_cells(self):
        for i in range(self._num_cols):
            col_cells = []
            for j in range(self._num_rows):
                cell = Cell(self._win)  # Instantiate the Cell object
                col_cells.append(cell)  # Add the Cell to the column
            self._cells.append(col_cells)  # Add the column to the matrix
        for i in range(self._num_cols):
            for j in range(self._num_rows):
                self._draw_cell(i, j)

    def _draw_cell(self, i, j):
        if self._win is None:
            return
        x1 = self._x1 + i * self._cell_size_x
        x2 = x1 + self._cell_size_x
        y1 = self._y1 + j * self._cell_size_y
        y2 = y1 + self._cell_size_y
        self._cells[i][j].draw(x1, y1, x2, y2)
        self._animate()

    def _animate(self):
        if self._win is None:
            return
        self._win.redraw()
        time.sleep(0.25)

    def _break_entrance_and_exit(self):
        entrance_cell = self._cells[0][0]
        entrance_cell.has_top_wall = False
        self._draw_cell(0, 0)
        exit_cell = self._cells[self._num_cols - 1][self._num_rows - 1]
        exit_cell.has_bottom_wall = False
        self._draw_cell(self._num_cols - 1, self._num_rows - 1)

    def _break_walls_r(self, i, j):
        current_cell = self._cells[i][j]
        current_cell.visited = True
        while True:
            to_visit = [] # Hold i and j values we will need to visit
            # Check cells directly adjacent to current cell and keep track of which ones have not been visited
            if j + 1 < self._num_rows: # If we are not in the bottom row
                if not self._cells[i][j + 1].visited:
                    to_visit.append((i, j + 1))
            if j - 1 >= 0: # If we are not in the top row
                if not self._cells[i][j - 1].visited:
                    to_visit.append((i, j - 1))
            if i + 1 < self._num_cols: # If we are not in the last column
                if not self._cells[i + 1][j].visited:
                    to_visit.append((i + 1, j))
            if i - 1 >= 0: # If we are not in the first column
                if not self._cells[i - 1][j].visited:
                    to_visit.append((i - 1, j))
            if not to_visit: # If there are no adjacent cells to be visited
                self._draw_cell(i, j) # Draw the current cell
                return # Break out of the loop
            direction = random.randint(0, len(to_visit) - 1) # Pick a random direction
            new_i = to_visit[direction][0] # Get i for that direction
            new_j = to_visit[direction][1] # Get j for that direction

            if new_i == i + 1: # If the new column is to the right
                self._cells[i][j].has_right_wall = False
                self._cells[i + 1][j].has_left_wall = False
            if new_i == i - 1: # If the new column is to the left
                self._cells[i][j].has_left_wall = False
                self._cells[i - 1][j].has_right_wall = False
            if new_j == j + 1: # If the new row is below
                self._cells[i][j].has_bottom_wall = False
                self._cells[i][j + 1].has_top_wall = False
            if new_j == j - 1: # If the new row is above
                self._cells[i][j].has_top_wall = False
                self._cells[i][j - 1].has_bottom_wall = False

            self._break_walls_r(new_i, new_j) # Move to chosen cell by recursively calling _break_walls_r

    def _reset_cells_visited(self): # Method to reset visited property of all cells so it can be reused when solving maze
        for i in range(self._num_cols):
            for j in range(self._num_rows):
                self._cells[i][j].visited = False

    def solve(self): # Just call recursive _solve_r at i=0, j=0
        return self._solve_r(0, 0)
    
    def _solve_r(self, i, j):
        self._animate()
        self._cells[i][j].visited = True
        # If this isn't the entrance cell, increment the recursion level
        if i or j:
            self._recursion_level += 1
        note = Note()
        pitch = 72 - self._recursion_level
        pan = i * self._column_cc_increment
        print(f"i: {i}, j: {j}, Recursion level: {self._recursion_level}, Pitch: {pitch}, Pan = {pan}")
        duration = 0.125
        note.play(pitch, duration, j, pan)
        # If this is the exit cell, we've solved the maze
        if i == self._num_cols - 1 and j == self._num_rows - 1:
            note = Note()
            pitch = 72 - self._recursion_level
            print(f"i: {i}, j: {j}, Recursion level: {self._recursion_level}, Pitch: {pitch}")
            duration = 0.125
            note.play(pitch, duration, j, pan)
            return True
        # left
        if i > 0 and self._cells[i][j].has_left_wall == False and self._cells[i - 1][j].visited == False:
            self._cells[i][j].draw_move(self._cells[i - 1][j])
            test_left = self._solve_r(i - 1, j)
            if test_left:
                self._recursion_level -= 1
                note = Note()
                pitch = 72 - self._recursion_level
                print(f"i: {i}, j: {j}, Recursion level: {self._recursion_level}, Pitch: {pitch}")
                duration = 0.125
                note.play(pitch, duration, j, pan)
                return True
            self._cells[i][j].draw_move(self._cells[i - 1][j], True)
        # right
        if i < self._num_cols - 1 and self._cells[i][j].has_right_wall == False and self._cells[i + 1][j].visited == False:
            self._cells[i][j].draw_move(self._cells[i + 1][j])
            test_right = self._solve_r(i + 1, j)
            if test_right:
                self._recursion_level -= 1
                note = Note()
                pitch = 72 - self._recursion_level
                print(f"i: {i}, j: {j}, Recursion level: {self._recursion_level}, Pitch: {pitch}")
                duration = 0.125
                note.play(pitch, duration, j, pan)
                return True
            self._cells[i][j].draw_move(self._cells[i + 1][j], True)
        # up
        if j > 0 and self._cells[i][j].has_top_wall == False and self._cells[i][j - 1].visited == False:
            self._cells[i][j].draw_move(self._cells[i][j - 1])
            test_up = self._solve_r(i, j - 1)
            if test_up:
                self._recursion_level -= 1
                note = Note()
                pitch = 72 - self._recursion_level
                print(f"i: {i}, j: {j}, Recursion level: {self._recursion_level}, Pitch: {pitch}")
                duration = 0.125
                note.play(pitch, duration, j, pan)
                return True
            self._cells[i][j].draw_move(self._cells[i][j - 1], True)
        # down
        if j < self._num_rows - 1 and self._cells[i][j].has_bottom_wall == False and self._cells[i][j + 1].visited == False:
            self._cells[i][j].draw_move(self._cells[i][j + 1])
            test_down = self._solve_r(i, j + 1)
            if test_down:
                self._recursion_level -= 1
                note = Note()
                pitch = 72 - self._recursion_level
                print(f"i: {i}, j: {j}, Recursion level: {self._recursion_level}, Pitch: {pitch}")
                duration = 0.125
                note.play(pitch, duration, j, pan)
                return True
            self._cells[i][j].draw_move(self._cells[i][j + 1], True)
        self._recursion_level -= 1
        note = Note()
        pitch = 72 - self._recursion_level
        print(f"i: {i}, j: {j}, Recursion level: {self._recursion_level}, Pitch: {pitch}")
        duration = 0.125
        note.play(pitch, duration, j, pan)
        return False

