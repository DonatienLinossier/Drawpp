#Donatien
header = """ 
#include <SDL2/SDL.h>
#include <stdio.h>

#include "cursor.h"
#include "sdlEncapsulation.h"


                    
int main(int argc, char* args[]) {
                    
    SDL_Window *window = NULL;
    SDL_Renderer *renderer = NULL;
                    
    if (initSDL(&window, &renderer) != 0) 
    {
    return -1;
    }
    
    int returnStatement = 0;
    
    //Start of the generated code
    """

footer = """ 
    //End of the generated code

    SDL_RenderPresent(renderer);
    SDL_Delay(3000);
    
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
                    
    return returnStatement;
}"""
import os
import sys

sys.path.append(os.getcwd()+"\CTranslater_p")

print(sys.path)

from ._Function import Function
from .Variable import VarCall


class CTranslater:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(self.filename, "w")
        self.header()

        #TODO: Add the possibility to run with arguments
        #TODO: add the possibility to have optionals arguments
        self.main = Function("Main", [])

        self.varDict = {}
        self.instr = {"createVar": self.createVar,
                      "getVar": self.getVar,
                      "addToVar": self.addToVar,
                      "drawCircle": self.drawCircle,
                      "drawCircleFill": self.drawCircleFill,
                      "drawRect": self.drawRect,
                      "drawRectFill": self.drawRectFill,
                      "setColor": self.setColor,
                      "deb": self.deb,
                      "sleep": self.sleep,
                      "returnStatement": self.returnStatement
                      }

    def createVar(self, name, value):
        self.varDict[name] = value

    #Todo: get var for what ?? To delete.
    def getVar(self, name):
        return self.varDict[name]

    def addToVar(self, name, value):
        self.varDict[name] += value


    def drawCircle(self, x, y, radius):
        self.file.write("drawCircle(renderer, " + str(x) + ", " + str(y) + ", " + str(radius) + ");\n")

    def drawCircleFill(self, x, y, radius):
        self.file.write("drawCircleFill(renderer, " + str(x) + ", " + str(y) + ", " + str(radius) + ");\n")

    def drawRect(self, x, y, width, height):
        self.file.write(
            "drawRect(renderer, " + str(x) + ", " + str(y) + ", " + str(width) + ", " + str(height) + ");\n")

    def drawRectFill(self, x, y, width, height):
        self.file.write(
            "drawRectFill(renderer, " + str(x) + ", " + str(y) + ", " + str(width) + ", " + str(height) + ");\n")

    def setColor(self, r, g, b, a):
        self.file.write(
            "SDL_SetRenderDrawColor(renderer, " + str(r) + ", " + str(g) + ", " + str(b) + ", " + str(a) + ");\n")

    def header(self):
        self.file.write(header)

    def deb(self, test):
        print(test)

    def sleep(self, milliseconds):
        if not isinstance(milliseconds, int):
            print("milliseconds must be int type")
            return
        self.file.write("SDL_Delay( " + str(milliseconds) + ");\n")

    def returnStatement(self, value):
        #Todo: value must be an int
        self.file.write("returnStatement = " + str(value) + ";\n")

    def add_instruction(self, instructionName, *args):
        #print(f"Instruction Name: {instructionName}")
        #print(f"Instruction: {self.instr[instructionName]}")
        #print(f"Arguments: {args}")
        self.main.add_instruction(self.instr[instructionName], *args)
        #print(*args)

    def run(self):
        self.main()

    #TODO: not sure
    def createFunc(self, functionName, args):
        if functionName in self.instr:
            print("Function already exist")
            return
        newFunction = Function(functionName, args)
        self.instr[functionName] = newFunction

    #TODO: not sure
    def addInstructionToFunction(self, functionName, instr, *args):
        if (not functionName in self.instr):
            print("Function do not exist.")
            return

        if (not instr in self.instr):
            print("Instruction does not exist")
            return

        self.instr[functionName].add_instruction(self.instr[instr], *args)

    def __del__(self):
        self.file.write(footer)
        self.file.close()


"""if __name__ == '__main__':
    test = CTranslater("../output/test.c")


    test.add_instruction("createVar", "b", 105)
    test.add_instruction("setColor", 187, 40, VarCall("b"), 0)
    test.add_instruction("drawCircle", 158, 40, VarCall("b"))


    test.createFunc("MyTestFunction2", ["acb"])
    test.addInstructionToFunction("MyTestFunction2", "deb", VarCall("acb"))

    test.createFunc("MyTestFunction", ["a"])
    test.addInstructionToFunction("MyTestFunction", "deb", VarCall("a"))
    test.addInstructionToFunction("MyTestFunction", "MyTestFunction2", "salut")

    test.add_instruction("MyTestFunction", 5)
    test.add_instruction("MyTestFunction", "Test")
    test.add_instruction("MyTestFunction", 5)

    test.run()
"""