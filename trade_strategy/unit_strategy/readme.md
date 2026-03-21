# 自動売買システム：宣言的戦略構築エンジン 設計仕様書

## 1. 設計コンセプト
利用者が `(MACD.Cross > 0) & (RSI < 80)` のような自然な数式で売買ロジックを記述でき、かつ「条件を満たした場合に別の戦略を実行する」という再帰的な構造（Composite Pattern）をサポートします。

* **遅延評価 (Lazy Evaluation):** 条件式は定義時には計算されず、評価（`evaluate`）時に初めて計算される。
* **タイムスタンプ・キャッシュ:** 同一時間軸のインジケータ計算は、システム全体で1回のみ行われる（`last_timestamp` による制御）。
* **ステートレス・ロジック:** 条件オブジェクト自体は状態を持たず、実行時に外部から `StateManager` を注入することで連続回数などを管理する。

---

## 2. 主要コンポーネントの役割

### A. Strategy（戦略ノード）
意思決定の最小単位。
- **Attributes:** `condition`, `true_operation`, `false_operation`
- **Behavior:** `condition.evaluate()` の結果に基づき、次の `Operation`（注文、または別の `Strategy`）を再帰的に呼び出す。

### B. Condition（論理ゲート）
真偽値を判定するインターフェース。
- **ComparisonCondition:** `(Indicator > Value)` などの比較。
- **LogicalCondition:** `&` (AND) や `|` (OR) による結合。
- **StatefulCondition:** `ConsecutiveCount(cond) > N` のように、過去の履歴に依存する判定。

### C. Indicator（計算エンジン）
市場データを数値に変換する。
- **Internal:** `_cache`（最新の計算値）, `_last_timestamp`（最終計算時の時刻）。
- **Behavior:** `get_value(data)` が呼ばれた際、データの時刻が更新されていれば再計算し、そうでなければキャッシュを返す。

---

## 3. クラス設計（擬似コード）

### 演算子オーバーロードによる DSL 実装
利用者が `MACD > 0` と書いた瞬間に、計算ではなく「比較ルール」を生成する仕組みです。

```python
class Indicator:
    def __init__(self):
        self._cache = None
        self._last_timestamp = None

    def get_value(self, data):
        if self._last_timestamp != data.timestamp:
            self._cache = self.calculate(data)
            self._last_timestamp = data.timestamp
        return self._cache

    def __gt__(self, other):
        # > 演算子で ComparisonCondition を返す
        return ComparisonCondition(self, ">", other)

class ComparisonCondition:
    def __init__(self, left, op, right):
        self.left = left   # Indicator
        self.op = op       # ">"
        self.right = right # 0

    def evaluate(self, data, state_manager):
        val = self.left.get_value(data)
        # 実際の比較処理をここで実行
        return eval(f"{val} {self.op} {self.right}")
```

## 4. 状態管理 (StateManager) の仕組み

`Condition` オブジェクト自体に状態（カウンターなど）を持たせると、同じ条件を複数の戦略で再利用した際に数値が混ざってしまいます。これを防ぐため、状態は外部の `StateManager` で一括管理します。

### 状態データの構造
`StateManager` は各条件インスタンスの `id` をキーにして、その実行履歴を保持します。

| Key (Condition ID) | Value (State Object) | 説明 |
| :--- | :--- | :--- |
| `id(cond_1)` | `{"count": 3}` | 特定条件が連続で True になった回数 |
| `id(cond_2)` | `{"last_hit_price": 150.5}` | 条件成立時の価格（トレイリング決済用など） |
| `id(cond_3)` | `{"first_true_time": "10:00"}` | 最初に条件を満たした時刻 |

### 実装のポイント
`Condition.evaluate(data, state_manager)` 内で、自身の ID を使って `state_manager` からデータを取り出し、判定後に更新して戻します。これにより、ロジック（Condition）と記憶（State）の完全な分離が実現します。

---

## 5. 実行フロー（再帰的プロセス）

システムがシグナルを得るまでのプロセスは以下の通りです。

1.  **呼び出し**: `get_signal(root_strategy, market_data, state_manager)` を実行。
2.  **条件評価**: `Strategy` が `condition.evaluate()` を呼び出す。
3.  **オンデマンド計算**: 
    - `Condition` が `Indicator.get_value(data)` を要求。
    - `Indicator` は `data.timestamp` を確認。
    - **未計算なら**: 計算を実行しキャッシュを更新。
    - **計算済なら**: 即座にキャッシュ値を返す。
4.  **分岐**: 判定結果が `True` なら `true_op`、`False` なら `false_op` を参照。
5.  **再帰**: 参照先が別の `Strategy` であれば **手順2** に戻る。
6.  **終着**: 参照先が `OrderAction`（注文）や `NoAction` であれば、それを最終的なシグナルとして返す。

---

## 6. 実装上の急所：演算子オーバーロード (DSL)

Python の特殊メソッドを利用して、直感的な記述をオブジェクト構造に変換します。

```python
class Indicator:
    # ... (前述のキャッシュロジック)

    def __gt__(self, other):
        """ > 演算子のオーバーロード """
        return ComparisonCondition(self, ">", other)

    def __and__(self, other):
        """ & 演算子のオーバーロード (Condition同士の結合) """
        return LogicalCondition(self, "and", other)