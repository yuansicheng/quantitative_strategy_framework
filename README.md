# 轻量级策略回测框架
*苑思成，20220428*  
*https://github.com/yuansicheng/quantitative_strategy_framework/tree/master*

## 框架设计背景
上一个版本 *https://github.com/yuansicheng/strategy_template/tree/master* ，实现了回测的基本功能，但是使用和配置比较复杂，因此在上一个版本的基础上，主要针对以下方面进行了升级和优化：
- 使用yaml作为配置文件，yaml相对于python的好处在于语法简单，用户使用已有yaml模板可以快速更改参数进行下一组回测；
- 使用动态加载策略代码的方式，用户使用不同策略时，入口都是同一个python脚本；
- 使用matrix（参考github action）的方式，用户可以通过指定不同的参数实现多组参数的回测；
- 为每组参数对应的策略创建一个线程，并行执行回测，串行执行保存数据和图片，提高回测效率。

## 框架结构
![框架类图](design/class.png)

## 用户手册
