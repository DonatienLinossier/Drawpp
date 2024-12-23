from .Variable import VarCall
from ._Cursor import _Cursor

"""
This class is designed for executing a sequence of instructions in a controlled scope,
 supporting dynamic function calls, variable manipulations, and conditional logic.
"""


class _subBlock:
    def __init__(self):
        self.instr = []  #Store the instructions of the block
        self.lastReturnedValueFromFunction = None

        # Each Block maintains its own variable dictionary, with the name of the variable used as the key.
        # The varDict will be given at runtime as an argument of the __call__ function.
        # The varDict is returned in order to update the parent varDict
        self.blockVarDict = {}

        # Some functions must be overridden when entering a function.
        # For exemple, variable manipulation within a function should only modify the variable in the function
        self.overrideInstr = {
            "_storeReturnedValueFromFoncInVar": self.storeReturnedValueFromFuncInVar,  #Long.. mais explicite !
            "_getVar": self.functGetVar,
            "_addToVar": self.functAddToVar,
            "_createVar": self.functCreateVar,
            "_createCursor": self.createCursor,
            "_cursorJump": self.cursorJump,
            "_cursorDrawCircle": self.cursorDrawCircle,
            "_cursorDrawFilledCircle": self.cursorDrawFilledCircle,
            "_cursorRotate": self.cursorRotate,
            "_cursorPrintData": self.cursorPrintData,
            "_cursorChangeColor": self.cursorChangeColor,
            "_cursorChangeThickness": self.cursorChangeThickness,
        }

    #It takes:
    #   - The scope
    #It returns:
    #   - the scope(For parent sync if needed),
    #   - If the subBlock ended because of a return statement
    #   - The potential value of the returned value
    def __call__(self, varDict: dict) -> (dict, any):
        #TODO: Verif varDict
        self.blockVarDict = varDict

        for instr in self.instr:

            # Extract function
            func = instr[0]

            #if(isinstance(func, _ConditionalInstr)):
            if func.__class__.__name__ == "_ConditionalInstr" or func.__class__.__name__ == "_WhileLoop":  #Avoid circular Import !!
                self.blockVarDict, returnedValue = func(self.blockVarDict)

                if returnedValue is not None:
                    return self.blockVarDict, returnedValue

            elif func.__class__.__name__ == "_Function" or func.__class__.__name__ == "method":  #Represent function and instr. So basicaly all the others cases.
                arguments = instr[1]
                argumentsFinal = []  #Store the parsed arguments (Use for the varCall)

                for arg in arguments:
                    # Handle variable references
                    if isinstance(arg, VarCall):
                        if arg.name in self.blockVarDict:
                            argumentsFinal.append(self.blockVarDict[arg.name])
                        else:
                            pass
                            print(self.blockVarDict)
                            print("Error: unknown variable")
                            #TODO: HAndle error
                    else:
                        argumentsFinal.append(arg)


                if func.__name__ == "_functReturnStatement":
                    return self.blockVarDict, argumentsFinal[0]
                else:
                    # Call the function with final arguments
                    #print("Calling func :", func.__name__, "with arguments", argumentsFinal)
                    self.lastReturnedValueFromFunction = func(*argumentsFinal)

            else:
                print("Error : unhandled type", func.__class__.__name__, "in subBlock call")

        return self.blockVarDict, None

    def add_instruction(self, func, *args):
        if func.__name__ in self.overrideInstr:

            self.instr.append((self.overrideInstr[func.__name__], args)) #For verif and variable
            self.instr.append((func, args))
        else:
            self.instr.append((func, args))

    def storeReturnedValueFromFuncInVar(self, varName: str) -> None:
        self.functCreateVar(varName, self.lastReturnedValueFromFunction)

    def functCreateVar(self, name: str, value) -> None:
        self.blockVarDict[name] = value

    def functGetVar(self, name: str):
        return self.blockVarDict.get(name, None)  # Return None if variable does not exist

    def functAddToVar(self, name, value):
        if name in self.blockVarDict:
            self.blockVarDict[name] += value
        else:
            print(f"Variable '{name}' does not exist.")

    def createCursor(self, name, x, y, angle, r, g, b, a):
        if name in self.blockVarDict and type(self.blockVarDict[name]) is not _Cursor:
            print("Variable already exists and is not a cursor")
            #TODO: HAndle error
            return
        self.blockVarDict[name] = _Cursor(name, x, y, angle, r, g, b, a)

    def cursorJump(self, cursor, x, y):
        if type(cursor) is not _Cursor:
            #TODO: handle error
            print(cursor, "is not a cursor.")
            return

        cursor.x += x
        cursor.y += y

        self.blockVarDict[cursor.name] = cursor

    def cursorRotate(self, cursor, angle):
        if type(cursor) is not _Cursor:
            #TODO: handle error
            print(cursor, "is not a cursor.")
            return

        cursor.angle += angle

        if cursor.angle >= 360:
            cursor.angle -= 360

        elif cursor.angle <= 0:
            cursor.angle += 360

        self.blockVarDict[cursor.name] = cursor


    def cursorPrintData(self, cursor):
        if type(cursor) is not _Cursor:
            #TODO: handle error
            print(cursor, "is not a cursor.")
            return

        print(vars(cursor))

    def cursorChangeThickness(self, cursor, thickness):
        if type(cursor) is not _Cursor:
            #TODO: handle error
            print(cursor, "is not a cursor.")
            return

        if thickness <= 0:
            #TODO: handle error
            print("Cursor Thickness cannot be lower or equal to 0")
            return

        cursor.thickness = thickness
        self.blockVarDict[cursor.name] = cursor



    def cursorChangeColor(self, cursor, r, g, b, a):
        if type(cursor) is not _Cursor:
            #TODO: handle error
            print(cursor, "is not a cursor.")
            return

        if r < 0 or r > 255 \
        or g < 0 or g > 255 \
        or b < 0 or b > 255:
            #todo: handle error
            print("Color value cannot be lower than 0 or greater than 255.")
            return

        if a<0 or a>1:
            #todo: handle error
            print("Color a value cannot be lower than 0 or greater than 1.")
            return

        cursor.color = [r, g, b, a]
        self.blockVarDict[cursor.name] = cursor


    def cursorDrawCircle(self, cursor, r):
        if type(cursor) is not _Cursor:
            #TODO: handle error
            print(cursor, "is not a cursor.")

    def cursorDrawFilledCircle(self, cursor, r):
        if type(cursor) is not _Cursor:
            #TODO: handle error
            print(cursor, "is not a cursor.")












