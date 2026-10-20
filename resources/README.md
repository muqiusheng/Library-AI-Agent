# 静态资源与示例知识库

此目录保存随代码版本维护的输入样本。运行时上传、数据库、向量索引和备份放在被 Git 忽略的 `data/` 或 Compose 命名卷中。

| 路径 | 用途 |
|---|---|
| `knowledge_base/books/ShiepbookInfo.xlsx` | 示例馆藏，供 CLI 或管理端导入 |
| `knowledge_base/metadata/book_summaries.csv` | 图书摘要参考数据 |
| `knowledge_base/rules/borrowing_policy.json` | 借阅规则参考资料 |
| `knowledge_base/FAQ/historical_qa.json` | 历史问答参考样本 |
| `knowledge_base/samples/intent_samples.json` | 意图识别参考样本 |

除馆藏 Excel 的手动导入外，上述参考文件不因放在此目录中就被应用自动加载。实际使用方式以现有代码和[部署指南](../docs/deployment/DEPLOYMENT.md)为准。数据来源、版权和授权范围仍需由实际部署者确认。

在仓库根目录导入示例馆藏：

```powershell
uv run python -m app.cli import-library "resources\knowledge_base\books\ShiepbookInfo.xlsx"
```

后端镜像不包含本目录。Docker 环境使用部署指南中的 `docker compose cp` 命令，再在容器内导入。
