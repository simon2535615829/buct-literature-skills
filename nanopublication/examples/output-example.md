## 教学示例输出

以下内容节选自随包合成示例在 Linux 中生成的 catalog/claims.json。

```json
[
  {
    "subject": "Quartz",
    "relation": "had less drift than",
    "object": "Slate",
    "condition": "10 °C",
    "polarity": "positive",
    "modality": "reported observation",
    "confidence_basis": "The synthetic motion observation identifies the two devices, their order and the test temperature.",
    "evidence": [
      "X1"
    ],
    "support": "direct",
    "supporting_clauses": [
      {
        "evidence": "X1",
        "locator": "Synthetic example, line 1",
        "text": "At 10 °C, Quartz had less drift than Slate"
      }
    ],
    "iri": "urn:paper-skill:ae242f5985ddbc2469bf0659046cc9583a9b95b25c06afd05232b1dcba1971b7",
    "sources": [
      {
        "id": "X1",
        "file": "source.txt",
        "lines": [
          1,
          1
        ],
        "quote": "At 10 °C, Quartz had less drift than Slate.",
        "locator": "Synthetic example, line 1",
        "document": "D"
      }
    ],
    "documents": {
      "D": {
        "title": "Synthetic bench observations",
        "version": "teaching-1",
        "authors": null,
        "year": null
      }
    },
    "creator": "示例整理者"
  }
]
```
