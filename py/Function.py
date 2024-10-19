from Variable import VarCall
class Function:
    #Todo: get returned, and store it ? value from funct
    #Todo: Recursivity trouble. a function can call a func, but what about an instr calling another instr ??
    def __init__(self, name, listParameters):
        self.__name__ = name
        self.instr = []
        self.nb_param = len(listParameters)
        self.protoParameters = listParameters


        # Each function maintains its own variable dictionary
        self.FunctVarDict = {}
        self.overrideInstr = {
            "getVar": self.functGetVar,
            "addToVar": self.functAddToVar,
            "createVar": self.functCreateVar,
            "returnStatement": self.functReturnStatement
        }

    def __call__(self, *args):
        if len(args) != self.nb_param:
            print(f"Function {self.__name__} takes {self.nb_param} argument(s). Only {len(args)} were given.")
            return

        # Assign each argument value to its parameter
        for i in range(len(args)):
            self.FunctVarDict[self.protoParameters[i]] = args[i]  # Converts list to tuple

        for instr in self.instr:
            # Extract function and arguments
            func = instr[0]
            arguments = instr[1]
            argumentsFinal = []

            for arg in arguments:
                # Handle variable references
                if isinstance(arg, VarCall):
                    if arg.name in self.FunctVarDict:
                        argumentsFinal.append(self.FunctVarDict[arg.name])
                    else :
                        pass
                        print(self.FunctVarDict)
                        print("Error")
                        #TODO: HAndle error
                else:
                    argumentsFinal.append(arg)

            # Call the function with final arguments
            func(*argumentsFinal)
            #print("In function: " + str(self.FunctVarDict))

    def add_instruction(self, func, *args):
        if func.__name__ in self.overrideInstr:
            self.instr.append((self.overrideInstr[func.__name__], args))
        else:
            self.instr.append((func, args))

    def functCreateVar(self, name, value):
        self.FunctVarDict[name] = value

    #TODO: What is the point ??
    def functGetVar(self, name):
        return self.FunctVarDict.get(name, None)  # Return None if variable does not exist

    def functReturnStatement(self, value):
        self.instr.clear()
        return value

    def functAddToVar(self, name, value):
        if name in self.FunctVarDict:
            self.FunctVarDict[name] += value
        else:
            print(f"Variable '{name}' does not exist.")