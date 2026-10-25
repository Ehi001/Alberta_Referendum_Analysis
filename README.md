# Alberta 2026 Referendum Analysis (Power BI)

An interactive Power BI report on the results of Alberta's October 19, 2026 referendum: 10 questions, 87 electoral divisions and 5,540 voting locations. The data comes from Elections Alberta's public results feed.

> **Data status:** unofficial results pulled 2026-10-23 17:28 UTC, with 5,515 of 5,540 voting locations reported. Elections Alberta is scheduled to publish official results on 2026-10-29. Re-run the extract script after that date to update the numbers.

## Key findings

| Finding | Evidence |
|---|---|
| **Alberta stays.** Remain (Q10, Option 1) won by more than 1 million votes. | 74.9% Remain vs. 25.1% for starting the separation process. Only 2 of 87 divisions favoured Option 2: Rimbey-Rocky Mountain House-Sundre (51.2%) and Central Peace-Notley. |
| **A split verdict on policy.** Questions 1–5 passed and questions 6–9 failed. | Strongest support: proof of citizenship to vote (58.1% Yes). Weakest: opting out of federal programs with full funding (42.4%). |
| **Cities vs. the rest.** Votes outside Calgary and Edmonton carried the questions that passed. | Yes share across Q1–9: 60.4% in the rest of Alberta, 42.4% in Calgary, 37.8% in Edmonton. The rest of Alberta cast 48% of ballots. |
| **How people voted mattered.** Mail-in voters leaned strongly toward Remain and No. | Q10 Remain was 91.1% on special (mail-in) ballots vs. 66.9% on election day. Yes on Q1–9 ran 29 points lower on special ballots. |
| **One voting bloc.** Support for separation lines up with support for the policy questions. | Across the 87 divisions, the correlation between the Q10 Option 2 share and Yes on Q1–9 is 0.97. |
| **Some voters skipped questions.** | Q10 drew the most ballots (2,069,198). The least-answered question drew 41,153 fewer. |

## Report pages

1. **Overview**: KPI tiles, Yes share for every question, a results summary table, and auto-generated insights that recalculate on refresh.
2. **Q10 · Independence**: Remain share by region and by voting method, a heatmap of divisions × voting method, and every division ranked.
3. **Regional divide**: Calgary vs. Edmonton vs. the rest of Alberta on Q1–9, as a grouped bar chart, a heatmap, and divisions won per question.
4. **Voting method**: election day, advance, mobile and special ballots compared, with a heatmap, ballot mix and Q10 by method.
5. **Division explorer**: question and region slicers, a scatter of the separation vote vs. the policy vote by division, a ranked table, and a full division × question heatmap.

## Data model

Star schema, imported from CSV:

| Table | Grain | Rows |
|---|---|---|
| `fact_results_by_location` | Question × voting location (Yes/No votes) | 55,400 |
| `fact_results_by_division` | Question × electoral division (cross-check) | 870 |
| `dim_question` | Ballot question, with labels (Q10: Yes = Remain, No = Option 2) | 10 |
| `dim_electoral_division` | Division, with area (Calgary / Edmonton / Rest of Alberta) | 87 |
| `dim_voting_location` | Voting location, with vote type | 5,540 |
| `Key Measures` | 50+ DAX measures in display folders | — |
| `Insights` | Calculated table of plain-English findings built from measures | 6 |

Notable DAX techniques:
- A Pearson correlation computed in DAX across divisions (`Separation Correlation`)
- `TOPN`-based text measures for the strongest, closest and most supportive divisions
- A calculated table (`Insights`) whose text is generated from measures at refresh time
- Rule-based diverging conditional formatting centred on 50% (or 70% for Q10)

## How to open it

1. Install [Power BI Desktop](https://powerbi.microsoft.com/desktop/) (2024 or later).
2. Clone or download this repository.
3. Open `Alberta Referendum Result.pbip`.
4. The report reads its CSVs from the `DataFolder` parameter, which defaults to `C:\alberta-referendum-analysis\data\`. If you cloned somewhere else, go to **Home → Transform data → Edit parameters** and point `DataFolder` at this repo's `data\` folder, ending with a backslash.
5. Click **Refresh**.

## Refreshing the data

`scripts/ab_referendum_extract.py` calls the same public JSON endpoint as the Elections Alberta results page (`results.elections.ab.ca/data/8400`) and rebuilds all five CSVs.

```bash
pip install requests
python scripts/ab_referendum_extract.py data
```

The script prints a validation block (location totals must equal division totals, and there must be 5,540 × 10 fact rows). Then refresh Power BI.

## Notes

- Results are **unofficial** until Elections Alberta certifies them.
- Q10 was not a Yes/No question. In this dataset, `YesVotes` = Option 1 (remain a province of Canada) and `NoVotes` = Option 2 (begin the legal process toward a binding separation referendum).
- Source: [Elections Alberta](https://www.elections.ab.ca/elections/referendum/). This is an independent analysis and is not affiliated with Elections Alberta.

## Author

Ehidiamen Oaikhena, analytics engineer (Microsoft Fabric / Power BI)
