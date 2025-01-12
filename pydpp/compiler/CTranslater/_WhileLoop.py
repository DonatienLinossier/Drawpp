from ._subBlock import _subBlock

"""
This class is what handle the mechanic of while loops.


loops are defined by:
                - 2 _subBlocks (conditionBlock, loopBlock)
                - The step of build (Are we building the conditionBlock ? the loopBlock ? )
                - The variable dict that they share with the parent function (pass at init and returned after execution)

At runtime, they can be assimilated as the following function:
        while(self.condition()) :
            self.loopBlock()
"""
class _WhileLoop:
    def __init__(self, id):
        self.__name__ = "#whileLoop_" + str(id)
        self.varDict = {} #the scope
        self.conditionBlock = _subBlock()
        self.loopBlock = _subBlock()
        self.actualSteps = 0
        #TODO: Implement a limit to detect endless loop


    """
    This fonction is launch at runtime(when compiling).
    It only implements the mechanic, the real compilation is handle by subBlock. 
    """
    def __call__(self, varDict: dict) -> (dict, any):  #returns the scope and the returnValue
        self.varDict = varDict
        while self.conditionBlock(varDict)[1]:
            self.varDict, returnedValue = self.loopBlock(varDict)

            if returnedValue is not None:
                return self.varDict, returnedValue

        return self.varDict, None



    #The add_instruction function is the function that is called in the construction step.
    def add_instruction(self, instr, *args):
        match self.actualSteps:
            case 0:
                self.conditionBlock.add_instruction(instr, *args)
            case 1:
                self.loopBlock.add_instruction(instr, *args)
            case _:
                print("Error !!")
                #todo: handle error

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


