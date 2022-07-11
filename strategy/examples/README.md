# 回测框架简单示例

## 简单风险平价策略

simple_rp，使用权重的方式执行策略，并演示如何使用策略的成员变量及再平衡。

python run.py -y strategy/examples/simple_rp/simple_rp.yaml 

## 简单定投策略

simple_fixed_investment，使用订单的方式执行策略。当持有现金不足时，定投将中止。

- fixed_investment：定投金额；
- profit_stop：止盈收益率；
- sell_proportion：止盈时卖出比例；

python run.py -y strategy/examples/simple_fixed_investment/simple_fixed_investment.yaml