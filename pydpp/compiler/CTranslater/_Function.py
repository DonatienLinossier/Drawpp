from ._subBlock import _subBlock
"""
The purpose of this class is to store and handle user-defined functions.
The Function class is callable, acting like a real function.

Each Function instance maintains its own private local scope, meaning child functions do not share variables
with their parent functions, and vice versa.

To achieve this private scope, the function will not execute nor store the istr itself. It will use a _subBlock.
The purpose of the _subBlock is to guaranty that the storage and the execution of the instructions are done within
a specific scope.  

Functions can accept arguments, and parameters can be declared at the time of function creation.
For the technical aspect, we just add variables to the scope before executing the fonc that are named following the 
parameters names given at creation, and the values past as arguments 

When a function is called, all instructions or nested functions within it are executed sequentially.
"""


class _Function:
    #Todo: get returned, and store it ? value from funct
    def __init__(self, name, listParameters):

        self.__name__ = name
        self.nb_param = len(listParameters)  #nb of parameters that the function takes
        self.protoParameters = listParameters  #The definition of the parameters
        self.lastReturnedValueFromFunction = None
        self.actualStep = 0
        self.subBlock = _subBlock()

        # Each function maintains its own variable dictionary, with the name of the variable used as the key
        self.FunctVarDict = {}

    """
    This fonction is launch at runtime(when compiling).
    It only implements the mechanic, the real compilation is handle by subBlock. 
    
    The functions verify if the number of arguments match the number of parameters.
    
    It then links and adds the arguments to the scope.

    And then it execute the code with the subBlock, passing it the scope, and collecting the scope and returnedValue.
    Only the returned value is returned by the function.
    """
    def __call__(self, *args) -> any:
        #TODO: Check the type of the arguments
        if len(args) != self.nb_param:
            print(f"Function {self.__name__} takes {self.nb_param} argument(s). Only {len(args)} were given.")
            return

        # Assign each argument value to its parameter
        for i in range(len(args)):
            self.FunctVarDict[self.protoParameters[i]] = args[i]

        scope, returnedValue = self.subBlock(self.FunctVarDict)

        #TODO: Verif on returned type
        return returnedValue


    #The add_instruction function is the function that is called in the construction step.
    def add_instruction(self, func, *args) -> None:
        self.subBlock.add_instruction(func, *args)


    def nextStep(self):
        self.actualStep += 1
        if self.actualStep > 1:
            print("Error")
            print("Handle error")


    def isFinished(self) -> bool:
        match self.actualStep:
            case 0:
                return False
            case 1:
                return True
            case _:
                print("Error")
                #TODO: Handle error
                return True



