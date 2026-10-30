from collections import Counter
import math
import re

STOP = set(
    "a an the is are was were be been to of for in on and or it this that with as by should our".split()
)


def tokens(text):
    return [
        w
        for w in re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
        if w not in STOP
    ]


def rank(rows, query, limit):
    terms = set(tokens(query))
    if not rows or not terms:
        return []
    documents = [Counter(tokens(row["excerpt"])) for row in rows]
    lengths = [sum(d.values()) for d in documents]
    average = sum(lengths) / len(lengths) or 1
    frequencies = {term: sum(term in d for d in documents) for term in terms}
    ranked = []
    for row, counts, length in zip(rows, documents, lengths):
        score = 0.0
        for term in sorted(terms):
            frequency = counts[term]
            if frequency:
                inverse = math.log(
                    1
                    + (len(rows) - frequencies[term] + 0.5) / (frequencies[term] + 0.5)
                )
                score += (
                    inverse
                    * frequency
                    * 2.2
                    / (frequency + 1.2 * (0.25 + 0.75 * length / average))
                )
        if score > 0:
            ranked.append(dict(row) | {"score": round(score, 6)})
    return sorted(
        ranked,
        key=lambda r: (-r["score"], r["document_id"], r["page"], r["start_char"]),
    )[:limit]
