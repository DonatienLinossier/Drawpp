class _Cursor:

    def __init__(self, name, x, y, angle=0, r=255, g=255, b=255, a=1):
        self.name = name
        self.x = x
        self.y = y
        self.angle = angle
        self.thickness = 1
        self.writing = True

        self.color = [r, g, b, a]
