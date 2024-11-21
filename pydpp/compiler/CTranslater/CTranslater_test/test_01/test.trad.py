
# Main program
booleanVar = True
cmpt = 0


def TestFunction(booleanVar, cmpt):
    while booleanVar:
        print(f"cmpt: {cmpt}")
        cmpt += 5
        if booleanVar:
            booleanVar = False
        else:
            pass
    print("After loop :")
    print(f"cmpt: {cmpt}")
    print(f"Bool: {booleanVar}")
    return booleanVar, cmpt


booleanVar, cmpt = TestFunction(booleanVar, cmpt)