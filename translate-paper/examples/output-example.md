## 教学示例输出

以下内容节选自随包合成示例在 Linux 中生成的 alignment.json。

```json
[
  {
    "id": "p1",
    "locator": "Example, Results ¶1",
    "text": "The drift did not exceed 2 mm [3].",
    "terms": [
      "drift"
    ],
    "protect": [
      "[3]"
    ],
    "translation": "漂移未超过 2 mm [3]。"
  },
  {
    "id": "t1",
    "locator": "Table 1, column 2",
    "text": "Maximum drift (mm)",
    "protect": [],
    "terms": [
      "drift"
    ],
    "translation": "最大漂移（mm）"
  },
  {
    "id": "f1",
    "locator": "Figure 2 caption",
    "text": "Offset x = 2 mm [3].",
    "protect": [
      "x = 2 mm",
      "[3]"
    ],
    "terms": [],
    "translation": "偏移量 x = 2 mm [3]。"
  }
]
```
