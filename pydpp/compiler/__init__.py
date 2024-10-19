# Functions available to use within the IDE module.

from . import tokenizer
from . import CTranslater

def compile_code(code):
    x = tokenizer.tokenize(code)
    pass

def magic():
    print("Y'a plein de magie !!")