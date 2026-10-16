# 标注手册 / Annotation codebook — historical backtesting outcomes

> 中英对照版。术语代码（`answered` 等）保持英文原样填写，说明为中英双语。
> Bilingual. Label codes are always written in English; explanations are given
> in Chinese and English.

## 中文速览

你看到的是一个写于 **2021 年之前**的科研问题，加上最多 8 篇**之后**发表的论文摘要。
**只根据这些摘要判断**，不要上网查——AI 裁判当时看到的就是这几篇。

每题给**两个独立标签**：

| `outcome` 问题本身的命运 | 含义 |
|---|---|
| `answered` | 已解决：后续文献实质性解决了它，你现在能说出答案 |
| `partially_addressed` | 部分推进：有直接相关的实质进展，核心问题仍未解决 |
| `posed_but_open` | 被提出但未解决：后续文献也提出了同一问题，但没解决 |
| `not_addressed` | 未被触及：没有摘要实质涉及它（**同话题不算**） |

| `premise_status` 它依赖的假设的命运 | 含义 |
|---|---|
| `supported` | 假设被证实 |
| `refuted` | 假设被推翻 |
| `weakened` | 假设被动摇，但未彻底证伪 |
| `still_plausible` | 假设未被直接检验过 |
| `not_applicable` | 这个问题不依赖任何可争议的假设 |

**最容易犯的错：把「同话题」当成「有人研究了这个问题」。** 摘要讲同一颗行星、
同一个分子都**不算**，必须碰到这个问题真正要检验的东西，或它依赖的那个假设。

一个问题可以**正因为**假设被推翻而得到解决：`answered` + `refuted` 是合理组合。

`confidence` 填 1（没把握）/ 2（一般）/ 3（很有把握）；`notes` 写你犹豫在哪里。

---

## English version

You will see a research question written **before 2021**, and up to eight
abstracts of papers published **after** it. Judge only from these abstracts.
You do not need to know the field's later history; if an abstract does not
show it, it did not happen for our purposes.

Assign **two independent labels** per item.

## Label 1 — outcome: what happened to the question?

| Code | Meaning | Test to apply |
|---|---|---|
| `answered` | The literature substantially resolved it | Could you now state the answer, citing these abstracts? |
| `partially_addressed` | Substantial directly-relevant progress, core question still open | Real progress on *this* question, but no resolution |
| `posed_but_open` | Later work independently raises the same question without resolving it | The abstracts ask it too, and leave it open |
| `not_addressed` | No abstract engages it substantively | Same topic is **not** engagement |

**The single most common error is confusing topic overlap with engagement.**
An abstract about the same planet, or the same molecule, does not count
unless it bears on the question's actual test or its premise.

## Label 2 — premise_status: what happened to the assumption the question rests on?

| Code | Meaning |
|---|---|
| `supported` | Later evidence confirms the premise |
| `refuted` | Later evidence falsifies it |
| `weakened` | Later evidence seriously undermines it without falsifying |
| `still_plausible` | The premise was never directly tested |
| `not_applicable` | The question rests on no contestable premise |

A question can be `answered` **because** its premise was `refuted` — that
combination is expected, not a contradiction.

## Worked examples

*Question:* "Is the strongly subsolar terminator water abundance retrieved for
HD 209458 b a property of the atmosphere, or an artifact of retrieval
assumptions?"
*Abstracts:* three independent reanalyses converging on a solar abundance.
→ `answered` + `refuted` (the question is settled, and settled by overturning
the premise it challenged).

*Question:* the same question.
*Abstracts:* several papers measuring water in *other* hot Jupiters.
→ `not_addressed` (same topic, different object — no bearing on this test).

*Question:* "How do inhomogeneous terminators bias retrieved abundances?"
*Abstracts:* papers demonstrating the bias exists in general, none resolving
the specific case asked about.
→ `partially_addressed` + `still_plausible`.

## Procedure

1. Work through items **in the order given**; do not skip ahead.
2. Do **not** discuss items with the other annotator until both sheets are done.
3. Do **not** look up the papers online — abstracts only. The LLM judge saw
   exactly these abstracts, so any extra knowledge you use breaks the
   comparison.
4. Enter `confidence` as 1 (low) / 2 (medium) / 3 (high). Low-confidence items
   are analysed separately — they are informative, not failures.
5. Use `notes` freely, especially where you hesitated.

Budget roughly 2–3 minutes per item.
