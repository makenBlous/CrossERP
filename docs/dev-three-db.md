# 三库开发验证

本文状态：**已实现兼容路径；不是正式部署目标**。

代码保留 SQLite、MySQL 8.4、PostgreSQL 18 的 SQLAlchemy 兼容测试。SQLite 适合本机演示；正式环境以 MySQL 8.4 LTS 为主；PostgreSQL 只作备选。每个迁移必须完成 `upgrade head → downgrade base → upgrade head`，金额必须逐分一致。

验证矩阵由 CI 和任务验收维护；本文件不要求本地启动数据库或运行服务。MySQL 的字符集、严格模式和连接串要求见 [数据库](database.md) 与 [08 第 11 章](design/08-后端模块与API设计.md)。
