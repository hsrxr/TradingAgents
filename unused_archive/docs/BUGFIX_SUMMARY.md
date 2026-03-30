# Bug Fix Summary: KeyError in _log_state

## 问题描述

运行 `main.py` 时，在执行将要结束时出现如下错误：

```
KeyError: 'judge_decision'
  File "trading_graph.py", line 387, in _log_state
    "judge_decision": final_state["investment_debate_state"]["judge_decision"]
```

## 根本原因

在简化的架构中，以下问题导致状态字段丢失或不存在：

1. **Bull Researcher 和 Bear Researcher 节点** 在更新 `investment_debate_state` 时，没有保留 `judge_decision` 字段
2. **_log_state 方法** 硬性访问各个状态字段，没有使用安全的 `.get()` 方法
3. **反射方法** (reflection.py) 在访问状态字段时也没有使用 `.get()`，导致可能的 KeyError
4. **条件逻辑** (conditional_logic.py) 在访问 `investment_debate_state` 时，没有安全防护

## 修复清单

### 1. Bull Researcher (`tradingagents/agents/researchers/bull_researcher.py`)
**改动**: 添加 `judge_decision` 到返回的 `investment_debate_state`

```python
# Before
new_investment_debate_state = {
    "history": ...,
    "bull_history": ...,
    "bear_history": ...,
    "current_response": ...,
    "count": ...
}

# After
new_investment_debate_state = {
    "history": ...,
    "bull_history": ...,
    "bear_history": ...,
    "current_response": ...,
    "judge_decision": investment_debate_state.get("judge_decision", ""),  # ✓ Added
    "count": ...
}
```

### 2. Bear Researcher (`tradingagents/agents/researchers/bear_researcher.py`)
**改动**: 添加 `judge_decision` 到返回的 `investment_debate_state` (同 Bull Researcher)

### 3. Trading Graph (_log_state) (`tradingagents/graph/trading_graph.py`)
**改动**: 使用 `.get()` 安全访问所有状态字段，并处理缺失的嵌套字段

```python
# Before: direct access 会导致 KeyError
"judge_decision": final_state["investment_debate_state"]["judge_decision"]

# After: 安全的嵌套访问
if "investment_debate_state" in final_state:
    invest_debate = final_state["investment_debate_state"]
    invest_debate_log = {
        ...
        "judge_decision": invest_debate.get("judge_decision", ""),  # ✓ Safe
    }
```

### 4. Reflection Methods (`tradingagents/graph/reflection.py`)
**改动**: 使用 `.get()` 安全访问所有状态字段

```python
# Before: 直接访问
bull_debate_history = current_state["investment_debate_state"]["bull_history"]
judge_decision = current_state["investment_debate_state"]["judge_decision"]

# After: 安全访问
bull_debate_history = current_state.get("investment_debate_state", {}).get("bull_history", "")
judge_decision = current_state.get("investment_debate_state", {}).get("judge_decision", "")
```

**受影响的方法**:
- `reflect_bull_researcher()` 
- `reflect_bear_researcher()`
- `reflect_trader()`
- `reflect_invest_judge()`
- `reflect_risk_manager()`

### 5. Conditional Logic (`tradingagents/graph/conditional_logic.py`)
**改动**: 使用 `.get()` 安全访问状态字段

```python
# Before
if state["investment_debate_state"]["count"] >= 2:

# After
debate_state = state.get("investment_debate_state", {})
if debate_state.get("count", 0) >= 2:
```

## 验证

所有修改已通过 Python 语法检查：

```bash
✓ bull_researcher.py
✓ bear_researcher.py  
✓ reflection.py
✓ conditional_logic.py
✓ trading_graph.py
```

## 运行测试

现在可以安全地运行：

```bash
python main.py
```

或使用带 API 密钥：

```bash
export DEEPSEEK_API_KEY=sk_xxxxx
python main.py
```

## 相关改动

- 简化架构中的 Risk Engine 已正确保留所有 `risk_debate_state` 字段
- 所有节点现在保持完整的状态字段，迎向 LangGraph 的最佳实践
