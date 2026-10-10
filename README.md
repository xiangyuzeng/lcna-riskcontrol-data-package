# LCNA risk-control data packages

北美风控数据层包，供桌面项目 D1 导入生成《北美风控数据字典与取数手册》（LCNA-RC-2026-004）。全程只读取数；不含客户个人信息（手机号、邮箱、uid、IP 等均未取值）。

## 一个文件下载全部结果

- **[`LCNA_riskcontrol_results_all_20261010.zip`](https://github.com/xiangyuzeng/lcna-riskcontrol-data-package/raw/main/LCNA_riskcontrol_results_all_20261010.zip)**（约 14 MB）：四轮数据包（`RC_data_20261010-0013/` 最新、`RC_data_20260927-0614/`、`RC_data_20260926-1722/`、`RC_data_20260925-0817/`）原样解压后合在一个 zip 里，顶层有 `README.md` 索引；sha256 见 `LCNA_riskcontrol_results_all_20261010.zip.sha256`。合集隐私扫描 8,056 个文件，unresolved 0（放行 2 条：两轮的 Redis 平均 TTL，非个人信息）。
- 它取代 2026-09-27 的三轮合集（`LCNA_riskcontrol_results_all_20260927.zip`，仍在提交 `93aebbb` 的历史里）。

## 最新：RC_data_20261010-0013（2026-10-10，DR-030…038 + 常设项）

- 包内容（已解压）：[`RC_data_20261010-0013/`](RC_data_20261010-0013/) — 入口 [`README.md`](RC_data_20261010-0013/README.md)，DR 结论 [`04_数据问题结论.md`](RC_data_20261010-0013/04_数据问题结论.md)，开放探索 [`05_开放探索_20261009.md`](RC_data_20261010-0013/05_开放探索_20261009.md)，清单与校验和 [`MANIFEST.md`](RC_data_20261010-0013/MANIFEST.md)
- 原始 zip：`RC_data_package_20261010-0013.zip`，sha256 见 `RC_data_package_20261010-0013.zip.sha256`（桌面 D1 用它）
- 窗口：近 7 日 = 纽约日 2026-10-03…10-09；桥接序列 = 纽约日 09-27…10-09；长序列 = 纽约日 06-01…10-09
- DR：22 节（已答复 14、待确认 5、部分答复 2、待取数 1）；DR-002、DR-022 短节（Doris 不可达）；DR-028、DR-029 本次跳过
- 工具包 tk01–tk11（新增 tk11 绕过监控），61/61 项核对一致
- 隐私扫描（`toolkit/privacy_scan.py`）：557 个文件，unresolved 0

## 上一版：RC_data_20260927-0614（2026-09-27，DR-027 专项）

- 包内容（已解压）：[`RC_data_20260927-0614/`](RC_data_20260927-0614/)；zip：`RC_data_package_20260927-0614.zip`（+ `.sha256`）；近 7 日 = 纽约日 2026-09-20…09-26；13 条 DR（已答复 6、待确认 4、部分答复 2、待取数 1；新开 DR-029）；隐私扫描 unresolved 0。

## 第二版：RC_data_20260926-1722（2026-09-26）

- 包内容（已解压）：[`RC_data_20260926-1722/`](RC_data_20260926-1722/)；zip：`RC_data_package_20260926-1722.zip`（+ `.sha256`）；近 7 日 = 纽约日 2026-09-19…09-25；19 条 DR（已答复 12、待确认 5、部分答复 2）；隐私扫描 unresolved 0。

## 第一版：RC_data_20260925-0817（2026-09-25）

- 包内容（已解压）：[`RC_data_20260925-0817/`](RC_data_20260925-0817/)；zip：`RC_data_package_20260925-0817.zip`（+ `.sha256`）；隐私扫描 unresolved 0。
