from pydpp.compiler.CTranslater import *
import os

# Create the folder if it doesn't exist yet.
try:
    os.mkdir(".drawppTmp")
except:
    # "Oh no it already exists!" Yeah well we don't really care.
    pass
test = CTranslater(".drawppTmp/tmp.c")
#Main

test.add_instruction("createVar", "bool", True)
test.add_instruction("createVar", "cmpt", 0)

#def TestFunction(bool, cmpt) {
test.createFunc("TestFunction", ["bool", "cmpt"])

#while (
test.createWhileLoop()
test.add_instruction("functReturnStatement", VarCall("bool"))
test.endBlock()
# ) //end while condition

# {
test.add_instruction("deb", "cmpt")
test.add_instruction("deb", VarCall("cmpt"))

test.add_instruction("addToVar", "cmpt", 5)

#if (
test.createConditionalInstr()
test.add_instruction("functReturnStatement", VarCall("bool"))
test.endBlock()
#) { // end if condition

test.add_instruction("createVar", "bool", False)
test.endBlock()
# } else {

test.endBlock()
# } // end else


test.add_instruction("deb", "After loop :")
test.add_instruction("deb", "cmpt")
test.add_instruction("deb", VarCall("cmpt"))
test.add_instruction("deb", "Bool")
test.add_instruction("deb", VarCall("bool"))
test.endBlock()
# } //end While

test.endBlock()
# } //end TestFunction

test.add_instruction("TestFunction", VarCall("bool"), VarCall("cmpt"))
test.add_instruction("createVar", "cmpt", 5)
test.add_instruction("drawCircle", VarCall("cmpt"), VarCall("cmpt"), VarCall("cmpt"))

test.run()
