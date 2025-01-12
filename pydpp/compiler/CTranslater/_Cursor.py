"""
This class represent the cursor. It acts as a structure.

Note: the writing variable is not used yet.
"""

class _Cursor:

    def __init__(self, name, x, y, angle=0.0, r=255, g=255, b=255, a=1):
        self.name = name
        self.x = x
        self.y = y
        self.angle = angle
        self.thickness = 1
        self.writing = True

        self.color = [r, g, b, a]
