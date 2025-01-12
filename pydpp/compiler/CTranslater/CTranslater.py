from ._const import *
from ._Function import _Function
from ._subBlock import _subBlock
from ._WhileLoop import _WhileLoop
from ._ConditionalInstr import _ConditionalInstr
from ._Cursor import _Cursor

"""
This class is what encapsulate the whole CTranslater mechanic. 

It handles the C generated file.

It defines all the C functions that can be written in the generated file. 
A list of all the accepted functions is accessible in self.instr.

It handles the construction and run steps.

See the paper at the root of the project for full details about how it works.
"""

# To use CTranslater, preferably put it in a "with" statement.
class CTranslater:

    #################################
    # Internal functions
    #################################
    def __init__(self, filename):
        self.filename = filename
        try:
            self.file = open(self.filename, "w")
        except IOError as err:
            raise IOError(f"Error opening file '{self.filename}': {err}")
        self.closed = False

        self._header() #Function that writes the start of the C generated file.
        self.conditionalFuncCpt = 0 #The actual number of conditionalFunc (used for their id)
        self.main = _subBlock() #The subBlock that store and run the whole user-program.
                                # /!\ Can contains other subBlocks(via loop, conditional instr...)

        self._tmpInstr = {} #user-defined functions
        self._tmpCmpt = 0 #The actual number of user-defined function (used for their id)

        # self.instr is a dict that bind the name of a function, with a ref of that funtion.
        # Note that subBlocks store this references.
        self.instr = {
            "and": self._and,
            "or": self._or,
            "greaterThan": self._greaterThan,
            "greaterThanOrEquals": self._greaterThanOrEquals,
            "lowerThan": self._lowerThan,
            "lowerThanOrEquals": self._lowerThanOrEquals,
            "equals": self._equals,
            "notEquals": self._notEquals,
            "isNot": self._isNot,
            "add": self._add,
            "subtract": self._subtract,
            "multiply": self._multiply,
            "divide": self._divide,
            "storeReturnedValueFromFuncInVar": self._storeReturnedValueFromFuncInVar,
            "createVar": self._createVar, #also works for assignation
            "assignateValueToVar": self._createVar,
            "addToVar": self._addToVar,
            "drawCircle": self._drawCircle,
            "drawCircleFill": self._drawCircleFill,
            "drawRect": self._drawRect,
            "drawRectFill": self._drawRectFill,
            "setColor": self._setColor,
            "deb": self._deb,
            "sleep": self._sleep,
            "functReturnStatement": self._functReturnStatement,
            "createCursor": self._createCursor,
            "cursorJump": self._cursorJump,
            "cursorDrawCircle": self._cursorDrawCircle,
            "cursorDrawFilledCircle": self._cursorDrawFilledCircle,
            "cursorDrawFilledRectangle": self._cursorDrawFilledRectangle,
            "cursorDrawRectangle": self._cursorDrawRectangle,
            "cursorDrawLine": self._cursorDrawLine,
            "cursorDrawPixel": self._cursorDrawPixel,
            "cursorRotate": self._cursorRotate,
            "_cursorPrintData": self._cursorPrintData,
            "cursorChangeColor": self._cursorChangeColor,
            "cursorChangeThickness": self._cursorChangeThickness,
        }


        #This variable is a stack of scope, used for construction step.
        #it allows to go back to the parents of an element when the user ended a block with .endBlock.
        #Also useful to see if a function declaration is made in the main, and not in an function.
        self.constructionStack = ["main"]


        # Width and height of the canvas. And yes, this is where the default values reside.
        self.canvas_width = 1200
        self.canvas_height = 640

    def _header(self):
        self.file.write(header)

    def close(self):
        if not self.closed:
            self.file.write(footer)
            self.file.close()
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __del__(self):
        self.close()


    #Return the actual stack and handles the Mechanic of self.constructionStack
    def _getActualStackFrame(self):
        if len(self.constructionStack) == 0:
            #happens if the user ended the main func(so the prog)
            print("Error")
            #TODO: Handle error

        frame = self.constructionStack[-1]
        match frame:

            case "main":
                return self.main

            case frame if frame.startswith("#"):
                if frame in self._tmpInstr:
                    return self._tmpInstr[frame]
                else:
                    print("Error")
                    #todo: HAndle error

            case _:
                if frame in self.instr:
                    return self.instr[frame]
                else:
                    print("Unknown stack")
                    #TODO: Handle error

    ####################################
    # Interface functions
    # The followings functions are the functions that user can use with the CTranslater. (CTranslater.createFunc() for ex)
    ####################################

    def add_instruction(self, instructionName, *args) -> None:
        #TODO: check args ? Not necessary as it is done before, but still a security
        if instructionName not in self.instr:
            print("Unknown instruction ", instructionName)
            #todo: handle error

        frame = self._getActualStackFrame()
        frame.add_instruction(self.instr[instructionName], *args)

    def configure_canvas(self, w, h):
        """
        Configures the width and height of the canvas.
        """
        assert w > 0 and h > 0
        self.canvas_width = w
        self.canvas_height = h

    def createFunc(self, functionName: str, args) -> None:

        #TODO: Handle Error
        if self._getActualStackFrame() != self.main:
            print("cannot create a function inside a function, loop or conditional instruction.")
            return

        if functionName.startswith("#"):
            print("Function cannot start with #")
            return

        if functionName in self.instr:
            print("Function already exists")
            return

        newFunction = _Function(functionName, args)
        self.instr[functionName] = newFunction

        self.constructionStack.append(functionName)

    def createWhileLoop(self) -> None:

        newWhileLoop = _WhileLoop(self._tmpCmpt)
        self._tmpCmpt += 1

        frame = self._getActualStackFrame()
        frame.add_instruction(newWhileLoop)

        #TODO: verif
        if frame.__class__.__name__ == "_subBlock":
            self._tmpInstr[newWhileLoop.__name__] = frame.instr[-1][0]
        elif frame.__class__.__name__ == "_WhileLoop":
            self._tmpInstr[newWhileLoop.__name__] = frame.getActualSubBlock().instr[-1][0]
        else:
            self._tmpInstr[newWhileLoop.__name__] = frame.subBlock.instr[-1][0]

        self.constructionStack.append(newWhileLoop.__name__)

    def createConditionalInstr(self) -> None:
        newConditionalInstr = _ConditionalInstr(self._tmpCmpt)
        self._tmpCmpt += 1

        frame = self._getActualStackFrame()
        frame.add_instruction(newConditionalInstr)

        #TODO: verif
        if frame.__class__.__name__ == "_subBlock":
            self._tmpInstr[newConditionalInstr.__name__] = frame.instr[-1][0]
        elif frame.__class__.__name__ == "_WhileLoop":
            self._tmpInstr[newConditionalInstr.__name__] = frame.getActualSubBlock().instr[-1][0]
        else:
            self._tmpInstr[newConditionalInstr.__name__] = frame.getActualSubBlock().instr[-1][0]

        self.constructionStack.append(newConditionalInstr.__name__)

    def endBlock(self):
        frame = self._getActualStackFrame()

        if frame == self.main:
            print("Cannot end main function.")
            return

        frame.nextStep()

        if frame.isFinished():
            self.constructionStack.pop()

    def run(self):
        # First begin the canvas with the width/height dimensions.
        self.file.write(f"beginCanvas(renderer, {self.canvas_width}, {self.canvas_height}, &drawCanvas);\n");

        scope = {}
        scope, returnedValue = self.main(scope)


    """
    ##############################
    # The following functions are the implementations
    # of the drawpp functions
    # See self.instr to have the complete list
    # They should NEVER be called from outside the class
    ##############################
    """
    #####################################
    #  Variable related functions (Defined in _subBlock to respect scope)
    ######################################
    def _functReturnStatement(self, var):
        pass

    def _storeReturnedValueFromFuncInVar(self, varName: str) -> None:
        pass

    def _createVar(self, name: str, value) -> None:
        pass
        #self.varDict[name] = value

    def _addToVar(self, name, value) -> None:
        pass

    def _createCursor(self, name, x, y, angle, r, g, b, a):
        pass

    def _cursorJump(self, cursor, x, y):
        pass # TODO: Study the bug.
        #assert isinstance(cursor, _Cursor)
        #cursor.x, cursor.y = cursor.x + x, cursor.y + y

    def _cursorDrawCircle(self, cursor, r):
        assert isinstance(cursor, _Cursor)
        self._setColor(cursor.color[0], cursor.color[1], cursor.color[2], cursor.color[3])
        self._drawCircle(cursor.x, cursor.y, r, cursor.thickness)

    def _cursorDrawFilledCircle(self, cursor, r):
        assert isinstance(cursor, _Cursor)
        self._setColor(cursor.color[0], cursor.color[1], cursor.color[2], cursor.color[3])
        self._drawCircleFill(cursor.x, cursor.y, r)

    def _cursorDrawFilledRectangle(self, cursor, width, height):
        assert isinstance(cursor, _Cursor)
        self._setColor(cursor.color[0], cursor.color[1], cursor.color[2], cursor.color[3])
        self._drawRectFill(cursor.x, cursor.y, width, height, cursor.angle)

    def _cursorDrawRectangle(self, cursor, width, height):
        assert isinstance(cursor, _Cursor)
        self._setColor(cursor.color[0], cursor.color[1], cursor.color[2], cursor.color[3])
        self._drawRect(cursor.x, cursor.y, width, height, cursor.angle, cursor.thickness)

    def _cursorDrawLine(self, cursor, x, y):
        assert isinstance(cursor, _Cursor)
        self._setColor(cursor.color[0], cursor.color[1], cursor.color[2], cursor.color[3])
        self._drawLine(cursor.x, cursor.y, x, y, cursor.thickness)

    def _cursorDrawPixel(self, cursor):
        assert isinstance(cursor, _Cursor)
        self._setColor(cursor.color[0], cursor.color[1], cursor.color[2], cursor.color[3])
        self._drawPixel(cursor.x, cursor.y)

    def _cursorRotate(self, cursor, angle):
        assert isinstance(cursor, _Cursor)
        cursor.angle = angle

    def _cursorPrintData(self, cursor):
        pass

    def _cursorChangeThickness(self, cursor, thickness):
        assert isinstance(cursor, _Cursor)
        cursor.thickness = thickness

    def _cursorChangeColor(self, cursor, r, g, b, a):
        assert isinstance(cursor, _Cursor)
        cursor.color = [r, g, b, a]

    #########################
    # Logic & operation functions
    #########################

    def _greaterThan(self, a, b) -> bool:
        return a > b

    def _greaterThanOrEquals(self, a, b) -> bool:
        return a >= b

    def _lowerThan(self, a, b) -> bool:
        return a < b

    def _lowerThanOrEquals(self, a, b) -> bool:
        return a <= b

    def _equals(self, a, b) -> bool:
        return a == b

    def _notEquals(self, a, b) -> bool:
        return a != b

    def _isNot(self, a: bool) -> bool:
        return not a
    def _and(self, a, b) -> bool:
        return a and b

    def _or(self, a, b) -> bool:
        return a or b

    #########################
    # Arithmetic functions
    #########################
    def _add(self, a, b):
        return a + b

    def _subtract(self, a, b):
        return a - b

    def _multiply(self, a, b):
        return a * b

    def _divide(self, a, b):
        # Make sure that we do integer division when both operands are integers.
        if type(a) == int and type(b) == int:
            return a // b
        else:
            return a / b

    ##############################################
    #Draw functions
    ###############################################
    def _drawCircle(self, x, y, radius, thickness=1):
        #TODO: add type verif for parameters x,y,radius (and range ? yes for radius)
        self.file.write("drawCircleOutline(renderer, " + str(x) + ", " + str(y) + ", " + str(radius) + ", " + str(thickness) + ");\n")

    def _drawCircleFill(self, x, y, radius):
        #TODO: add type verif for parameters x,y,radius (and range ? yes for radius)
        self.file.write("drawCircleFill(renderer, " + str(x) + ", " + str(y) + ", " + str(radius) + ");\n")

    def _drawRect(self, x, y, width, height, angle, thickness):
        #TODO: add type verif for parameters x,y,width,height (and range ? probably not)
        self.file.write(
            f"drawRectangleOutline(renderer, {str(x)}, {str(y)}, {str(width)}, {str(height)}, {str(angle)}, {str(thickness)});\n")

    def _drawRectFill(self, x, y, width, height, angle):
        self.file.write(f"drawRectangleFill(renderer, {x}, {y}, {width}, {height}, {angle});\n")

    def _drawLine(self, x1, y1, x2, y2, thickness):
        self.file.write(f"drawThickLine(renderer, {x1}, {y1}, {x2}, {y2}, {thickness});\n")

    def _drawPixel(self, x, y):
        self.file.write(f"drawPixel(renderer, {x}, {y});\n")

    def _setColor(self, r, g, b, a):

        # Check that RGB values are in the range [0, 255]
        if not (0 <= r <= 255):
            print(f"Error: Red value must be between 0 and 255. Received: {r}")
            return  # Return early if red value is out of range
        if not (0 <= g <= 255):
            print(f"Error: Green value must be between 0 and 255. Received: {g}")
            return  # Return early if green value is out of range
        if not (0 <= b <= 255):
            print(f"Error: Blue value must be between 0 and 255. Received: {b}")
            return  # Return early if blue value is out of range

        # Check that alpha value is in the range [0, 255]
        if not (0 <= a <= 255):
            print(f"Error: Alpha value must be between 0 and 255. Received: {a}")
            return  # Return early if alpha value is out of range

        self.file.write(
            "SDL_SetRenderDrawColor(renderer, " + str(r) + ", " + str(g) + ", " + str(b) + ", " + str(a) + ");\n")

    ################################
    # Animation
    ################################
    def _sleep(self, milliseconds):
        if not isinstance(milliseconds, int):
            print("milliseconds must be int type")
            return
        self.file.write("SDL_Delay( " + str(milliseconds) + ");\n")

    ######################
    # Debug
    ######################

    def _deb(self, test):
        print(test)
