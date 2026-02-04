# Git 历史敏感信息清理指南

由于代码库中曾包含硬编码的敏感信息（如密码、密钥），即使在最新提交中已修复，这些信息仍可能保留在 Git 历史记录中。为了彻底清除这些风险，建议按照以下步骤清理 Git 历史。

> [!WARNING]
> **危险操作**：重写 Git 历史是破坏性操作。它会修改 commit hash，导致需要强制推送 (`git push --force`)。
> 请务必在执行前备份整个仓库！

## 方案一：使用 BFG Repo-Cleaner（推荐，简单快速）

BFG 是专门用于删除大文件和敏感数据的工具。

1.  **安装 BFG**
    - Mac: `brew install bfg`
    - Windows: `choco install bfg-repo-cleaner`

2.  **准备敏感字符串文件**
    创建一个包含要删除的敏感字符串的文件 `***REMOVED***words.txt`（每行一个）。
    ```text
    ***REMOVED***
    your-secret-key-change-in-production
    q5W19H3LbGcAmjNqjvZE91I7yNYWmzvD
    ```

3.  **执行清理**
    ```bash
    bfg --replace-text ***REMOVED***words.txt
    ```

4.  **清理引用并修剪**
    ```bash
    git reflog expire --expire=now --all && git gc --prune=now --aggressive
    ```

5.  **强制推送**
    ```bash
    git push --force
    ```

## 方案二：使用 git-filter-repo（官方推荐，功能强大）

1.  **安装**
    ```bash
    pip install git-filter-repo
    ```

2.  **执行清理**
    替换文件内容：
    ```bash
    git filter-repo --replace-text expressions.txt
    ```
    (其中 `expressions.txt` 格式需参考文档，通常为 `original_text==>replacement_text`) 

## 常见问题 (FAQ)

### Q: 这些操作会修复其他分支吗？
**是的，只要这些分支在本地存在。**

上述工具（BFG 和 git-filter-repo）不仅会处理当前检出的分支，默认情况下它们会扫描并重写**所有本地存在的引用**（包括所有本地分支 HEADS 和标签 TAGS）。

**为了确保清理所有远程分支：**

1.  **拉取所有分支到本地**：
    在运行清理工具之前，请确保你已经将所有需要清理的远程分支拉取到了本地。
    ```bash
    git fetch --all
    # 简单的批量拉取示例（或手动 checkout 每个需要的分支）
    git branch -r | grep -v '\->' | while read remote; do git branch --track "${remote#origin/}" "$remote"; done
    ```

2.  **清理后推送所有分支**：
    清理完成后，你需要强制推送所有分支更新到远程仓库：
    ```bash
    git push origin --all --force
    git push origin --tags --force
    ```

3.  **提醒团队成员**：
    由于历史被重写，团队其他成员在下次 pull 时会遇到冲突。最好的做法是让他们删除本地旧仓库，重新 clone 一份新的。

## 安全提示

- 清理完历史后，**所有现有密钥都应视为已泄露**。请务必轮换（Rotate）生产环境中的所有真实凭证（API Keys, JWT Secrets, Passwords）。
- 通知所有协作者重新 clone 仓库，避免再次推送包含旧历史的分支。
