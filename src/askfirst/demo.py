from .ablation import argmax, rank_gaps, sensitivity_map, sufficiency
from .schema import load_schema
from .stub import make_scorer

CASE = {
    "heart_rate": "high",
    "blood_pressure": "normal",
    "temperature": "normal",
    "smoker": True,
}


def main():
    schema = load_schema("clinical")
    scorer = make_scorer(schema)
    gaps = rank_gaps(CASE, scorer, schema)

    print("Record — 34F, chest pain 2h, HR high, BP normal, smoker\n")
    print(f"  SUFFICIENCY  {sufficiency(CASE, scorer, schema)} / 100")
    print(f"  leaning      {argmax(scorer(CASE))}\n")

    print("  Go get:")
    for gap in gaps[:5]:
        tell = gap.most_telling()
        detail = (
            f"if {tell.value} -> {tell.verdict}" if tell else "wouldn't change the answer"
        )
        print(
            f"    {gap.field:<16} p = {gap.flip_prob:.2f}   {detail:<26}"
            f" cost {gap.cost:>3.0f}  {gap.delay:>4.0f} min"
        )

    best = max(gaps, key=lambda g: g.value_per_cost())
    print(f"\n  Best value for money: {best.field} "
          f"(p = {best.flip_prob:.2f} at cost {best.cost:.0f})\n")

    print("  What the record already rests on:")
    for inf in sensitivity_map(CASE, scorer, schema)[:4]:
        print(f"    {inf.field:<16} influence {inf.shift:.3f}")


if __name__ == "__main__":
    main()
