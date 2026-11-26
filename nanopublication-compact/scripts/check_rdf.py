"""Check the graph links in an exported TriG or N-Quads dataset."""
import argparse
from pathlib import Path

from rdflib import Dataset, Namespace, RDF, URIRef

NP = Namespace("http://www.nanopub.org/nschema#")
ROLES = (NP.hasAssertion, NP.hasProvenance, NP.hasPublicationInfo)
DERIVED = URIRef("http://www.w3.org/ns/prov#wasDerivedFrom")


def inspect(dataset, withheld):
    errors = []
    heads = list(dataset.quads((None, RDF.type, NP.Nanopublication, None)))
    if not heads:
        errors.append("No typed nanopublication in a head graph")
    for publication, _, _, head in heads:
        names = [head]
        if head == dataset.default_context.identifier or not isinstance(head, URIRef):
            errors.append(f"{publication}: expected a named head graph")
        for role in ROLES:
            targets = list(dataset.graph(head).objects(publication, role))
            if len(targets) != 1 or not isinstance(targets[0], URIRef):
                errors.append(f"{publication}: expected one named graph for {role}")
                continue
            name = targets[0]
            if name in names:
                errors.append(f"{publication}: reused graph name {name}")
            names.append(name)
            triples = dataset.graph(name)
            if not len(triples):
                errors.append(f"{publication}: empty or missing graph {name}")
            if role == NP.hasAssertion:
                leaked = {term for triple in triples for term in triple if term in withheld}
                errors.extend(f"{publication}: withheld IRI in assertion: {term}" for term in sorted(leaked))
        if len(names) == 4:
            assertion, provenance = names[1:3]
            prov = dataset.graph(provenance)
            # A provenance graph can describe itself in addition to describing the claim.
            # A source for the graph alone does not identify the evidence for the assertion.
            if set(prov.subjects(DERIVED, None)) == {provenance}:
                claim_terms = {assertion, *dataset.graph(assertion).subjects()}
                if not any(s in claim_terms or o in claim_terms for s, _, o in prov):
                    errors.append(f"{publication}: source describes the provenance graph alone; link the assertion or claim to its evidence")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--format", choices=("trig", "nquads"))
    parser.add_argument("--withhold", action="append", default=[], metavar="CLAIM_IRI")
    args = parser.parse_args()
    fmt = args.format or {".trig": "trig", ".nq": "nquads", ".nquads": "nquads"}.get(args.file.suffix.lower())
    if not fmt:
        parser.error("Specify --format for an unrecognized filename")
    dataset = Dataset()
    try:
        dataset.parse(args.file, format=fmt)
    except Exception as exc:
        parser.exit(1, f"RDF parse failed: {exc}\n")
    errors = inspect(dataset, set(map(URIRef, args.withhold)))
    if errors:
        parser.exit(1, "\n".join(errors) + "\n")
    print("Graph links verified")
