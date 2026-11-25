---
name: nanopublication
description: 从论文材料生成或核验带限定条件、证据与来源的原子断言，交付案例约定的机器可读产物。
---

# Nanopublication

给定原始材料和案例要求，交付以下结果。中间工具、表示和操作顺序由执行者选择。

- **断言。** 每条只表达一个可核验的结论。主体、比较方向、指标、适用条件、极性和确定程度忠实于原文。保留数值精度。换算单位、调换双方并反转比较方向、使用文中已定义的别名均可，只要含义与适用范围一致。
- **证据。** 每条可发布断言都能定位到支撑整个结论的最小原文、行或表格单元。对象、结果和全部限定条件必须属于同一观测；分散在表头、行或脚注时给出各自位置。另一组恰好出现同样的词或数值，不能支撑这一组。保留材料提供的作者、年份和版本。
- **边界。** 区分直接观察、推断与未决候选。缺证、冲突或条件错配的候选注明具体原因；其余有依据的断言照常交付。待核候选不作为已证实断言导出。
- **成品。** 遵守当前案例对 case_id、输出路径、字段、文件及状态的约定。JSON 可解析；案例要求 RDF 时，断言、来源和发布信息通过 Head 关联到各自的命名图，能够追溯到与 JSON 相同的结论和证据，并区分研究作者与记录制作者。案例有更具体的序列化约定时遵循该约定。

**最小调用示例（合成示意）**　给本 Skill 一条材料“表 2 第 4 行：经过 90 秒，样品 P 的读数高于 Q”，要求核验“1.5 分钟时 Q 的读数低于 P”。可交付的断言是“1.5 分钟时 Q < P”，证据指向表 2 第 4 行；若候选写的是 15 秒，该行不能支撑它。实际输出使用当前案例规定的格式。本 Skill 仅含说明，使用本身无需安装依赖。

**RDF 最终文件示意。** N-Quads 每行句点前的第四项是该条三元组所属的图名。以下为上例的最小四图；实际结论、来源、制作者及标识取自当前案例。

```nquads
<urn:np:demo> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.nanopub.org/nschema#Nanopublication> <urn:np:demo:head> .
<urn:np:demo> <http://www.nanopub.org/nschema#hasAssertion> <urn:np:demo:a> <urn:np:demo:head> .
<urn:np:demo> <http://www.nanopub.org/nschema#hasProvenance> <urn:np:demo:p> <urn:np:demo:head> .
<urn:np:demo> <http://www.nanopub.org/nschema#hasPublicationInfo> <urn:np:demo:i> <urn:np:demo:head> .
<urn:np:demo:comparison> <http://www.w3.org/2000/01/rdf-schema#label> "1.5 分钟时 Q 的读数低于 P" <urn:np:demo:a> .
<urn:np:demo:a> <http://www.w3.org/ns/prov#wasDerivedFrom> <urn:example:table2:row4> <urn:np:demo:p> .
<urn:example:table2:row4> <http://www.w3.org/2000/01/rdf-schema#label> "示例观测记录，表 2 第 4 行" <urn:np:demo:p> .
<urn:np:demo> <http://purl.org/dc/terms/creator> "示例整理者" <urn:np:demo:i> .
```
