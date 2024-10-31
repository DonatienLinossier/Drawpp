from enum import Flag, auto
from typing import Iterable

from pydpp.compiler.syntax import AnnotationKey, AnnotationKeyMeta, Node, NodeProblem


class Location(Flag):
    NOWHERE = 0
    SELF = auto()
    CHILD = auto()

class ProblemsAnnotation(AnnotationKey[tuple[NodeProblem, ...]], metaclass=AnnotationKeyMeta):
    name = "problems"

class HasProblemsAnnotation(AnnotationKey[Location], metaclass=AnnotationKeyMeta):
    name = "has_problems"

    @classmethod
    def attached(cls, node: Node, v: Location):
        # Cascade SELF/CHILD values up the tree
        _propagate_location_annotation(node, cls, v)

    @classmethod
    def detached(cls, node: Node, v: Location):
        _propagate_location_annotation(node, cls, Location.NOWHERE)


def _propagate_location_annotation(node: Node, key: type[AnnotationKey[Location]], value: Location):
    if value:
        # We have a SELF or CHILD value (or both!).
        # Cascade it up by adding a CHILD flag to all parents.
        p = node.parent
        while p is not None:
            existing = p.annotations.get(key, Location.NOWHERE)
            if Location.CHILD in existing:
                break

            p.annotations[key] = existing | Location.CHILD
            p = p.parent
    else:
        # We have a NOWHERE value.
        # Remove any CHILD flags from parents, until we reach a SELF flag.
        p = node.parent
        while p is not None:
            if Location.SELF in p.annotations.get(key, Location.NOWHERE):
                break
            p.annotations[key] = Location.CHILD
            p = p.parent


def _add_location_annotation(node: Node, key: type[AnnotationKey[Location]], value: Location):
    cur = node.annotations.get(key, Location.NOWHERE)
    if cur != value:
        node.annotations[key] = cur | value
        _propagate_location_annotation(node, HasProblemsAnnotation, node.annotations[HasProblemsAnnotation])


def _remove_location_annotation(node: Node, key: type[AnnotationKey[Location]], value: Location):
    cur = node.annotations.get(key, Location.NOWHERE)
    if cur != value:
        node.annotations[key] = cur & ~value
        _propagate_location_annotation(node, HasProblemsAnnotation, node.annotations[HasProblemsAnnotation])


def node_get_problems(node: Node) -> tuple[NodeProblem, ...]:
    return node.annotations.get(ProblemsAnnotation, ())


def node_set_problems(node: Node, problems: Iterable[NodeProblem]):
    node.annotations[ProblemsAnnotation] = problems if isinstance(problems, tuple) else tuple(problems)
    if problems:
        _add_location_annotation(node, HasProblemsAnnotation, Location.SELF)
    else:
        _remove_location_annotation(node, HasProblemsAnnotation, Location.SELF)


def node_add_problems(node: Node, *problems: NodeProblem):
    node_set_problems(node, node_get_problems(node) + problems)