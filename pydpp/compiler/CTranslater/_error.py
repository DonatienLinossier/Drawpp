"""WIP: Not used yet"""

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