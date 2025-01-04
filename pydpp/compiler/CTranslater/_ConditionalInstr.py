"""Not working yet"""

from ._subBlock import _subBlock

"""
Conditional instructions are defined by:
                - 3 _subBlocks (_condition, _ifFunction, _elseFunction)
                - The step of build (Are we building the condition function ? the ifFunction ? or the elseFunction ?)
                - The variable dict that they share with the parent function (pass at init and returned after execution)

At runtime, they can be assimilated as the following function:
        if self.condition() :
            self.ifFunction()
        else :
            self.elseFunction()
            
            
At creation, the step of build is 0(condition). So when adding an instr it will be added to the conditionFunction. 
When finished with the conditional function, call the nextStep in order to pass to the next step, the ifFunction.
So now, when adding an instr it will be added to the ifFunction.
When finished, same as before, you need to call the nextStep function to get to the elseFunction
"""


class _ConditionalInstr:
    def __init__(self, id: int):
        self.__name__ = "#conditionalFunc_" + str(id)
        self.varDict = {}
        self.condition = _subBlock()
        self.ifFunction = _subBlock()
        self.elseFunction = _subBlock()
        self.actualSteps = 0

    def __call__(self, varDict: dict) -> (dict, any):
        #returns the scope and the returnValue

        self.varDict = varDict

        if self.condition(self.varDict)[1]:
            scope, returnedValue = self.ifFunction(self.varDict)
            return scope, returnedValue
        else:
            scope, returnedValue = self.elseFunction(self.varDict)
            return scope, returnedValue

    ###########################
    # The next functions are used to create the _ConditionalInstr
    ###########################
    def nextStep(self):
        self.actualSteps += 1
        #Todo: Add verif that condition returns a bool value before changing step

    def getActualSubBlock(self):
        match self.actualSteps:
            case 0:
                return self.condition
            case 1:
                return self.ifFunction
            case 2:
                return self.elseFunction
            case _:
                print("Error !!")
                #todo: handle error

    def isFinished(self):
        if self.actualSteps > 2:
            return True
        else:
            return False

    def add_instruction(self, instr, *args):
        match self.actualSteps:
            case 0:
                self.condition.add_instruction(instr, *args)
            case 1:
                self.ifFunction.add_instruction(instr, *args)
            case 2:
                self.elseFunction.add_instruction(instr, *args)
            case _:
                print("Error !!")
                #todo: handle error
