from typing import Union, Iterator

from ...symbols import NOUN, PROPN, PRON
from ...errors import Errors
from ...tokens import Doc, Span


def noun_chunks(doclike: Union[Doc, Span]) -> Iterator[Span]:
    """Detect base noun phrases from a dependency parse. Works on Doc and Span."""
    # It follows the logic of the noun chunks finder of English language,
    # adjusted to some Greek language special characteristics.
    # obj tag corrects some DEP tagger mistakes.
    # Further improvement of the models will eliminate the need for this tag.
    labels = ["nsubj", "obj", "iobj", "appos", "ROOT", "obl"]
    doc = doclike.doc  # type: ignore[union-attr]    # Ensure works on both Doc and Span.
    if not doc.has_annotation("DEP"):
        raise ValueError(Errors.E029)
    np_deps = [doc.vocab.strings.add(label) for label in labels]  # type: ignore[union-attr]
    conj = doc.vocab.strings.add("conj")  # type: ignore[union-attr]
    nmod = doc.vocab.strings.add("nmod")  # type: ignore[union-attr]
    np_label = doc.vocab.strings.add("NP")  # type: ignore[union-attr]
    prev_end = -1
    for i, word in enumerate(doclike):
        if word.pos not in (NOUN, PROPN, PRON):
            continue
        # Prevent nested chunks from being produced
        if word.left_edge.i <= prev_end:
            continue
        if word.dep in np_deps:
            flag = False
            if word.pos == NOUN:
                #  check for patterns such as γραμμή παραγωγής
                for potential_nmod in word.rights:
                    if potential_nmod.dep == nmod:
                        prev_end = potential_nmod.i
                        yield word.left_edge.i, potential_nmod.i + 1, np_label  # type: ignore[misc]
                        flag = True
                        break
            if flag is False:
                prev_end = word.i
                yield word.left_edge.i, word.i + 1, np_label  # type: ignore[misc]
        elif word.dep == conj:
            # covers the case: έχει όμορφα και έξυπνα παιδιά
            head = word.head
            while head.dep == conj and head.head.i < head.i:
                head = head.head
            # If the head is an NP, and we're coordinated to it, we're an NP
            if head.dep in np_deps:
                prev_end = word.i
                yield word.left_edge.i, word.i + 1, np_label  # type: ignore[misc]


SYNTAX_ITERATORS = {"noun_chunks": noun_chunks}
