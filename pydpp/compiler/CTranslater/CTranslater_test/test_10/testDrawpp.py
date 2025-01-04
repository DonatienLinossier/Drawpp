from pydpp.compiler.CTranslater import *

test = CTranslater(".drawppTmp/tmp.c")


#Main
test.add_instruction("createCursor", "cursor1", 70, 70, 0, 255, 10, 10, 1)
test.add_instruction("cursorChangeThickness", VarCall("cursor1"), 50)
test.add_instruction("_cursorPrintData", VarCall("cursor1"))

test.run()