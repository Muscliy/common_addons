# Common Addons

雅博平台的公共 Odoo 插件仓库，当前面向 Odoo / OCB 19。

每个插件放在本仓库的独立子目录，包含标准 Odoo `__manifest__.py` 文件。
主项目通过 Git 子模块固定本仓库的提交，并将 `common_addons/` 加入本地及部署环境的 `addons_path`。

拉取主项目后，在主项目根目录执行：

```sh
git submodule update --init --recursive
```

初始化或更新子模块只同步源码，不会自动安装业务插件。
