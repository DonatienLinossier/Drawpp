from .Variable import VarCall

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
            self.instr.append((self.overrideInstr[func.__name__], args))
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