"""Not working yet"""


from .Variable import VarCall
class Function:
    def __init__(self, name, listParameters):
        self.__name__ = name
        self.condition = []
        self.trueInstr = []
        self.falseInstr = []

    def __call__(self, *args):




        if True:
            instructions = self.trueInstr
        else :
            instructions = self.falseInstr

        for instr in instructions:
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
                        #TODO: HAndle error
                else:
                    argumentsFinal.append(arg)

            # Call the function with final arguments
            func(*argumentsFinal)
            #print("In function: " + str(self.FunctVarDict))

    def add_trueInstruction(self, func, *args):
            self.trueInstr.append((func, args))

    def add_falseInstruction(self, func, *args):
        self.falseInstr.append((func, args))