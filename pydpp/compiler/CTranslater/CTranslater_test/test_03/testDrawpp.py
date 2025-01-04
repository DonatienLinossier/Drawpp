from pydpp.compiler.CTranslater import *

test = CTranslater(".drawppTmp/tmp.c")


#Main
test.add_instruction("setColor", 10, 10, 250, 1)
test.add_instruction("drawCircleFill", 20, 20, 20)

test.run()
