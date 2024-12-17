from dataclasses import dataclass
from typing import Union

from pydpp.compiler.tokenizer import TokenKind, Token

# ==================================
# codegen.py: The Node class code generator
# ==================================
# This module generates all the InnerNode classes for every Node Definition found in nodedefs.py.
# The goal of this code generation mechanism is to avoid writing tons of boring code defining
# a single node: slots, children functions, properties, __init__, etc.
#
# It works by reading a list of classes, with each class attribute containing a tuple describing the slot:
#   (type, multi, check, optional, doc)
# The single/multi functions can be used to generate these tuples easily.
#
# Then, it just reads this list and generates the classes in generated.py.
#
# TO UPDATE THE generated.py FILE: Run this file, not the module!
#    python3 pydpp/compiler/syntax/codegen.py


class PythonOutput:
    def __init__(self):
        self.text = ""
        self.indent = 0

    def write(self, text: str):
        self.text += text

    def write_indent(self, text: str = ""):
        self.text += "    " * self.indent + text

    def newline(self):
        self.text += "\n"

    def writeln(self, text: str = ""):
        self.write_indent(text)
        self.newline()

    def inc_indent(self):
        self.indent += 1

    def dec_indent(self):
        self.indent -= 1


NodeCheck = Union[TokenKind, list[TokenKind], str, None]


@dataclass
class SlotProp:
    name: str
    "Name of the slot"
    multi: bool
    "Whether it's a multi slot or not"
    slot_attr_name: str
    "The name of the class attribute containing the slot, usually xxx_slot"
    storage_attr_name: str
    "The name of the attribute storing the slot value, usually self._xxx"
    element_type: str
    "The type of the element in the slot, not a list!"
    property_type: str
    "The type of the property"
    doc_string: str | None
    "The docstring of the slot and property"
    check: NodeCheck
    "The check function for the slot"
    optional: bool
    "Whether the slot is optional or not, only applicable for single slots"


def single(t: Union[type, TokenKind], *, check: NodeCheck = None, optional=True, doc: str = "") -> tuple[
    type, bool, NodeCheck, bool, str | None]:
    if isinstance(t, TokenKind):
        assert check is None
        check = t
        t = Token

    return t, False, check, optional, doc or None


def multi(t: Union[type, TokenKind], *, check: NodeCheck = None, optional=True, doc: str = "") -> tuple[
    type, bool, NodeCheck, bool, str | None]:
    if isinstance(t, TokenKind):
        assert check is None
        check = t
        t = Token
    return t, True, check, optional, doc or None


# Class decorator that add relevants attributes like extension_class
def declare_definitions():
    nodes = []

    def node_class(*args, extension_class: str | None = None):
        def decorator(cls):
            cls.extension_class = extension_class
            nodes.append(cls)
            return cls

        if args:
            return decorator(args[0])
        else:
            return decorator

    return node_class, nodes


def generate_code(definition_classes: list[type], doc_str_indentation=0) -> str:
    """
    Generates the Python code for the InnerNode classes, as defined in nodedefs.py.
    """
    out = PythonOutput()

    out.writeln("# ============================")
    out.writeln("# AUTO-GENERATED CODE: NODE DEFINITIONS CLASSES DEFINED IN nodedefs.py")
    out.writeln("# This file contains the generated classes issued from the nodedefs.py file.")
    out.writeln("# It is generated by the codegen.py module.")
    out.writeln("# ============================")
    out.newline()
    out.writeln("from pydpp.compiler.syntax.base import *")
    out.writeln("from pydpp.compiler.tokenizer import Token, TokenKind")
    out.writeln("import pydpp.compiler.syntax.genext as genext")
    out.writeln("from typing import Iterable")
    out.newline()

    for c in definition_classes:
        class_name = c.__name__
        slots: list[SlotProp] = []
        base_class = "InnerNode"
        doc_str = c.__doc__.strip() if c.__doc__ else None
        extension_class_name = c.extension_class if hasattr(c, "extension_class") else None

        # Step 0: Collect data for slots
        for name, val in c.__dict__.items():
            if name[0] == '_' or type(val) != tuple:
                continue

            slot_type, multi, check, optional, doc = val

            if isinstance(check, str) and extension_class_name is None:
                raise ValueError(
                    f"Slot {name} in class {class_name} uses a check function ({check}) but no extension class is specified.")

            element_type = slot_type.__name__
            if element_type == "Token":
                element_type = "LeafNode"

            if multi:
                prop_type = f"Iterable[{element_type}]"
            else:
                if optional:
                    prop_type = f"{element_type} | None"
                else:
                    prop_type = element_type

            slots.append(SlotProp(
                name=name,
                multi=multi,
                slot_attr_name=name + "_slot",
                storage_attr_name="_" + name,
                element_type=element_type,
                property_type=prop_type,
                doc_string=doc,
                check=check,
                optional=optional)
            )

        if len(c.__bases__) > 0 and c.__bases__[0] != object:
            base_class = c.__bases__[0].__name__

        node_only_slots = [x for x in slots if x.element_type != "LeafNode"]

        def print_slot_doc_string(s: SlotProp, force_triple_quotes=False):
            if s.doc_string:
                lines = s.doc_string.split("\n")
                if len(lines) == 1 and not force_triple_quotes:
                    out.writeln('"' + repr(lines[0])[1:-1] + '"')
                else:
                    out.writeln('"""')
                    for line in lines:
                        out.writeln(line)
                    out.writeln('"""')

        # ==============
        # Begin generating the class!
        # ==============

        ext_suffix = f", genext.{extension_class_name}" if extension_class_name else ""
        out.writeln(f"class {class_name}({base_class}{ext_suffix}):")
        out.inc_indent()

        if doc_str:
            out.writeln('"""')
            lines = doc_str.split('\n')
            out.writeln(lines[0])
            for line in lines[1:]:
                out.writeln(line[doc_str_indentation:])
            out.writeln('"""')

        # Step 1: Print the __slots__ attribute.
        out.write_indent("__slots__ = (")
        for s in slots:
            out.write(f"{s.storage_attr_name!r}, ")
        out.write(")")

        out.newline()
        out.newline()

        # Step 2: Print out the _slot class attributes
        for s in slots:
            type_name = "MultiNodeSlot" if s.multi else "SingleNodeSlot"
            out.write_indent(f"{s.slot_attr_name}: {type_name}[\"{class_name}\", {s.element_type}]"
                             f" = {type_name}({s.storage_attr_name!r}, {s.element_type}")

            if s.check is not None:
                if isinstance(s.check, TokenKind):
                    out.write(f", check_func=lambda x: x.kind == TokenKind.{s.check.name}")
                elif isinstance(s.check, list):
                    set_notation = '{' + ", ".join(f"TokenKind.{x.name}" for x in s.check) + '}'
                    out.write(f", check_func=lambda x: x.kind in {set_notation}")
                elif isinstance(s.check, str):
                    out.write(f", check_func=genext.{extension_class_name}.{s.check}")

            if not s.optional:
                out.write(", optional=False")

            out.write(")")
            out.newline()
            print_slot_doc_string(s)

        out.newline()

        if len(slots) == 0:
            out.dec_indent()
            out.newline()
            continue

        # Step 3: The __init__ function
        out.write_indent("def __init__(self, ")
        for i, s in enumerate(slots):
            out.write(f"{s.name}: {s.property_type}")
            if i != len(slots) - 1:
                out.write(", ")
        out.write("):")
        out.newline()

        out.inc_indent()
        local_id = 0
        out.writeln("super().__init__()")
        for s in slots:
            if s.multi:
                # Initialize a multi slot.
                local_id += 1

                out.writeln(f"self.{s.storage_attr_name} = list({s.name})")
                out.writeln(f"for s_init_el in self.{s.storage_attr_name}:")
                out.inc_indent()

                out.writeln(f"assert s_init_el is not None and {class_name}.{s.slot_attr_name}.accepts(s_init_el)")

                out.writeln(f"s_init_el.register_attachment(self, {class_name}.{s.slot_attr_name})")
                out.writeln("if s_init_el.has_problems: self._update_has_problems(True)")
                out.dec_indent()
                out.newline()
            else:
                if s.optional:
                    out.writeln(f"assert {s.name} is None or {class_name}.{s.slot_attr_name}.accepts({s.name})")
                else:
                    out.writeln(f"assert {s.name} is not None and {class_name}.{s.slot_attr_name}.accepts({s.name})")

                out.writeln(f"self.{s.storage_attr_name} = {s.name}")

                if s.optional:
                    out.writeln(f"if {s.name} is not None: ")
                    out.inc_indent()

                out.writeln(f"{s.name}.register_attachment(self, {class_name}.{s.slot_attr_name})")
                out.writeln(f"if {s.name}.has_problems: self._update_has_problems(True)")

                if s.optional:
                    out.dec_indent()
                out.newline()

        out.dec_indent()

        # Step 4: The properties
        for s in slots:
            out.newline()
            out.write_indent("@property")
            out.newline()
            out.write_indent(f"def {s.name}(self) -> {s.property_type}:")
            out.newline()
            out.inc_indent()
            print_slot_doc_string(s, True)
            out.writeln(f"return self.{s.storage_attr_name}")
            out.dec_indent()

            if not s.multi:
                out.newline()
                out.write_indent(f"@{s.name}.setter")
                out.newline()
                out.write_indent(f"def {s.name}(self, value: {s.property_type}):")
                out.newline()
                out.inc_indent()
                if s.optional:
                    out.writeln("if value is not None: ")
                    out.inc_indent()
                    out.writeln(f"self.{s.storage_attr_name} = self.attach_child(self.{s.slot_attr_name}, value)")
                    out.dec_indent()
                    out.writeln("else:")
                    out.inc_indent()
                    out.writeln(f"self.detach_child(self.{s.slot_attr_name})")
                    out.dec_indent()
                else:
                    out.writeln(f"self.{s.storage_attr_name} = self.attach_child(self.{s.slot_attr_name}, value)")

                out.dec_indent()

            # Create a token_str property for identifiers so we can easily get its value.
            if s.check == TokenKind.IDENTIFIER and not s.multi:
                out.newline()
                out.write_indent("@property")
                out.newline()
                out.write_indent(f"def {s.name}_str(self) -> str:")
                out.newline()
                out.inc_indent()
                print_slot_doc_string(s, True)
                out.writeln(f"return self.{s.storage_attr_name}.text")
                out.dec_indent()


        # Step 5: The children functions
        out.newline()
        out.writeln("@property")
        out.writeln("def children(self):")
        out.inc_indent()
        for s in slots:
            if s.multi:
                out.writeln(f"yield from self.{s.storage_attr_name}")
            else:
                if s.optional:
                    out.writeln(f"if self.{s.storage_attr_name} is not None: yield self.{s.storage_attr_name}")
                else:
                    out.writeln(f"yield self.{s.storage_attr_name}")
        out.dec_indent()
        out.newline()

        out.writeln("@property")
        out.writeln("def children_reversed(self):")
        out.inc_indent()
        for s in reversed(slots):
            if s.multi:
                out.writeln(f"yield from reversed(self.{s.storage_attr_name})")
            else:
                if s.optional:
                    out.writeln(f"if self.{s.storage_attr_name} is not None: yield self.{s.storage_attr_name}")
                else:
                    out.writeln(f"yield self.{s.storage_attr_name}")
        out.dec_indent()
        out.newline()

        out.writeln("@property")
        out.writeln("def child_inner_nodes(self):")
        out.inc_indent()
        if node_only_slots:
            if len(node_only_slots) == 1 and node_only_slots[0].multi:
                s = node_only_slots[0]
                out.writeln(f"return self.{s.storage_attr_name}")
            else:
                for s in node_only_slots:
                    if s.multi:
                        out.writeln(f"yield from self.{s.storage_attr_name}")
                    else:
                        if s.optional:
                            out.writeln(f"if self.{s.storage_attr_name} is not None: yield self.{s.storage_attr_name}")
                        else:
                            out.writeln(f"yield self.{s.storage_attr_name}")
        else:
            out.writeln("return []")
        out.dec_indent()

        out.dec_indent()
        out.newline()

        # Step 6: The element_slots and inner_node_slots class attributes (do it outside the class definition)
        out.write_indent(f"{class_name}.element_slots = (")
        for s in slots:
            out.write(f"{class_name}.{s.slot_attr_name}, ")
        out.write(")")
        out.newline()

        out.write_indent(f"{class_name}.inner_node_slots = (")
        for s in node_only_slots:
            out.write(f"{class_name}.{s.slot_attr_name}, ")
        out.write(")")
        out.newline()

        out.newline()
        out.newline()

    return out.text


def clear_file():
    import os
    path = os.path.join(os.path.dirname(__file__), "generated.py")

    # First, clear the file to avoid runtime interpreter errors
    # if the file is invalid.
    with open(path, "w"):
        pass  # Mode w already truncates the file.


def generate_file():
    import os
    import nodedefs
    path = os.path.join(os.path.dirname(__file__), "generated.py")

    # Generate the code and write it to the file
    code = generate_code(nodedefs.definitions(), doc_str_indentation=8)
    with open(path, "w") as f:
        f.write(code)
    print(f"Code generated at {path}")


if __name__ == '__main__':
    clear_file()
    generate_file()