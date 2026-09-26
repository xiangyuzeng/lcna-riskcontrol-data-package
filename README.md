# LCNA risk-control data packages

北美风控数据层包，供桌面项目 D1 导入生成《北美风控数据字典与取数手册》（LCNA-RC-2026-004）。全程只读取数；不含客户个人信息（手机号、邮箱、uid、IP 等均未取值）。

## 一个文件下载全部结果

- **[`LCNA_riskcontrol_results_all_20260926.zip`](https://github.com/xiangyuzeng/lcna-riskcontrol-data-package/raw/main/LCNA_riskcontrol_results_all_20260926.zip)**（约 10 MB）：两轮数据包（`RC_data_20260926-1722/` 最新、`RC_data_20260925-0817/` 上一轮）原样解压后合在一个 zip 里，顶层有 `README.md` 索引；sha256 见 `LCNA_riskcontrol_results_all_20260926.zip.sha256`。合集隐私扫描 7,097 个文件，unresolved 0。

## 最新：RC_data_20260926-1722（2026-09-26）

- 包内容（已解压）：[`RC_data_20260926-1722/`](RC_data_20260926-1722/) — 入口 [`README.md`](RC_data_20260926-1722/README.md)，DR 结论 [`04_数据问题结论.md`](RC_data_20260926-1722/04_数据问题结论.md)，清单与校验和 [`MANIFEST.md`](RC_data_20260926-1722/MANIFEST.md)
- 原始 zip：`RC_data_package_20260926-1722.zip`，sha256 见 `RC_data_package_20260926-1722.zip.sha256`
- 近 7 日窗口：纽约日 2026-09-19…09-25；DR 清单按 2026-09-26 版 `DATA_REQUESTS.md`（19 条：已答复 12、待确认 5、部分答复 2）
- 隐私扫描（`toolkit/privacy_scan.py`）：3,822 个文件，unresolved 0（1 条人工核对放行：Redis 平均 TTL）

## 上一版：RC_data_20260925-0817（2026-09-25）

- 包内容（已解压）：[`RC_data_20260925-0817/`](RC_data_20260925-0817/)；zip：`RC_data_package_20260925-0817.zip`（+ `.sha256`）；隐私扫描 unresolved 0。
