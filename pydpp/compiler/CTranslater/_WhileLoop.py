from ._subBlock import _subBlock


class _WhileLoop:
    def __init__(self, id):
        self.__name__ = "#whileLoop_" + str(id)
        self.varDict = {}
        self.conditionBlock = _subBlock()
        self.loopBlock = _subBlock()
        self.actualSteps = 0
        #TODO: Implement a limit to detect endless loop

    def __call__(self, varDict: dict) -> (dict, any):  #returns the scope and the returnValue
        self.varDict = varDict
        while self.conditionBlock(varDict)[1]:
            self.varDict, returnedValue = self.loopBlock(varDict)

            if returnedValue is not None:
                return self.varDict, returnedValue

        return self.varDict, None

    def nextStep(self):
        self.actualSteps += 1
        #Todo: Add verif that condition returns a bool value before changing step


    def getActualSubBlock(self):
        match self.actualSteps:
            case 0:
                return self.conditionBlock
            case 1:
                return self.loopBlock
            case _:
                print("Error !!")
                #todo: handle error

    def isFinished(self):
        if self.actualSteps > 1:
            return True
        else:
            return False

    def add_instruction(self, instr, *args):
        match self.actualSteps:
            case 0:
                self.conditionBlock.add_instruction(instr, *args)
            case 1:
                self.loopBlock.add_instruction(instr, *args)
            case _:
                print("Error !!")
                #todo: handle error
