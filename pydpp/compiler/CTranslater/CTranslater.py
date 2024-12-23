from ._const import *
from ._Function import _Function
from ._subBlock import _subBlock
from ._WhileLoop import _WhileLoop
from ._ConditionalInstr import _ConditionalInstr
from ._Cursor import _Cursor


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

        self._header()
        self.conditionalFuncCpt = 0
        self.main = _subBlock()
        self._tmpInstr = {}
        self._tmpCmpt = 0
        self.instr = {
            "and": self._and,
            "or": self._or,
            "greaterThan": self._greaterThan,
            "greaterThanOrEquals": self._greaterThanOrEquals,
            "lowerThan": self._lowerThan,
            "lowerThanOrEquals": self._lowerThanOrEquals,
            "equals": self._equals,
            "isNot": self._isNot,
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
            "cursorRotate": self._cursorRotate,
            "_cursorPrintData": self._cursorPrintData,
            "cursorChangeColor": self._cursorChangeColor,
            "cursorChangeThickness": self._cursorChangeThickness,
        }
        self.constructionStack = ["main"]

    def _header(self):
        self.file.write(header)

    def __del__(self):
        self.file.write(footer)
        self.file.close()

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
    ####################################

    def add_instruction(self, instructionName, *args) -> None:
        #TODO: check args
        if instructionName not in self.instr:
            print("Unknown instruction ", instructionName)
            #todo: handle error

        frame = self._getActualStackFrame()
        frame.add_instruction(self.instr[instructionName], *args)

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
            self._tmpInstr[newConditionalInstr.__name__] = frame.subBlock.instr[-1][0]

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

    def _cursorJump(self, circle, x, y):
        self._drawRect(circle.x, circle.y, circle.x+x, circle.y+y)

    def _cursorDrawCircle(self, circle, r):
        self._setColor(circle.color[0], circle.color[1], circle.color[2], circle.color[3])
        self._drawCircle(circle.x, circle.y, r)

    def _cursorDrawFilledCircle(self, circle, r):
        self._setColor(circle.color[0], circle.color[1], circle.color[2], circle.color[3])
        self._drawCircleFill(circle.x, circle.y, r)

    def _cursorRotate(self, cursor, angle):
        pass

    def _cursorPrintData(self, cursor):
        pass

    def _cursorChangeThickness(self, cursor, thickness):
        pass

    def _cursorChangeColor(self, cursor, r, g, b, a):
        pass

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

    def _isNot(self, a: bool) -> bool:
        return not a
    def _and(self, a, b) -> bool:
        return a and b

    def _or(self, a, b) -> bool:
        return a or b


    ##############################################
    #Draw functions
    ###############################################
    def _drawCircle(self, x, y, radius):
        #TODO: add type verif for parameters x,y,radius (and range ? yes for radius)
        self.file.write("drawCircle(renderer, " + str(x) + ", " + str(y) + ", " + str(radius) + ");\n")

    def _drawCircleFill(self, x, y, radius):
        #TODO: add type verif for parameters x,y,radius (and range ? yes for radius)
        self.file.write("drawCircleFill(renderer, " + str(x) + ", " + str(y) + ", " + str(radius) + ");\n")

    def _drawRect(self, x, y, width, height):
        #TODO: add type verif for parameters x,y,width,height (and range ? probably not)
        self.file.write(
            "drawRect(renderer, " + str(x) + ", " + str(y) + ", " + str(width) + ", " + str(height) + ");\n")

    def _drawRectFill(self, x, y, width, height):
        #TODO: add type verif for parameters x,y,width,height (and range ? probably not)
        self.file.write(
            "drawRectFill(renderer, " + str(x) + ", " + str(y) + ", " + str(width) + ", " + str(height) + ");\n")

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

        # Check that alpha value is in the range [0, 1]
        if not (0 <= a <= 1):
            print(f"Error: Alpha value must be between 0 and 1. Received: {a}")
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
