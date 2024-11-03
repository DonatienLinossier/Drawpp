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
from ._Function import Function
from .Variable import VarCall


'''All functions and variables (varDict) related to the main function have been deleted as the main function is now a simple function'''

class CTranslater:
    def __init__(self, filename):

        #TODO: make verif about the file
        self.filename = filename
        self.file = open(self.filename, "w")
        self.header()




        #self.main is the entry point of the created program
        #TODO: Add the possibility to run with arguments
        #TODO: add the possibility to have optionals arguments
        self.main = Function("Main", [])


        '''
        #Self.varDict contains the variables of the main function.
        self.varDict = {}
        '''
        #self.instr store all the core functions of the compilater and the functions created by the user.
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



    '''Contains all the added functions'''
    def drawCircle(self, x, y, radius):
        #TODO: add type verif for parameters x,y,radius (and range ? yes for radius)
        self.file.write("drawCircle(renderer, " + str(x) + ", " + str(y) + ", " + str(radius) + ");\n")

    def drawCircleFill(self, x, y, radius):
        #TODO: add type verif for parameters x,y,radius (and range ? yes for radius)
        self.file.write("drawCircleFill(renderer, " + str(x) + ", " + str(y) + ", " + str(radius) + ");\n")

    def drawRect(self, x, y, width, height):
        #TODO: add type verif for parameters x,y,width,height (and range ? probably not)
        self.file.write(
            "drawRect(renderer, " + str(x) + ", " + str(y) + ", " + str(width) + ", " + str(height) + ");\n")

    def drawRectFill(self, x, y, width, height):
        #TODO: add type verif for parameters x,y,width,height (and range ? probably not)
        self.file.write(
            "drawRectFill(renderer, " + str(x) + ", " + str(y) + ", " + str(width) + ", " + str(height) + ");\n")

    def setColor(self, r, g, b, a):
        #TODO: add range and type verif for parameters r,g,b,a
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
        self.main.add_instruction(self.instr[instructionName], *args)

    def run(self):
        self.main()

    def createFunc(self, functionName, args):
        if functionName in self.instr:
            print("Function already exists")
            return
        newFunction = Function(functionName, args)
        self.instr[functionName] = newFunction

    def addInstructionToFunction(self, functionName, instr, *args):
        if (not functionName in self.instr):
            print("Function does not exist.")
            return

        if (not instr in self.instr):
            print("Instruction does not exist")
            return

        self.instr[functionName].add_instruction(self.instr[instr], *args)

    def __del__(self):
        self.file.write(footer)
        self.file.close()