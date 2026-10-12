# GitHub 仓库与分发

仓库地址：[xiaoshen-kai/civilization-os](https://github.com/xiaoshen-kai/civilization-os) 。本项目采用 main 分支，原创代码与文档使用 [MIT 许可证](../LICENSE) ，第三方资料遵循 [NOTICE.md](../NOTICE.md) 与 [DATA.md](DATA.md) 中的出处及使用条件。

## 获取与安装

在仓库页面选择 Code → Download ZIP，或运行：

```text
git clone https://github.com/xiaoshen-kai/civilization-os.git
cd civilization-os
```

源码或完整仓库包内的 Skill 目录为 skills/civilization-os/；独立 Skill ZIP 内的目录为 civilization-os/。将对应目录整体复制到目标工具的项目或个人技能目录，保留 LICENSE、NOTICE.md、references/、scripts/ 和 agents/；具体路径及调用见 [README.md](../README.md) 。

当前本地构建器可生成仓库包和 Skill 包。GitHub 的 Source ZIP 是源码快照；本文件不承诺存在额外的 GitHub Release 附件。

## 维护与检查

在仓库根执行：

```text
python -X utf8 skills/civilization-os/scripts/catalog.py validate
python -X utf8 skills/civilization-os/scripts/verify_events.py
python -X utf8 scripts/update_library.py
python -X utf8 -m unittest discover -s tests
python -X utf8 scripts/build_release.py --output-dir ../civilization-os-release
```

构建器排除 Git 元数据、依赖、测试缓存和构建产物；发现工作资料、真实环境配置、个人配置或常见凭据时拒绝打包。根目录与 Skill 目录的许可证和声明必须保持一致。现有输出默认不覆盖，明确重新构建时可使用 --overwrite。

统计和离线校验不代表重新查阅全部一手原文。新增案例、事实更正和引用要求见 [CONTRIBUTING.md](../CONTRIBUTING.md) 。

## 提交与同步

实际变更和必要验证完成后，更新受到影响的文档与 ROADMAP.md。只提交正式公开文件，排除原始聊天、研究缓存、账户凭据、个人路径和 ZIP 产物。新增根文件须同步发布白名单。

Git 提交、推送、PR 和版本发布须在维护者授权范围内执行。不做覆盖式推送或改写历史；远端有新提交时先读取并协调。首次上传后，应核对默认分支、README、MIT 识别结果以及远端文件清单。

## 迁移到其他 GitHub 仓库

需要其他所有者、名称或可见性时，先明确目标和授权范围，再在独立仓库中处理，不覆盖无关项目。创建与上传可参考 [GitHub 新建仓库文档](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository) 与 [GitHub 文件上传说明](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository) 。

网页上传应把仓库内部的文件与目录放在仓库根，不多套一层 civilization-os-repo/。当前官方网页限制为单文件不超过 25 MiB、每批最多 100 个文件；文件数量或体积增长后按官方说明选择合适的 Git 工作流。只有明确要求时才创建或修改 GitHub Actions。
