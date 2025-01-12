"""
WIP: This class is not implemented yet.

The purpose of this class is to handle error in the CTranslater.
This part is not necessary as most of the errors are handled before the CTranslater, but it is still interesting if
we want to improve the error detection. The idea is to respect the moto "If it compiles, it runs".

The errors we wanna detect here are errors that we want to anticipate from the runtime. For example, detect endless loop.
Other securities can be added such as type verification. (no necessary and could be heavy as the type detection is already
done previously)
"""

class _error:
    def __init__(self, instructionName: str, description: str, errorStack: str = None):
        """
        Represents an error occurring in a specific instruction.

        :param instructionName: Name of the instruction where the error occurred.
        :param description: Description of the error.
        :param errorStack: Optional stack trace or additional error details.
        """
        self.instructionName = instructionName
        self.description = description
        self.errorStack = errorStack

    def __repr__(self) -> str:
        returnString = "Error in {}: {}\n".format(self.instructionName, self.description)
        if self.errorStack:
            returnString += "{}".format(self.errorStack)
        return returnString