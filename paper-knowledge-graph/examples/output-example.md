## 教学示例输出

以下内容节选自随包合成示例在 Linux 中生成的 answers.json。

```json
[
  {
    "query": {
      "mode": "out",
      "start": "a",
      "predicate": "uses",
      "question": "Which instrument did Method A use?"
    },
    "paths": [
      [
        {
          "id": "e1",
          "source": "a",
          "target": "s",
          "predicate": "uses",
          "condition": "reported experiment",
          "polarity": "positive",
          "evidence": [
            "E1"
          ]
        }
      ]
    ],
    "evidence_paths": [
      [
        {
          "edge_id": "e1",
          "evidence": [
            {
              "id": "E1",
              "file": "source.txt",
              "lines": [
                1,
                1
              ],
              "quote": "Method A used sensor S.",
              "locator": "Example §2 ¶1"
            }
          ]
        }
      ]
    ]
  },
  {
    "query": {
      "mode": "in",
      "start": "d",
      "predicate": "measures",
      "question": "Which instrument measured drift?"
    },
    "paths": [
      [
        {
          "id": "e2",
          "source": "s",
          "target": "d",
          "predicate": "measures",
          "condition": "reported experiment",
          "polarity": "positive",
          "evidence": [
            "E2"
          ]
        }
      ]
    ],
    "evidence_paths": [
      [
        {
          "edge_id": "e2",
          "evidence": [
            {
              "id": "E2",
              "file": "source.txt",
              "lines": [
                2,
                2
              ],
              "quote": "Sensor S measured drift.",
              "locator": "Example §2 ¶2"
            }
          ]
        }
      ]
    ]
  },
  {
    "query": {
      "mode": "two_hop",
      "start": "a",
      "predicate": "uses",
      "second_predicate": "measures",
      "question": "Which quantity is reached through the instrument used by Method A?"
    },
    "paths": [
      [
        {
          "id": "e1",
          "source": "a",
          "target": "s",
          "predicate": "uses",
          "condition": "reported experiment",
          "polarity": "positive",
          "evidence": [
            "E1"
          ]
        },
        {
          "id": "e2",
          "source": "s",
          "target": "d",
          "predicate": "measures",
          "condition": "reported experiment",
          "polarity": "positive",
          "evidence": [
            "E2"
          ]
        }
      ]
    ],
    "evidence_paths": [
      [
        {
          "edge_id": "e1",
          "evidence": [
            {
              "id": "E1",
              "file": "source.txt",
              "lines": [
                1,
                1
              ],
              "quote": "Method A used sensor S.",
              "locator": "Example §2 ¶1"
            }
          ]
        },
        {
          "edge_id": "e2",
          "evidence": [
            {
              "id": "E2",
              "file": "source.txt",
              "lines": [
                2,
                2
              ],
              "quote": "Sensor S measured drift.",
              "locator": "Example §2 ¶2"
            }
          ]
        }
      ]
    ]
  }
]
```
