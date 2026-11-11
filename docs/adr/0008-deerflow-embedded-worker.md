# ADR 0008：DeerFlow SDK 嵌入独立 worker

- 状态：已采用

## 背景

DeerFlow 依赖较多，且 AI 运行不应拖垮 FastAPI API 进程；项目也不允许部署独立 DeerFlow 服务或 Docker 沙箱。

## 决定

在独立 Python 环境的 agent worker 进程中以 SDK 嵌入 DeerFlow。CrossERP API 进程通过 MySQL 任务表和事件表通信；业务工具在 CrossERP 进程内执行并重新检查权限。

## 后果

部署多一个 worker 进程，但 API 依赖边界清晰；不需要 DeerFlow 服务端口，也不需要 Docker。

## 依据（08 章节）

[08 第 10.0、10.1、10.7 节](../design/08-后端模块与API设计.md)。

## 状态

已采用；仅设计，待 worker 实现。
